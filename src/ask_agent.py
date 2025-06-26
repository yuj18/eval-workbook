import asyncio

from agents import MCSAgent


async def chat(agent: MCSAgent) -> bool:
    try:
        print("-" * 50)
        query = input("User:>")
    except KeyboardInterrupt:
        print("\n\nExiting chat...")
        return False
    except EOFError:
        print("\n\nExiting chat...")
        return False

    if query == "exit":
        print("\n\nExiting chat...")
        return False

    agent_response = await agent.get_response(query=query, save_to="response.json")
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
    agent = MCSAgent(user_id=user_id)
    while chatting:
        chatting = await chat(agent=agent)


if __name__ == "__main__":
    asyncio.run(main())
