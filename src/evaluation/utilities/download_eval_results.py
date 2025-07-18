import argparse
import json
import os
import mlflow

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from storage_account_io import read_blob_from_uri

load_dotenv()


def get_workspace_specs():
    """Get workspace specifications."""

    ml_client = MLClient(
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
        resource_group_name=os.environ["AZURE_RESOURCE_GROUP"],
        workspace_name=os.environ["AZURE_HUB_PROJECT_NAME"],
        credential=DefaultAzureCredential(),
    )
    workspace = ml_client.workspaces.get(name=os.environ["AZURE_HUB_PROJECT_NAME"])
    project_id = workspace._workspace_id
    storage_id = workspace.storage_account
    storage_account_name = storage_id.split("/")[-1] if storage_id else None

    return {
        "project_id": project_id,
        "storage_account_name": storage_account_name,
    }


def get_evaluation_results(evaluation_job_id: str) -> list:
    """
    Get evaluation results from AI Hub Project evaluation runs.

    Args:
        evaluation_job_id (str): The evaluation job ID which is available in the
        evaluation job creation response.

    Returns:
        list: Parsed JSON content of the evaluation results.
    """
    try:
        # Get workspace specifications
        workspace_specs = get_workspace_specs()
        workspace_id = workspace_specs["project_id"]
        storage_account_name = workspace_specs["storage_account_name"]

        # Construct the results URI
        job_id = evaluation_job_id
        data_container_id = f"dcid.{job_id}"
        results_uri = f"https://{storage_account_name}.blob.core.windows.net/{workspace_id}-azureml/ExperimentRun/{data_container_id}/instance_results.jsonl"  # noqa: E501

        # Read the blob content
        content = read_blob_from_uri(results_uri)

        if content:
            # Parse JSONL content
            lines = content.strip().split("\n")
            results = []

            for line in lines:
                if line.strip():
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"Error parsing line: {e}")
                        continue

            print(f"Parsed {len(results)} JSON objects")
            return results
        else:
            print("Failed to read blob content")

    except Exception as e:
        print(f"Error processing evaluation response: {e}")
        return None

def get_evaluation_metrics(evaluation_job_id: str) -> dict:
    """
    Get evaluation metrics from AI Hub Project evaluation runs.

    Args:
        evaluation_job_id (str): The evaluation job ID which is available in the
        evaluation job creation response.

    Returns:
        dict: JSON content of the evaluation metrics.
    """
    try:
        ml_client = MLClient(
            subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
            resource_group_name=os.environ["AZURE_RESOURCE_GROUP"],
            workspace_name=os.environ["AZURE_HUB_PROJECT_NAME"],
            credential=DefaultAzureCredential(),
        )

        # Get the MLflow tracking URI from the workspace
        workspace = ml_client.workspaces.get(os.environ["AZURE_HUB_PROJECT_NAME"])
        mlflow.set_tracking_uri(workspace.mlflow_tracking_uri)

        # Get metrics from the MLflow run
        run = mlflow.get_run(run_id=evaluation_job_id)
        metrics = run.data.metrics

        if metrics:
            print(f"{len(metrics)} Metrics found for job '{evaluation_job_id}'.")
            return metrics
        else:
            print(f"No metrics found for job '{evaluation_job_id}'.")

    except Exception as e:
        print(f"Error retrieving job {evaluation_job_id}: {e}")
        return None



def main():
    """
    Example usage:
        python download_eval_results.py --config ../../../config/eval_result_download_config.json    # noqa: E501

    Config structure:
        {
            "input_path": "eval_run.json",  # Path to input JSON with 'job_id'
            "results_output_path": "evaluation_results.json",  # Path to save output JSON for evaluation results
            "metrics_output_path": "evaluation_metrics.json",  # Path to save output JSON for evaluation metrics
            "notes": (
                "Paths are relative to the parent directory of "
                "download_eval_results.py. Input JSON should contain a 'job_id' key "
                "with the evaluation run ID."
            )
        }
    """
    parser = argparse.ArgumentParser(description="Read cloud evaluation results.")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to config JSON file containing input_path and output_path.",
    )
    args = parser.parse_args()

    with open(args.config, "r") as f:
        config = json.load(f)
    input_path = config["input_path"]
    results_output_path = config.get("results_output_path", "evaluation_results.json")
    metrics_output_path = config.get("metrics_output_path", "evaluation_metrics.json")

    with open(input_path, "r") as f:
        evaluation_response = json.load(f)

    # Read the evaluation job ID from the provided file
    evaluation_job_id = evaluation_response.get("job_id")

    if evaluation_job_id:
        results = get_evaluation_results(evaluation_job_id)
        if results:
            print("Evaluation results retrieved successfully.")
            with open(results_output_path, "w") as f:
                json.dump(results, f, indent=4)
            print(f"Results saved to {results_output_path}")
        else:
            print("No results found or an error occurred.")

        metrics = get_evaluation_metrics(evaluation_job_id)
        if metrics:
            print("Evaluation metrics retrieved successfully.")
            with open(metrics_output_path, "w") as f:
                json.dump(metrics, f, indent=4)
            print(f"Metrics saved to {metrics_output_path}")
        else:
            print("No metrics found or an error occurred.")
    else:
        print("No evaluation job ID found in the provided input file.")


if __name__ == "__main__":
    main()
