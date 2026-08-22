import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

import aiosqlite

from app.config import BACKEND_DIR, get_settings

JSON_COLUMNS = {
    "projects": {"research", "extracted", "metadata"},
    "events": {"payload"},
    "avatars": {"metadata"},
    "templates": {"prompt", "metadata"},
    "wallet": {"metadata"},
}

BUILTIN_TEMPLATES = [
    {
        "id": "bold-founder",
        "name": "Bold Founder",
        "description": "Direct, energetic founder-led short-form pitch.",
        "prompt": {"avatar_vibe": "confident, warm, concise", "style": "founder pitch"},
    },
    {
        "id": "trusted-expert",
        "name": "Trusted Expert",
        "description": "Credible educational delivery focused on a clear insight.",
        "prompt": {"avatar_vibe": "calm, authoritative, approachable", "style": "expert explainer"},
    },
    {
        "id": "social-native",
        "name": "Social Native",
        "description": "Fast, conversational delivery with an immediate hook.",
        "prompt": {"avatar_vibe": "playful, spontaneous, expressive", "style": "social short"},
    },
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _json_dump(value: Any) -> str | None:
    return None if value is None else json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def row_to_dict(row: aiosqlite.Row | None, table: str) -> dict[str, Any] | None:
    if row is None:
        return None
    item = dict(row)
    for key in JSON_COLUMNS.get(table, set()):
        value = item.get(key)
        if value is None or isinstance(value, (dict, list)):
            continue
        try:
            item[key] = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            item[key] = {"_raw": value, "_parse_error": True}
    return item


@asynccontextmanager
async def connect() -> AsyncIterator[aiosqlite.Connection]:
    path = Path(get_settings().database_path)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        yield db


async def initialize() -> None:
    async with connect() as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                target_prompt TEXT,
                avatar_vibe TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                script TEXT,
                audio_url TEXT,
                avatar_image_url TEXT,
                driving_video_url TEXT,
                video_url TEXT,
                final_video_url TEXT,
                research TEXT,
                extracted TEXT,
                metadata TEXT,
                render_duration_seconds REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                stage TEXT NOT NULL,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                payload TEXT,
                timestamp TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_project_timestamp
                ON events(project_id, timestamp);
            CREATE TABLE IF NOT EXISTS avatars (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                vibe TEXT,
                image_url TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                prompt TEXT NOT NULL,
                metadata TEXT,
                built_in INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS wallet (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                credits REAL NOT NULL DEFAULT 1000,
                spent REAL NOT NULL DEFAULT 0,
                metadata TEXT,
                updated_at TEXT NOT NULL
            );
            """
        )
        now = utc_now()
        for template in BUILTIN_TEMPLATES:
            await db.execute(
                """INSERT OR IGNORE INTO templates
                   (id,name,description,prompt,metadata,built_in,created_at)
                   VALUES (?,?,?,?,?,1,?)""",
                (
                    template["id"],
                    template["name"],
                    template["description"],
                    _json_dump(template["prompt"]),
                    _json_dump({"product_preset": True}),
                    now,
                ),
            )
        await db.execute(
            "INSERT OR IGNORE INTO wallet (id,credits,spent,metadata,updated_at) VALUES (1,1000,0,?,?)",
            (_json_dump({}), now),
        )
        await db.execute(
            "UPDATE wallet SET credits = 1000 WHERE id = 1 AND credits = 0"
        )
        await db.commit()


async def list_rows(table: str, order_by: str = "created_at DESC") -> list[dict[str, Any]]:
    if table not in JSON_COLUMNS:
        raise ValueError("Unsupported table")
    async with connect() as db:
        cursor = await db.execute(f"SELECT * FROM {table} ORDER BY {order_by}")
        return [row_to_dict(row, table) for row in await cursor.fetchall()]  # type: ignore[misc]


async def get_row(table: str, row_id: str | int) -> dict[str, Any] | None:
    if table not in JSON_COLUMNS:
        raise ValueError("Unsupported table")
    async with connect() as db:
        cursor = await db.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,))
        return row_to_dict(await cursor.fetchone(), table)


async def delete_row(table: str, row_id: str) -> bool:
    if table not in {"projects", "avatars", "templates"}:
        raise ValueError("Unsupported table")
    async with connect() as db:
        cursor = await db.execute(f"DELETE FROM {table} WHERE id = ?", (row_id,))
        await db.commit()
        return cursor.rowcount > 0


async def create_project(data: dict[str, Any]) -> dict[str, Any]:
    project_id = data.get("id") or str(uuid4())
    now = utc_now()
    values = {
        "id": project_id,
        "name": data.get("name") or "Untitled project",
        "target_prompt": data.get("target_prompt"),
        "avatar_vibe": data.get("avatar_vibe"),
        "status": data.get("status", "draft"),
        "metadata": _json_dump(data.get("metadata", {})),
        "created_at": now,
        "updated_at": now,
    }
    async with connect() as db:
        await db.execute(
            """INSERT INTO projects
               (id,name,target_prompt,avatar_vibe,status,metadata,created_at,updated_at)
               VALUES (:id,:name,:target_prompt,:avatar_vibe,:status,:metadata,:created_at,:updated_at)""",
            values,
        )
        await db.commit()
    return (await get_row("projects", project_id))  # type: ignore[return-value]


PROJECT_FIELDS = {
    "name", "target_prompt", "avatar_vibe", "status", "script", "audio_url",
    "avatar_image_url", "driving_video_url", "video_url", "final_video_url",
    "research", "extracted", "metadata", "render_duration_seconds",
}


async def update_project(project_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    values = {key: value for key, value in changes.items() if key in PROJECT_FIELDS}
    for key in ("research", "extracted", "metadata"):
        if key in values:
            values[key] = _json_dump(values[key])
    if not values:
        return await get_row("projects", project_id)
    values["updated_at"] = utc_now()
    values["id"] = project_id
    assignments = ", ".join(f"{key} = :{key}" for key in values if key != "id")
    async with connect() as db:
        await db.execute(f"UPDATE projects SET {assignments} WHERE id = :id", values)
        await db.commit()
    return await get_row("projects", project_id)


async def add_event(project_id: str, event: dict[str, Any]) -> dict[str, Any]:
    event_id = str(uuid4())
    timestamp = event.get("timestamp") or utc_now()
    async with connect() as db:
        await db.execute(
            """INSERT INTO events (id,project_id,stage,level,message,payload,timestamp)
               VALUES (?,?,?,?,?,?,?)""",
            (
                event_id, project_id, event["stage"], event["level"], event["message"],
                _json_dump(event.get("payload")), timestamp,
            ),
        )
        await db.commit()
    return {**event, "id": event_id, "project_id": project_id, "timestamp": timestamp}


async def get_project_with_events(project_id: str) -> dict[str, Any] | None:
    project = await get_row("projects", project_id)
    if project is None:
        return None
    async with connect() as db:
        cursor = await db.execute(
            "SELECT * FROM events WHERE project_id = ? ORDER BY timestamp", (project_id,)
        )
        project["events"] = [
            row_to_dict(row, "events") for row in await cursor.fetchall()
        ]
    return project


async def insert_named_resource(table: str, data: dict[str, Any]) -> dict[str, Any]:
    row_id = data.get("id") or str(uuid4())
    now = utc_now()
    async with connect() as db:
        if table == "avatars":
            await db.execute(
                "INSERT INTO avatars (id,name,vibe,image_url,metadata,created_at) VALUES (?,?,?,?,?,?)",
                (row_id, data["name"], data.get("vibe"), data["image_url"], _json_dump(data.get("metadata", {})), now),
            )
        elif table == "templates":
            await db.execute(
                """INSERT INTO templates
                   (id,name,description,prompt,metadata,built_in,created_at)
                   VALUES (?,?,?,?,?,0,?)""",
                (row_id, data["name"], data.get("description"), _json_dump(data["prompt"]), _json_dump(data.get("metadata", {})), now),
            )
        else:
            raise ValueError("Unsupported resource")
        await db.commit()
    return (await get_row(table, row_id))  # type: ignore[return-value]


async def wallet_adjust(spent_delta: float, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    async with connect() as db:
        await db.execute(
            """UPDATE wallet SET spent = spent + ?, metadata = ?, updated_at = ? WHERE id = 1""",
            (spent_delta, _json_dump(metadata or {}), utc_now()),
        )
        await db.commit()
    return (await get_row("wallet", 1))  # type: ignore[return-value]


async def dashboard_stats() -> dict[str, Any]:
    async with connect() as db:
        project_counts = await (
            await db.execute(
                "SELECT COUNT(*) total, SUM(status='completed') completed, SUM(status='failed') failed FROM projects"
            )
        ).fetchone()
        avatar_count = await (await db.execute("SELECT COUNT(*) count FROM avatars")).fetchone()
        wallet = row_to_dict(await (await db.execute("SELECT * FROM wallet WHERE id=1")).fetchone(), "wallet")
    return {
        "projects": {
            "total": project_counts["total"] or 0,
            "completed": project_counts["completed"] or 0,
            "failed": project_counts["failed"] or 0,
        },
        "avatars": avatar_count["count"] or 0,
        "wallet": wallet,
    }
