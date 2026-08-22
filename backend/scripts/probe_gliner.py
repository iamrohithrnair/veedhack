import asyncio
import json

from app.config import get_settings
from app.pioneer.finetune import PioneerClient


async def main() -> None:
    settings = get_settings()
    async with PioneerClient(
        settings.require("pioneer_api_key"), settings.pioneer_base_url
    ) as pioneer:
        result = await pioneer.inference(
            {
                "model_id": settings.pioneer_model_id or "fastino/gliner2-base-v1",
                "text": "Busy founders struggle to publish consistently; turn one insight into a compelling video today.",
                "schema": {
                    "entities": ["Core_Subject", "Pain_Point", "Action_Hook"],
                    "classifications": [
                        {
                            "task": "Emotional_Vibe",
                            "labels": ["outrage", "excitement", "warning", "confidence"],
                        }
                    ],
                },
                "store": False,
            }
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
