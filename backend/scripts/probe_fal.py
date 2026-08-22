import asyncio
import json
import os

from app.config import get_settings


async def main() -> None:
    settings = get_settings()
    os.environ["FAL_KEY"] = settings.require("fal_key")
    import fal_client

    result = await fal_client.subscribe_async(
        settings.fal_image_model,
        arguments={
            "prompt": "Photorealistic charismatic presenter, neutral studio background",
            "num_images": 1,
        },
        with_logs=True,
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
