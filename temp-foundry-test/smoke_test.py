from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI


def main() -> None:
    with DefaultAzureCredential() as credential:
        token_provider = get_bearer_token_provider(
            credential, "https://ai.azure.com/.default"
        )
        with OpenAI(
            base_url="https://nkfoundry26.openai.azure.com/openai/v1/",
            api_key=token_provider,
            max_retries=0,
            timeout=60.0,
        ) as client:
            response = client.responses.create(
                model="gpt-5.4-mini",
                input="What is the capital of France?",
                max_output_tokens=256,
                store=False,
            )

        if response.status != "completed" or not response.output_text:
            raise RuntimeError(
                f"No completed text response: status={response.status}, "
                f"incomplete_details={response.incomplete_details}"
            )

        print(f"answer: {response.output_text}")
        if response.usage is not None:
            print(
                f"tokens: input={response.usage.input_tokens}, "
                f"output={response.usage.output_tokens}"
            )


if __name__ == "__main__":
    main()
