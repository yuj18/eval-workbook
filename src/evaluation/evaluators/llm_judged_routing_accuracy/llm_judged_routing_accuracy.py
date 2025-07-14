import asyncio
import json
import logging
import os
from typing import TypedDict

from azure.ai.evaluation import AzureOpenAIModelConfiguration
from dotenv import load_dotenv
from promptflow.core._flow import AsyncPrompty
from utils import extract_agent_info, extract_conversation

logger = logging.getLogger(__name__)
load_dotenv()

EVALUATOR_NAME = "LLMJudgedRoutingAccuracyEvaluator"
EVALUATOR_DESCRIPTION = "Evaluates the routing accuracy of a conversation using LLM. "


class LLMJudgedRoutingAccuracyResult(TypedDict):
    """
    Result of the LLM judged routing accuracy evaluation.
    contains the rating, explanation, and thought process of the LLM.
    """

    rating: int
    explanation: str
    thought: str


class LLMJudgedRoutingAccuracyEvaluator:
    def __init__(self, model_config, step_types_to_evaluate: list = ["agent"]):
        """
        Initialize the evaluator with the model config and step types to evaluate.

        Args:
            model_config (AzureOpenAIModelConfiguration): Azure OpenAI LLM config.
            step_types_to_evaluate (list, optional):Step types to include in evaluation.
        """
        current_dir = os.path.dirname(__file__)
        prompty_path = os.path.join(current_dir, "llm_judged_routing_accuracy.prompty")

        self._flow = AsyncPrompty.load(
            source=prompty_path, model={"configuration": model_config}
        )
        self._step_types_to_evaluate = step_types_to_evaluate

    async def evaluate(
        self, *, conversation: str, agent_description: str
    ) -> LLMJudgedRoutingAccuracyResult:
        """
        Evaluate the routing accuracy of the conversation using LLM.

        Args:
            conversation (str): Formatted conversation string.
            agent_description (str): Agent descriptions.
        """
        try:
            response = await self._flow(
                conversation=conversation, agent_description=agent_description
            )
        except Exception as e:
            logger.error(f"Error during LLM evaluation: {e}")
            raise
        return response

    def __call__(self, *, conversation: list, agent_dictionary: dict):
        """
        Call the evaluator with conversation and agent dictionary.
        Args:
            conversation (list): List of conversation turns.
            agent_dictionary (dict): Dictionary containing agent information.
        Returns:
            LLMJudgedRoutingAccuracyResult: Result of the evaluation.
        """

        formatted_conversation = extract_conversation(
            conversation, self._step_types_to_evaluate
        )
        agent_description = extract_agent_info(agent_dictionary)
        return asyncio.run(
            self.evaluate(
                conversation=formatted_conversation, agent_description=agent_description
            )
        )


# Example usage:

if __name__ == "__main__":

    model_config = AzureOpenAIModelConfiguration(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_deployment=os.environ["MODEL_DEPLOYMENT_NAME"],
    )

    evaluator = LLMJudgedRoutingAccuracyEvaluator(model_config=model_config)

    conversation = [
        {
            "role": "user",
            "content": "What is the capital of France?",
        },
        {
            "role": "assistant",
            "content": "The capital of France is Paris.",
            "steps_completed": [
                {"name": "Search Agent", "type": "agent"},
            ],
        },
    ]

    agent_dictionary = {
        "agent_name": "Principal Agent",
        "agent_description": "An agent that routes queries to the appropriate service.",
        "agent_instructions": "Use the Search Agent for queries related to information retrieval. Use the Booking Agent for queries related to bookings.",  # noqa: E501
        "sub_agents": [
            {
                "name": "Search Agent",
                "description": "Handles search queries.",
            },
            {
                "name": "Booking Agent",
                "description": "Handles booking requests.",
            },
        ],
    }

    result = evaluator(
        conversation=conversation,
        agent_dictionary=agent_dictionary,
    )

    print("Evaluation Result:", json.dumps(result, indent=2))
