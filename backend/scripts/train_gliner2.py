import argparse
import asyncio
import json
from itertools import zip_longest
from typing import Any

from pathlib import Path

from app.config import BACKEND_DIR, get_settings
from app.pioneer.finetune import PioneerClient, PioneerError

try:
    from scripts.seed_corpus import collect_paragraphs
except ImportError:
    from seed_corpus import collect_paragraphs

NER_LABELS = ["Core_Subject", "Pain_Point", "Action_Hook"]
MARKET_TOPICS = {
    "b2b_sales": [
        "hyper-personalized B2B video sales outreach at scale",
        "extract a prospect tech stack and pain point from CRM notes",
        "1-to-1 video pitches from a sales rep photo",
        "outbound teams drowning in generic email sequences",
        "bespoke SaaS demo videos for each account",
        "send thousands of personalized sales videos a day",
        "why cold email fails and personalized video converts",
        "AI sales avatars closing enterprise deals with custom pitches",
    ],
    "edtech": [
        "historical figures teaching interactive lessons from primary sources",
        "parse historical texts into people places and events for class avatars",
        "AI tutors that roleplay Socrates Lincoln or Cleopatra",
        "teachers spend hours preparing history lesson plans by hand",
        "dynamic EdTech lessons generated from unstructured textbooks",
        "interactive history education with talking historical avatars",
        "extract entities from historical documents for teaching",
        "personalized history lessons created on the fly",
    ],
    "media": [
        "breaking news triggers for automated short-form video",
        "brand avatars publish viral shorts 24/7 without a crew",
        "autonomous media channels from news entity extraction",
        "newsrooms cannot keep up with 24 hour short-form demand",
        "AI news anchors reacting to breaking stories",
        "extract people companies and events from breaking news",
        "always-on social video channel without a production crew",
        "turn wire stories into TikTok and YouTube Shorts automatically",
    ],
}
CACHE_PATH = BACKEND_DIR / "data" / "charismate-tavily-markets.jsonl"
DOMAIN = (
    "Three Charismate markets: hyper-personalized B2B sales videos, interactive "
    "EdTech lessons with historical figures, and autonomous media channels that "
    "turn breaking news into shorts. Each passage names a product, person, "
    "company, or story, a concrete costly or slow workflow, and a next action."
)


def interleaved_topics(markets: dict[str, list[str]] | None = None) -> list[str]:
    buckets = list((markets or MARKET_TOPICS).values())
    topics: list[str] = []
    for group in zip_longest(*buckets):
        topics.extend(topic for topic in group if topic)
    return topics


def identifier(payload: dict[str, Any], label: str) -> str:
    value = payload.get(f"{label}_id") or payload.get("id") or payload.get("job_id")
    if not value:
        raise RuntimeError(f"Pioneer {label} response did not include an identifier: {payload}")
    return str(value)


def write_model_id(model_id: str) -> None:
    path = BACKEND_DIR / ".env.local"
    lines = path.read_text().splitlines() if path.exists() else []
    replacement = f"PIONEER_MODEL_ID={model_id}"
    updated: list[str] = []
    found = False
    for line in lines:
        if line.startswith("PIONEER_MODEL_ID="):
            if not found:
                updated.append(replacement)
                found = True
        else:
            updated.append(line)
    if not found:
        updated.append(replacement)
    path.write_text("\n".join(updated).rstrip() + "\n")


