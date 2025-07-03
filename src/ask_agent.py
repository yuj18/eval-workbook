import asyncio

from agents import MCSAgent


async def close_conversation(agent: MCSAgent) -> None:
    """
    Close the conversation with the agent.
    Args:
        agent (MCSAgent): The MCSAgent instance to close the conversation for.
    """
    agent_response = await agent.close_conversation()
    if agent_response.get("response"):
        for response in agent_response["response"]:
            if response["data"]:
                print(f"\nAgent:> {response['data']}\n")
    print("\nExiting chat...")


async def chat(agent: MCSAgent) -> bool:
    """
    Start a chat session with the agent.
    Args:
        agent (MCSAgent): The MCSAgent instance to chat with.
    Returns:
        bool: True if the chat should continue, False if it should exit.
    """
    try:
        print("-" * 50)
        query = input("User:>")
    except KeyboardInterrupt:
        await close_conversation(agent)
        return False
    except EOFError:
        await close_conversation(agent)
        return False

    if query == "exit":
        await close_conversation(agent)
        return False

    # Send the query to the agent and get the response
    agent_response = await agent.get_response(query=query)
    if agent_response.get("response"):
        for response in agent_response["response"]:
            if response["data"]:
                print(f"\nAgent:> {response['data']}\n")
            else:
                print("\nAgent:> Sorry, I don't have a response for that query.\n")

    return True


async def main() -> None:
    chatting = True
    user_id = "test_user"
    agent = MCSAgent(user_id=user_id, save_to="response.json")
    while chatting:
        chatting = await chat(agent=agent)


if __name__ == "__main__":
    asyncio.run(main())
