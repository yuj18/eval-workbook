import asyncio
import json
import os
import time

import aiohttp
from dotenv import load_dotenv

load_dotenv()


class MCSAgent:
    """
    A class to asyncly interact with the Microsoft Copilot Studio (MCS) agent
    through the Direct Line API.
    """

    def __init__(
        self,
        user_id: str = "default_user",
        locale: str = "en-EN",
        timeout: int = 60,
        poll_interval: int = 5,
        save_to: str = None,
    ):
        """
        Initialize the MCSAgent with user ID, locale, timeout, and poll interval.
        Args:
            user_id (str): Unique identifier for the user interacting with the agent.
            locale (str): Locale for the conversation, e.g., "en-EN".
            timeout (int): Maximum seconds to wait for a response from the agent.
            poll_interval (int): Interval in seconds to poll for a response.
            save_to (str): Optional file path to save the full response.
        """
        self._user_id = user_id
        self._locale = locale
        self._timeout = timeout
        self._poll_interval = poll_interval
        self._save_to = save_to

        self._agent_key = os.getenv("MCS_AGENT_KEY")
        self._conversation_base_url = (
            os.getenv(
                "DIRECTLINE_BASE_URL",
                "https://directline.botframework.com/v3/directline",
            )
            + "/conversations"
        )
        self._conversation_id = None
        self._token = None
        self._logs = {}
        self._watermark = None

        self._full_response = []

    async def _send_query(self, query: str, session: aiohttp.ClientSession) -> str:
        """
        Send a query to the agent:
        https://learn.microsoft.com/en-us/azure/bot-service/rest-api/bot-framework-rest-direct-line-3-0-send-activity
        Args:
            query (str): The query to send to the MCS agent.
            session (aiohttp.ClientSession): The session to use for the request.
        Returns:
            str: The ID of the activity created in the conversation.
        """
        data = {
            "locale": self._locale,
            "type": "message",
            "from": {"id": self._user_id},
            "text": query,
        }
        conversation_url = (
            f"{self._conversation_base_url}/{self._conversation_id}/activities"
        )
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }
        async with session.post(
            conversation_url, headers=headers, json=data
        ) as response:
            response.raise_for_status()
            resp_json = await response.json()
            return resp_json.get("id")

    async def _start_conversation(self, session: aiohttp.ClientSession):
        """
        Start a conversation with the agent. This method needs to be called
        before sending any queries whether to start a new conversation or to
        continue an existing one:
        https://learn.microsoft.com/en-us/azure/bot-service/rest-api/bot-framework-rest-direct-line-3-0-start-conversation
        Args:
            session (aiohttp.ClientSession): The session to use for the request.
        """
        if self._token is None:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._agent_key}",
            }
        else:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }
        async with session.post(
            self._conversation_base_url, headers=headers
        ) as response:
            response.raise_for_status()
            response_json = await response.json()
            if self._conversation_id is None:
                self._conversation_id = response_json.get("conversationId")
            if self._token is None:
                self._token = response_json.get("token")

    async def _poll_for_response(self, session: aiohttp.ClientSession):
        """
        Poll for the agent response.
        https://learn.microsoft.com/en-us/azure/bot-service/rest-api/bot-framework-rest-direct-line-3-0-receive-activities
        Args:
            session (aiohttp.ClientSession): The session to use for the request.
        Returns:
            dict: A dictionary containing the full response, the agent response,
            and the processing time.
        """
        if self._watermark is None:
            conversation_url = (
                f"{self._conversation_base_url}/{self._conversation_id}/activities"
            )
        else:
            conversation_url = (
                f"{self._conversation_base_url}/"
                f"{self._conversation_id}/activities?watermark="
                f"{self._watermark}"
            )
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }
        start_time = time.time()
        bot_response = []
        while time.time() - start_time < self._timeout:
            async with session.get(conversation_url, headers=headers) as response:
                response.raise_for_status()
                response_json = await response.json()
                bot_response = [
                    {
                        "data": activity.get("text") or activity.get("speak"),
                        "timestamp": activity.get("timestamp"),
                    }
                    for activity in response_json.get("activities", [])
                    if activity.get("from", {}).get("role") == "bot"
                    and activity.get("type") == "message"
                    and (activity.get("text") or activity.get("speak"))
                ]
                new_watermark = response_json.get("watermark")
                if (
                    self._watermark
                    and new_watermark
                    and self._watermark == new_watermark
                    and bot_response
                ):
                    break
                self._watermark = new_watermark
                print(f"Waiting for bot response, current watermark: {self._watermark}")
                await asyncio.sleep(self._poll_interval)

        result = {
            "response": response_json,
            "bot_response": bot_response,
            "conversation_id": self._conversation_id,
            "processing_time": int(time.time() - start_time),
        }

        return result

    async def get_response(self, query: str) -> dict:
        """
        Get a response from the MCS agent for a given query.
        Args:
            query (str): The query to send to the MCS agent.
        Returns:
            dict: A dictionary containing the user ID, conversation ID, response,
            logs, and processing time.
        """
        async with aiohttp.ClientSession() as session:
            await self._start_conversation(session)
            await self._send_query(query, session)
            result = await self._poll_for_response(session)
            agent_response = {
                "user_id": self._user_id,
                "conversation_id": self._conversation_id,
                "response": result.get("bot_response"),
                "logs": self._logs,
                "processing_time": result.get("processing_time"),
            }

        if self._save_to:
            # Save the full response
            self._full_response.append(result.get("response"))
            with open(self._save_to, "w") as f:
                json.dump(self._full_response, f, indent=2)
        return agent_response

    async def close_conversation(self) -> dict:
        """
        Close the conversation with the agent.
        Args:
            session (aiohttp.ClientSession): The session to use for the request.
        Returns:
            dict: A dictionary containing the user ID, conversation ID, response,
            logs, and processing time.
        """
        if self._conversation_id is not None:
            conversation_url = (
                f"{self._conversation_base_url}/{self._conversation_id}/activities"
            )
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._token}",
            }
            data = {
                "type": "endOfConversation",
                "from": {"id": self._user_id},
            }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                conversation_url, headers=headers, json=data
            ) as response:
                response.raise_for_status()
                result = await self._poll_for_response(session)
                agent_response = {
                    "user_id": self._user_id,
                    "conversation_id": self._conversation_id,
                    "response": result.get("bot_response"),
                    "logs": self._logs,
                    "processing_time": result.get("processing_time"),
                }
                if self._save_to:
                    # Save the full response
                    self._full_response.append(result.get("response"))
                    with open(self._save_to, "w") as f:
                        json.dump(self._full_response, f, indent=2)

        return agent_response

    # Get conversation id
    def get_conversation_id(self) -> str:
        """
        Get the conversation ID of the current conversation.
        Returns:
            str: The conversation ID.
        """
        return self._conversation_id


if __name__ == "__main__":
    # Example usage of the async MCSAgent
    agent = MCSAgent(user_id="test_user")
    response = asyncio.run(
        agent.get_response(
            "can you help me learn about food chain and quiz me?",
            save_to="response.json",
        )
    )
