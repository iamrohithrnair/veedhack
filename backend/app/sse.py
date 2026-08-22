import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from app.db import add_event

logger = logging.getLogger(__name__)


def make_event(
    stage: str,
    level: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "stage": stage,
        "level": level,
        "message": message,
        "payload": payload or {},
        "timestamp": datetime.now(UTC).isoformat(),
    }


def format_sse(event: dict[str, Any]) -> dict[str, str]:
    return {
        "event": event.get("stage", "message"),
        "data": json.dumps(event, ensure_ascii=False, separators=(",", ":"), default=str),
    }


async def emit(project_id: str, event: dict[str, Any]) -> dict[str, str]:
    await add_event(project_id, event)
    return format_sse(event)


async def emit_error(project_id: str, stage: str, error: Exception) -> dict[str, str]:
    logger.exception("Pipeline stage failed for project %s", project_id)
    error_type = type(error).__name__
    if error_type == "PioneerError":
        message = "Pioneer request failed. Check the API key, billing status, and server logs."
    elif isinstance(error, ValueError):
        message = str(error)
    else:
        message = "Pipeline stage failed. Check the server logs for provider details."
    return await emit(
        project_id,
        make_event(stage, "error", message, {"error_type": error_type}),
    )
