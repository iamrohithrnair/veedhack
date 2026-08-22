import argparse
import asyncio
import json
from typing import Any

from tavily import TavilyClient

from app.config import get_settings
from app.pioneer.finetune import PioneerClient


def _split_passages(content: str) -> list[str]:
    parts: list[str] = []
    for block in content.replace("\r\n", "\n").split("\n"):
        block = " ".join(block.split()).strip()
        if len(block) < 80:
            continue
        if len(block) <= 700:
            parts.append(block)
            continue
        start = 0
        while start < len(block):
            end = min(start + 700, len(block))
            if end < len(block):
                cut = block.rfind(". ", start, end)
                if cut > start + 120:
                    end = cut + 1
            chunk = block[start:end].strip()
            if len(chunk) >= 80:
                parts.append(chunk)
            start = end
    return parts


def collect_paragraphs(
    api_key: str,
    topics: list[str],
    per_topic: int,
    *,
    include_raw_content: bool = False,
) -> list[dict[str, str]]:
    tavily = TavilyClient(api_key=api_key)
    rows: list[dict[str, str]] = []
    for topic in topics:
        response = tavily.search(
            query=topic,
            search_depth="advanced",
            max_results=per_topic,
            include_answer=False,
            include_raw_content=include_raw_content,
        )
        for result in response.get("results", []):
            blobs: list[str] = []
            for key in ("content", "raw_content"):
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    blobs.append(value)
            for blob in blobs:
                for paragraph in _split_passages(blob):
                    rows.append(
                        {"topic": topic, "text": paragraph, "source_url": result.get("url", "")}
                    )
    if not rows:
        raise RuntimeError("Tavily returned no usable paragraphs")
    return rows


async def main() -> None:
    parser = argparse.ArgumentParser(description="Build and label a real Charismate corpus")
    parser.add_argument("topics", nargs="+")
    parser.add_argument("--per-topic", type=int, default=8)
    parser.add_argument("--name", default="charismate-corpus")
    args = parser.parse_args()
    settings = get_settings()
    rows = await asyncio.to_thread(
        collect_paragraphs,
        settings.require("tavily_api_key"),
        args.topics,
        args.per_topic,
    )
    async with PioneerClient(
        settings.require("pioneer_api_key"), settings.pioneer_base_url
    ) as pioneer:
        inputs = [row["text"] for row in rows]
        ner_result, classification_result = await asyncio.gather(
            pioneer.label_existing_ner(
                ["Core_Subject", "Pain_Point", "Action_Hook"], inputs
            ),
            pioneer.label_existing_classification(
                [
                    "outrage",
                    "excitement",
                    "warning",
                    "confidence",
                ],
                inputs,
            ),
        )
    print(
        json.dumps(
            {
                "corpus_name": args.name,
                "sources": rows,
                "ner_annotations": ner_result,
                "vibe_annotations": classification_result,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
