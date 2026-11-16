import asyncio

from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncOpenAI


async def main() -> None:
    async with DefaultAzureCredential() as credential:
        token_provider = get_bearer_token_provider(
            credential, "https://ai.azure.com/.default"
        )
        async with AsyncOpenAI(
            base_url="https://nkfoundry26.openai.azure.com/openai/v1/",
            api_key=token_provider,
            max_retries=0,
            timeout=60.0,
        ) as sdk_client:
            agent = Agent(
                client=OpenAIChatClient(
                    model="gpt-5.4-mini", async_client=sdk_client
                ),
                name="TravelHelper",
                instructions="Answer briefly. Use the conversation for follow-up questions.",
                default_options={"store": False, "max_tokens": 256},
            )
            # With store=False, this shared session holds history in memory.
            # Reusing it in each run sends earlier prompts and answers as context.
            session = agent.create_session()

            for prompt in (
                "What is the capital of France?",
                "What are three top tourist attractions there? Name the city in your answer.",
            ):
                print(f"user: {prompt}", flush=True)
                response = await agent.run(prompt, session=session)
                if response.finish_reason != "stop" or not response.text.strip():
                    raise RuntimeError(
                        f"No completed text response: finish_reason={response.finish_reason}"
                    )

                print(f"assistant: {response.text}")
                if response.usage_details:
                    print(f"usage: {dict(response.usage_details)}")
                print()


if __name__ == "__main__":
    asyncio.run(main())
