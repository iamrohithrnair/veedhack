import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.artifacts import DEMO_DIR

router = APIRouter(prefix="/api/showcase")

ALLOWED_FILES = {
    "audio.mp3": "audio/mpeg",
    "avatar.png": "image/png",
    "driving.mp4": "video/mp4",
    "intermediate.mp4": "video/mp4",
    "final.mp4": "video/mp4",
}

TOPIC = "Why fine-tuning LLMs manually is obsolete with Pioneer AI."
VIBE = "A dramatic, wise 18th-century philosopher in an oil painting style."


def _project_dir() -> Path:
    latest = DEMO_DIR / "latest"
    if latest.exists():
        return latest.resolve()
    runs = sorted(
        (path for path in DEMO_DIR.iterdir() if path.is_dir() and path.name != "_shared"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not runs:
        raise HTTPException(404, "No showcase run is available yet")
    return runs[0]


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text())
    return payload if isinstance(payload, dict) else {}


@router.get("")
@router.get("/")
async def get_showcase() -> dict:
    folder = _project_dir()
    pipeline = _read_json(folder / "script-pipeline.json")
    extracted = _read_json(folder / "extracted.json") or pipeline.get("entities") or {}
    script = ""
    script_file = folder / "script.txt"
    if script_file.exists():
        script = script_file.read_text().strip()
    elif isinstance(pipeline.get("script"), str):
        script = pipeline["script"]
    files = {name: f"/api/showcase/files/{name}" for name in ALLOWED_FILES if (folder / name).exists()}
    return {
        "project_id": folder.name,
        "name": "Pioneer Pitch",
        "topic": TOPIC,
        "avatar_vibe": VIBE,
        "tone": "theatrical",
        "script": script,
        "entities": extracted,
        "files": files,
    }


@router.get("/files/{name}")
async def showcase_file(name: str) -> FileResponse:
    if name not in ALLOWED_FILES:
        raise HTTPException(404, "Unknown showcase file")
    path = _project_dir() / name
    if not path.exists():
        raise HTTPException(404, f"Showcase file {name} is missing")
    return FileResponse(path, media_type=ALLOWED_FILES[name], filename=name)
