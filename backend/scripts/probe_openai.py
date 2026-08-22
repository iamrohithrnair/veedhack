import asyncio

from openai import AsyncOpenAI

from app.config import get_settings


async def main() -> None:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.require("openai_api_key"))
    response = await client.responses.create(
        model=settings.openai_model,
        input="Reply with exactly: Charismate ready",
        store=False,
    )
    print(response.output_text)


if __name__ == "__main__":
    asyncio.run(main())
