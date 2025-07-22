import os
import re
from typing import Optional, TypedDict

from azure.ai.evaluation import AzureOpenAIModelConfiguration
from azure.ai.ml import MLClient
from azure.ai.ml.identity import AzureMLOnBehalfOfCredential
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()


class ModelConfigInput(TypedDict):
    subscription_id: str
    resource_group: str
    project_name: str
    connection_name: str
    azure_deployment: str
    api_version: Optional[str]


def normalize_model_config(
    model_config_input: ModelConfigInput,
) -> AzureOpenAIModelConfiguration:
    """
    Create and return a normalized Azure OpenAI model configuration.
    Args:
        model_config_input (ModelConfigInput): Model configuration input.
    Returns:
        AzureOpenAIModelConfiguration: A normalized model configuration object.
    """

    subscription_id = model_config_input["subscription_id"]
    resource_group = model_config_input["resource_group"]
    project_name = model_config_input["project_name"]
    connection_name = model_config_input["connection_name"]
    azure_deployment = model_config_input["azure_deployment"]
    api_version = model_config_input.get("api_version")

    if os.environ.get("AZURE_OPENAI_API_KEY") and os.environ.get(
        "AZURE_OPENAI_ENDPOINT"
    ):
        api_key = os.environ["AZURE_OPENAI_API_KEY"]
        azure_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    else:
        try:
            # Use default Azure credential to retrieve connection details.
            ml_client = MLClient(
                subscription_id=subscription_id,
                resource_group_name=resource_group,
                workspace_name=project_name,
                credential=DefaultAzureCredential(),
            )

            connection = ml_client.connections.get(
                name=connection_name, populate_secrets=True
            )
            api_key = connection.credentials.get("key", None)
            azure_endpoint = connection.api_base
        except Exception:
            # Fallback to AzureMLOnBehalfOfCredential if DefaultAzureCredential fails.
            # This credential is used for scenarios where the application is running
            # on Azure Foundry Hub project managed compute.
            ml_client = MLClient(
                subscription_id=subscription_id,
                resource_group_name=resource_group,
                workspace_name=project_name,
                credential=AzureMLOnBehalfOfCredential(),
            )
            connection = ml_client.connections.get(
                name=connection_name, populate_secrets=True
            )
            api_key = connection.credentials.get("key", None)
            azure_endpoint = connection.api_base

    model_config = AzureOpenAIModelConfiguration(
        azure_endpoint=azure_endpoint or os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=api_version
        or os.environ["AZURE_OPENAI_API_VERSION"]
        or "2025-01-01-preview",
        api_key=api_key,
        azure_deployment=azure_deployment,
    )

    return model_config


def extract_conversation(
    conversation: list, step_types_to_evaluate: list = None
) -> str:
    """
    Extract a sequence of conversation turns, including
    user message and assistant response, as well as any agent steps
    associated with the assistant's response.

    Args:
        conversation (list): A list of conversation turns, where each turn is a dict.
        step_types_to_evaluate (list, optional): List of step types for analysis.
    Returns:
        str: A formatted string representing the conversation sequence.
    """

    results = []
    for turn in conversation:
        role = turn.get("role")
        content = turn.get("content", "")
        entry = {"role": role, "content": content}
        if role == "assistant":
            agent_steps = []
            steps_completed = turn.get("steps_completed", [])
            if steps_completed:
                if step_types_to_evaluate is not None:
                    agent_steps = [
                        step.get("name")
                        for step in steps_completed
                        if step.get("type") in step_types_to_evaluate
                    ]
                else:
                    agent_steps = [step.get("name") for step in steps_completed]
            agent_steps_str = ", ".join(agent_steps)
            entry["agent_steps"] = agent_steps_str
        results.append(entry)

    # Join the results into a formatted string
    formatted_results = []
    for entry in results:
        if "agent_steps" in entry:
            formatted_results.append(
                f"{entry['role'].upper()}: {entry['content']} \n(AGENT STEPS: {entry['agent_steps']})\n\n"  # noqa: E501
            )
        else:
            formatted_results.append(f"{entry['role'].upper()}: {entry['content']}")

    # Join all entries with newlines
    results = "\n".join(formatted_results)

    # Return the final formatted string
    if not results:
        return "No conversation data available."
    return results


def extract_agent_info(agent_dictionary: dict) -> str:
    """
    Extract agent name, description, and instruction from agent_dictionary.
    Agent instruction is included for principal agent only.

    Args:
        agent_dictionary (dict): The record containing agent information.
    Returns:
        str: A formatted string containing the agent information.
    """

    def clean_text(text: str) -> str:
        """Clean the text by removing leading non-alphanumeric characters."""
        if not text:
            return text
        # Remove leading non-alphanumeric characters (including newlines)
        cleaned = re.sub(r"^[^\w]+", "", text)
        return cleaned

    def extract_string(input: str, prefixes: list, postfixes: list) -> str:
        """
        Extract a specific section from an input string based on possible
        prefixes and postfixes.
        """
        for prefix in prefixes:
            for postfix in postfixes:
                pattern = re.escape(prefix) + r"(.*?)" + re.escape(postfix)
                match = re.search(pattern, input, re.DOTALL)
                if match:
                    return match.group(1).strip()
        return None

    principal_name = agent_dictionary.get("agent_name", "")
    principal_desc = clean_text(agent_dictionary.get("agent_description", ""))
    principal_instr_field = agent_dictionary.get("agent_instructions", "")

    # Extract principal agent instructions
    principal_instr = extract_string(
        principal_instr_field,
        ["instructions: |-\n", "instructions: |-\r\n"],
        ["\ngptCapabilities:", "\rgptCapabilities:"],
    )
    if principal_instr is None:
        principal_instr = principal_instr_field
    principal_instr = clean_text(principal_instr)

    # Build principal agent section
    principal_agent_section = (
        "\n## Principal Agent\n"
        + f"{principal_name}: {principal_desc}\n"
        + f"\n### Principal Agent Instructions\n{principal_instr}"
    )

    # Extract sub-agents
    sub_agents_list = []
    for sub in agent_dictionary.get("sub_agents", []):
        name = sub.get("name", "")
        desc = sub.get("description", "")
        instr_field = sub.get("instructions", "")

        # If description is empty, extract from instructions
        if not desc and instr_field:
            desc = extract_string(
                instr_field, ["description: "], ["\nsettings:", "\r\nsettings:"]
            )
        desc = clean_text(desc)
        if name and name != principal_name and desc:
            sub_agents_list.append(f"**{name}**: {desc}")

    # Add a single sub-agent section listing all sub-agents
    if sub_agents_list:
        sub_agents_section = "\n\n## Sub Agents\n\n" + "\n\n- ".join(sub_agents_list)
    else:
        sub_agents_section = "\nSub Agents: None"

    result = principal_agent_section + sub_agents_section

    return result