def extract_ner_seeds(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("data")
    if not isinstance(rows, list):
        return []
    seeds: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = row.get("text") or row.get("input") or row.get("source")
        if not isinstance(text, str) or not text.strip():
            continue
        entities = _entity_pairs(row.get("entities") or row.get("spans") or [])
        if not entities:
            continue
        seeds.append({"text": text.strip(), "entities": entities})
    return seeds


def _entity_pairs(raw: Any) -> list[list[str]]:
    pairs: list[list[str]] = []
    if isinstance(raw, dict):
        for label, items in raw.items():
            if label not in NER_LABELS:
                continue
            values = items if isinstance(items, list) else [items]
            for item in values:
                span = item.get("text") if isinstance(item, dict) else item
                if isinstance(span, str) and span.strip():
                    pairs.append([span.strip(), label])
        return pairs
    if not isinstance(raw, list):
        return []
    for item in raw:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            span, label = str(item[0]).strip(), str(item[1]).strip()
        elif isinstance(item, dict):
            span = str(
                item.get("text") or item.get("span") or item.get("entity") or ""
            ).strip()
            label = str(
                item.get("label") or item.get("type") or item.get("entity_type") or ""
            ).strip()
        else:
            continue
        if span and label in NER_LABELS:
            pairs.append([span, label])
    return pairs


def _inference_entity_map(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    candidates = [result]
    for key in ("result", "data"):
        value = result.get(key)
        if isinstance(value, dict):
            candidates.append(value)
            nested = value.get("data")
            if isinstance(nested, dict):
                candidates.append(nested)
    for candidate in candidates:
        entities = candidate.get("entities")
        if isinstance(entities, dict):
            return entities
    return {}


def _span_in_text(text: str, item: Any) -> str | None:
    if isinstance(item, str) and item and item in text:
        return item
    if not isinstance(item, dict):
        return None
    claimed = item.get("text") or item.get("span") or item.get("entity")
    if isinstance(claimed, str) and claimed:
        index = text.find(claimed)
        if index < 0:
            index = text.lower().find(claimed.lower())
        if index >= 0:
            return text[index : index + len(claimed)]
        return None
    start, end = item.get("start"), item.get("end")
    if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text):
        return text[start:end]
    return None


def entities_from_inference(text: str, result: Any) -> list[list[str]]:
    pairs: list[list[str]] = []
    for label, items in _inference_entity_map(result).items():
        if label not in NER_LABELS:
            continue
        values = items if isinstance(items, list) else [items]
        for item in values:
            span = _span_in_text(text, item)
            if span:
                pairs.append([span, label])
    return pairs


def align_inference_rows(texts: list[str], payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    result = payload.get("result", payload)
    if isinstance(result, list) and len(result) == len(texts):
        return [
            {"text": text, "entities": entities_from_inference(text, item)}
            for text, item in zip(texts, result)
        ]
    if isinstance(result, dict):
        data = result.get("data")
        if isinstance(data, list) and len(data) == len(texts):
            return [
                {"text": text, "entities": entities_from_inference(text, item)}
                for text, item in zip(texts, data)
            ]
        if len(texts) == 1:
            return [{"text": texts[0], "entities": entities_from_inference(texts[0], result)}]
    return None


def load_cached_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if isinstance(row, dict) and isinstance(row.get("text"), str):
            rows.append(row)
    return rows


def merge_unique_rows(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in groups:
        for row in group:
            text = str(row.get("text", "")).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            merged.append(row)
    return merged


def to_ner_jsonl(rows: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps({"text": row["text"], "entities": row["entities"]}, ensure_ascii=False) + "\n"
        for row in rows
    )


def valid_preview_rows(preview: dict[str, Any]) -> list[dict[str, Any]]:
    rows = preview.get("rows")
    if not isinstance(rows, list):
        return []
    valid: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = row.get("text") or row.get("input")
        entities = row.get("entities") or row.get("spans")
        if isinstance(text, str) and text.strip() and entities:
            valid.append(row)
    return valid


async def wait_dataset_ready(client: PioneerClient, name: str) -> dict[str, Any]:
    deadline = asyncio.get_running_loop().time() + 900
    while True:
        detail = await client.dataset(name)
        versions = detail.get("versions") if isinstance(detail.get("versions"), list) else []
        ready = [
            version
            for version in versions
            if isinstance(version, dict) and str(version.get("status", "")).lower() == "ready"
        ]
        failed = [
            version
            for version in versions
            if isinstance(version, dict) and str(version.get("status", "")).lower() == "failed"
        ]
        if ready:
            return detail
        if failed and not any(
            str(version.get("status", "")).lower() in {"initialized", "uploading", "converting", "validating", "generating"}
            for version in versions
            if isinstance(version, dict)
        ):
            raise RuntimeError(f"Dataset {name} failed: {detail}")
        if asyncio.get_running_loop().time() >= deadline:
            raise TimeoutError(f"Timed out waiting for dataset {name}")
        await asyncio.sleep(5)


async def dataset_has_labeled_rows(client: PioneerClient, name: str) -> bool:
    preview = await client.request("GET", f"/felix/datasets/{name}/latest/preview")
    valid = valid_preview_rows(preview)
    print(
        json.dumps(
            {
                "dataset": name,
                "preview_rows": len(preview.get("rows") or []),
                "valid_preview_rows": len(valid),
                "sample": valid[:2],
            },
            indent=2,
        ),
        flush=True,
    )
    return bool(valid)


INFERENCE_SCHEMA = {
    "entities": {
        "Core_Subject": "The central product, technology, or idea being discussed",
        "Pain_Point": "A concrete problem, costly workflow, or frustration",
        "Action_Hook": "A recommended next step, solution, or call to action",
    }
}


async def label_texts_with_inference(
    client: PioneerClient,
    texts: list[str],
    batch_size: int = 15,
) -> list[dict[str, Any]]:
    settings = get_settings()
    model_id = settings.pioneer_model_id or "fastino/gliner2-base-v1"
    labeled: list[dict[str, Any]] = []
    for offset in range(0, len(texts), batch_size):
        chunk = texts[offset : offset + batch_size]
        payload = {
            "model_id": model_id,
            "text": chunk if len(chunk) > 1 else chunk[0],
            "schema": INFERENCE_SCHEMA,
            "threshold": 0.2,
            "include_confidence": True,
            "include_spans": True,
            "store": False,
        }
        try:
            result = await client.inference(payload)
            aligned = align_inference_rows(chunk, result)
        except PioneerError as error:
            print(f"Batch inference failed, falling back per row: {error}", flush=True)
            aligned = None
        if aligned is None:
            aligned = []
            for text in chunk:
                single = await client.inference({**payload, "text": text})
                rows = align_inference_rows([text], single)
                if not rows:
                    raise RuntimeError(f"Could not align Pioneer inference for: {text[:80]}")
                aligned.extend(rows)
        labeled.extend(aligned)
        print(
            f"Labeled {min(offset + len(chunk), len(texts))}/{len(texts)} Tavily paragraphs",
            flush=True,
        )
    return labeled


async def seed_from_tavily(
    client: PioneerClient,
    name: str,
    topics: list[str],
    per_topic: int,
    *,
    target_rows: int = 500,
) -> tuple[str, list[dict[str, Any]]]:
    cached = load_cached_rows(CACHE_PATH)
    cached_texts = {str(row["text"]).strip() for row in cached}
    print(f"Cache has {len(cached)} rows ({sum(1 for row in cached if row.get('entities'))} labeled)", flush=True)
    rows = await asyncio.to_thread(
        collect_paragraphs,
        get_settings().require("tavily_api_key"),
        topics,
        per_topic,
        include_raw_content=False,
    )
    texts: list[str] = []
    seen = set(cached_texts)
    for row in rows:
        text = row["text"].strip()
        if text not in seen:
            seen.add(text)
            texts.append(text)
    needed = max(target_rows * 2 - len(cached), 0)
    texts = texts[:needed]
    print(
        f"Collected {len(texts)} new unique Tavily paragraphs to label (capped at {needed})",
        flush=True,
    )
    inferred = await label_texts_with_inference(client, texts) if texts else []
    merged = merge_unique_rows(cached, inferred)
    positives = [row for row in merged if row.get("entities")]
    negatives = [row for row in merged if not row.get("entities")]
    extra_negatives = max(1, min(len(negatives), len(positives) // 5))
    seeds = positives + negatives[:extra_negatives]
    if len(seeds) > target_rows:
        seeds = seeds[:target_rows]
        positives = [row for row in seeds if row.get("entities")]
    print(
        f"Dataset now has {len(positives)} labeled rows and {len(seeds) - len(positives)} negatives "
        f"(target {target_rows})",
        flush=True,
    )
    if len(positives) < 50:
        raise RuntimeError("Pioneer inference produced too few Tavily rows with in-text entity spans")
    jsonl = to_ner_jsonl(seeds)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(jsonl)
    uploaded = await client.upload_ner_jsonl(name, jsonl)
    print(json.dumps({"uploaded": name, "rows": len(seeds), "meta": uploaded}, default=str), flush=True)
    await wait_dataset_ready(client, name)
    if not await dataset_has_labeled_rows(client, name):
        raise RuntimeError(f"Uploaded Tavily dataset {name} has no valid text/entity rows")
    return name, positives


async def generate_from_seeds(
    client: PioneerClient,
    name: str,
    seeds: list[dict[str, Any]],
    count: int,
) -> str:
    result = await client.generate(
        {
            "task_type": "ner",
            "dataset_name": name,
            "labels": NER_LABELS,
            "num_examples": count,
            "domain_description": DOMAIN,
            "classified_examples": seeds[:20],
            "quality": "medium",
        }
    )
    job_id = identifier(result, "job")
    print(json.dumps({"generation_job_id": job_id, "dataset": name}), flush=True)
    await client.poll_job(job_id)
    await wait_dataset_ready(client, name)
    if not await dataset_has_labeled_rows(client, name):
        raise RuntimeError(f"Seeded generation {name} produced no valid rows")
    return name


async def generate_dataset(
    client: PioneerClient,
    name: str,
    task: str,
    count: int,
    *,
    held_out: bool = False,
) -> str:
    try:
        existing = await client.dataset(name)
        versions = existing.get("versions") if isinstance(existing.get("versions"), list) else []
        if any(
            str(version.get("status", "")).lower() == "ready"
            for version in versions
            if isinstance(version, dict)
        ):
            print(f"Reusing ready dataset: {name}", flush=True)
            return name
    except PioneerError:
        pass

    labels = (
        NER_LABELS
        if task == "ner"
        else ["outrage", "excitement", "warning", "confidence"]
    )
    payload: dict[str, Any] = {
        "task_type": task,
        "dataset_name": name,
        "labels": labels,
        "num_examples": count,
        "domain_description": (
            "Held-out evaluation examples, distinct from training, of " if held_out else ""
        )
        + (
            "B2B AI and developer-tool launch announcements, technical comparisons, "
            "and short pitch copy. Each passage names a central product or technology, "
            "describes a concrete slow or expensive manual workflow as the pain point, "
            "and contains a direct recommendation or next action. Copy ranges from "
            "theatrical outrage and urgent excitement to grim warning and smug confidence."
        ),
    }
    if task == "classification":
        payload["classified_examples"] = [
            {"text": "Fools! Manual pipelines are devouring your budget alive.", "label": "outrage"},
            {"text": "Hark! Your team still hand-labels data while rivals automate everything.", "label": "outrage"},
            {"text": "Ship in minutes—this agent turns your raw data into a trained model today!", "label": "excitement"},
            {"text": "The breakthrough is here; switch on Agent Mode and move now!", "label": "excitement"},
            {"text": "Keep tuning by hand and your competitors will leave you permanently behind.", "label": "warning"},
            {"text": "That brittle pipeline is one failed run away from missing the launch.", "label": "warning"},
            {"text": "While they wrestle YAML, we press one button and ship the better model.", "label": "confidence"},
            {"text": "Manual tuning takes days; ours finishes before the meeting ends.", "label": "confidence"},
        ]
    result = await client.generate(payload)
    job_id = identifier(result, "job")
    await client.poll_job(job_id)
    detail = await client.dataset(name)
    state = str(detail.get("status") or detail.get("state") or "").lower()
    versions = detail.get("versions") if isinstance(detail.get("versions"), list) else []
    if state != "ready" and not any(
        str(version.get("status", "")).lower() == "ready"
        for version in versions
        if isinstance(version, dict)
    ):
        raise RuntimeError(f"Dataset {name} did not become ready: {detail}")
    return name


async def main() -> None:
    parser = argparse.ArgumentParser(description="Train Charismate multi-head GLiNER2 LoRA")
    parser.add_argument("--ner-examples", type=int, default=300)
    parser.add_argument("--classification-examples", type=int, default=200)
    parser.add_argument("--held-out", type=int, default=100)
    parser.add_argument(
        "--ner-only",
        action="store_true",
        help="Train only the extraction head when Pioneer classification generation is unavailable.",
    )
    parser.add_argument(
        "--from-tavily",
        action="store_true",
        help="Seed Pioneer NER generation from real Tavily passages.",
    )
    parser.add_argument("--per-topic", type=int, default=8)
    parser.add_argument("--target-rows", type=int, default=500)
    args = parser.parse_args()
    settings = get_settings()
    async with PioneerClient(
        settings.require("pioneer_api_key"),
        settings.pioneer_base_url,
        timeout=300,
    ) as pioneer:
        heldout_id = None
        if args.from_tavily:
            ner_id, _seeds = await seed_from_tavily(
                pioneer,
                "charismate-tavily-markets",
                interleaved_topics(),
                args.per_topic,
                target_rows=args.target_rows,
            )
        else:
            ner_id = await generate_dataset(
                pioneer, "charismate-pitch-ner", "ner", args.ner_examples
            )
        classification_id = None
        if not args.ner_only:
            classification_id = await generate_dataset(
                pioneer,
                "charismate-vibe-cls",
                "classification",
                args.classification_examples,
            )
        if not args.from_tavily:
            heldout_id = await generate_dataset(
                pioneer, "charismate-heldout-ner", "ner", args.held_out, held_out=True
            )
        datasets = [{"name": ner_id}]
        if classification_id:
            datasets.append({"name": classification_id})
        training = await pioneer.launch_training(
            {
                "model_name": "charismate-gliner2-v3",
                "base_model": "fastino/gliner2-base-v1",
                "datasets": datasets,
                "training_type": "lora",
                "nr_epochs": 5,
                "learning_rate": 5e-5,
            }
        )
        model_id = identifier(training, "job")
        trained = await pioneer.poll_training(model_id, timeout=7200)

        metrics: dict[str, Any] = {"model_id": model_id, "training": trained.get("metrics", {})}
        for label, candidate in (
            ("tuned", model_id),
            ("base", "fastino/gliner2-base-v1"),
        ):
            if not heldout_id:
                continue
            try:
                evaluation = await pioneer.launch_evaluation(
                    {
                        "base_model": candidate,
                        "dataset_name": heldout_id,
                    }
                )
                evaluations = evaluation.get("evaluations")
                evaluation_id = (
                    str(evaluations[0]["id"])
                    if isinstance(evaluations, list)
                    and evaluations
                    and isinstance(evaluations[0], dict)
                    and evaluations[0].get("id")
                    else identifier(evaluation, "evaluation")
                )
                metrics[label] = await pioneer.poll_evaluation(
                    evaluation_id, timeout=3600
                )
            except PioneerError as error:
                metrics[label] = {"unsupported_or_failed": str(error)}

    write_model_id(str(model_id))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
