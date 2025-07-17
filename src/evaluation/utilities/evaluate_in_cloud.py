import argparse
import json
import os

from azure.ai.evaluation import AzureOpenAIModelConfiguration
from azure.ai.ml import MLClient
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import Dataset, Evaluation, EvaluatorConfiguration
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()


def get_hub_project_client(
    project_endpoint: str = None,
) -> AIProjectClient:
    """
    Initializes and returns an AIProjectClient instance for the Hub project.

    Args:
        project_endpoint (str, optional): The endpoint of the Azure AI Foundry project.

    Returns:
        AIProjectClient: An instance of AIProjectClient.
    """
    if project_endpoint is None:
        project_endpoint = os.environ.get("HUB_PROJECT_ENDPOINT")
        if not project_endpoint:
            raise ValueError("HUB_PROJECT_ENDPOINT environment variable is not set.")

    return AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=project_endpoint,
    )


def get_data_id(ml_client, data_name, data_version):
    """
    Given a data asset name and version, retrieve the data asset ID.
    """
    try:
        if data_version == "latest":
            data = ml_client.data.get(name=data_name, label="latest")
        else:
            data = ml_client.data.get(name=data_name, version=data_version)
        return data.id
    except Exception as e:
        raise ValueError(
            f"Failed to retrieve data asset '{data_name}' with version "
            f"'{data_version}': {e}"
        )


def configure_evaluator(ml_client, workspace, evaluators_config):
    """
    Configure evaluator settings for the evaluation job.
    """
    if not evaluators_config:
        raise ValueError("No evaluators found in the evaluation configuration.")

    evaluator_setting = {}
    model_config = AzureOpenAIModelConfiguration(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_deployment=os.environ["MODEL_DEPLOYMENT_NAME"],
    )

    init_params = {"model_config": model_config}
    for evaluator in evaluators_config:
        evaluator_name = evaluator.get("name")
        if not evaluator_name:
            raise ValueError("Evaluator name is required in the configuration.")

        evaluator_version = evaluator.get("version", "latest")
        if evaluator_version == "latest":
            evaluator_model = ml_client.models.get(name=evaluator_name, label="latest")
        else:
            evaluator_model = ml_client.models.get(
                name=evaluator_name, version=evaluator_version
            )
        data_mapping = {
            key: f"${{data.{value}}}"
            for key, value in evaluator.get("data_mapping", {}).items()
        }
        if not data_mapping:
            raise ValueError(
                f"Data mapping is required for evaluator '{evaluator_name}'."
            )
        init_param_keys = evaluator.get("init_params", [])
        # Validate init_param_keys
        for key in init_param_keys:
            if key not in init_params:
                raise ValueError(
                    f"Init parameter '{key}' is not defined in the provided "
                    "init_params."
                )
        config_kwargs = {
            "id": (
                f"azureml://locations/{workspace.location}/workspaces/"
                f"{workspace._workspace_id}/models/{evaluator_name}/versions/"
                f"{evaluator_model.version}"
            ),
            "data_mapping": data_mapping,
        }
        if init_param_keys:
            config_kwargs["init_params"] = {
                key: init_params[key] for key in init_param_keys
            }
        evaluator_setting[evaluator_name] = EvaluatorConfiguration(**config_kwargs)
    return evaluator_setting


def create_evaluation(project_client, eval_config, data_id, evaluator_setting):
    """
    Create and submit an evaluation job to Azure AI Foundry.
    """
    evaluation = Evaluation(
        display_name=eval_config.get("name", "Evaluation"),
        description=eval_config.get("description", ""),
        data=Dataset(id=data_id),
        evaluators=evaluator_setting,
    )
    evaluation_job = project_client.evaluations.create(evaluation=evaluation)
    print(f"Evaluation job submitted with job ID: {evaluation_job.id}")
    # Optionally, you can wait for the evaluation to complete
    # evaluation_job.wait_for_completion(show_output=True)

    return evaluation_job


def main():
    """
    Example usage:
        python evaluate_in_cloud.py --config ../../../config/evaluation_config.json

    Config structure:
        {
            "name": "Evaluate Routing Performance",
            "description": "Evaluate the routing performance of the principal agent.",
            "data": {
                "name": "interactive_conversations_test",
                "version": "latest"
            },
            "evaluators": [
                {
                    "name": "RoutingAccuracyEvaluator",
                    "version": "latest",
                    "data_mapping": {
                        "route": "all_steps_planned",
                        "reference_route": "expected_steps"
                    }
                },
                {
                    "name": "LLMJudgedRoutingAccuracyEvaluator",
                    "version": "latest",
                    "data_mapping": {
                        "conversation": "conversation",
                        "agent_dictionary": "agent_dictionary"
                    },
                    "init_params":["model_config"]
                }
            ]
        }
    """
    parser = argparse.ArgumentParser(
        description="Run evaluation in cloud using config."
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to evaluation_config.json file.",
    )
    args = parser.parse_args()

    with open(args.config, "r") as f:
        eval_config = json.load(f)
    data_name = eval_config["data"]["name"]
    data_version = eval_config["data"].get("version", "latest")
    evaluators_config = eval_config.get("evaluators", [])

    # Foundry hub project client
    project_client = get_hub_project_client()

    # An ML client is linked to the specified Foundry hub project and
    # provides the access to the underlying data and evaluators (i.e., models)
    # that underpin the Foundry evaluation job.
    ml_client = MLClient(
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
        resource_group_name=os.environ["AZURE_RESOURCE_GROUP"],
        workspace_name=os.environ["AZURE_HUB_PROJECT_NAME"],
        credential=DefaultAzureCredential(),
    )
    workspace = ml_client.workspaces.get(name=os.environ["AZURE_HUB_PROJECT_NAME"])

    # Retrieve the data asset ID
    data_id = get_data_id(ml_client, data_name, data_version)

    # Configure evaluator settings
    evaluator_setting = configure_evaluator(ml_client, workspace, evaluators_config)

    # Submit the evaluation job
    evaluation_job = create_evaluation(project_client, eval_config, data_id, evaluator_setting)

    # Save the evaluation job ID to a file for later results retrieval
    with open("evaluation_job_response.json", "w") as f:
        json.dump({"job_id": evaluation_job.id}, f, indent=2)


if __name__ == "__main__":
    main()
