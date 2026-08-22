from collections.abc import Iterable
from typing import Any

CANONICAL = ("Core_Subject", "Pain_Point", "Emotional_Vibe", "Action_Hook")
VIBE_DISPLAY = {
    "outrage": "Theatrical Outrage",
    "excitement": "Urgent Excitement",
    "warning": "Grim Warning",
    "confidence": "Smug Confidence",
}
ALIASES = {
    "core_subject": "Core_Subject",
    "subject": "Core_Subject",
    "topic": "Core_Subject",
    "pain_point": "Pain_Point",
    "pain": "Pain_Point",
    "problem": "Pain_Point",
    "emotional_vibe": "Emotional_Vibe",
    "emotion": "Emotional_Vibe",
    "vibe": "Emotional_Vibe",
    "action_hook": "Action_Hook",
    "hook": "Action_Hook",
    "call_to_action": "Action_Hook",
    "cta": "Action_Hook",
}


def _canonical_label(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return ALIASES.get(normalized)


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            ranked = sorted(
                value,
                key=lambda item: float(item.get("confidence") or 0),
                reverse=True,
            )
            for item in ranked:
                found = _text(item.get("text") or item.get("value") or item.get("entity"))
                if found:
                    return found
        parts = [text for item in value if (text := _text(item))]
        return parts[0] if parts else None
    if isinstance(value, dict):
        for key in ("text", "value", "entity", "label", "answer", "name"):
            found = _text(value.get(key))
            if found:
                return found
    return None


def _walk(value: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def normalize_inference(result: Any) -> dict[str, str]:
    output: dict[str, str] = {}
    if isinstance(result, dict):
        for key, value in result.items():
            canonical = _canonical_label(key)
            text = _text(value)
            if canonical and text:
                output[canonical] = text

    entity_containers: list[Any] = []
    classification_containers: list[Any] = []
    for key, value in _walk(result):
        canonical = _canonical_label(key)
        text = _text(value)
        if canonical and text and canonical not in output:
            output[canonical] = text
        normalized = key.lower().replace("-", "_")
        if normalized in {"entities", "entity_predictions", "ner", "spans"}:
            entity_containers.append(value)
        if normalized in {"classification", "classifications", "labels", "classes"}:
            classification_containers.append(value)

    for container in entity_containers + classification_containers:
        entries = container if isinstance(container, list) else [container]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            label = (
                entry.get("label")
                or entry.get("type")
                or entry.get("entity_type")
                or entry.get("class")
                or entry.get("name")
            )
            canonical = _canonical_label(label)
            value = (
                entry.get("text")
                or entry.get("value")
                or entry.get("entity")
                or entry.get("prediction")
                or entry.get("answer")
            )
            text = _text(value)
            if canonical and text and canonical not in output:
                output[canonical] = text

    missing = [key for key in CANONICAL if key not in output]
    if missing:
        raise ValueError(
            "Pioneer response did not contain required fields: " + ", ".join(missing)
        )
    normalized = {key: output[key] for key in CANONICAL}
    normalized["Emotional_Vibe"] = VIBE_DISPLAY.get(
        normalized["Emotional_Vibe"].strip().lower(),
        normalized["Emotional_Vibe"],
    )
    return normalized
