import json
import shutil
from pathlib import Path
from typing import Any

import httpx

from app.config import BACKEND_DIR

DEMO_DIR = BACKEND_DIR / "demo-artifacts"


def project_dir(project_id: str) -> Path:
    path = DEMO_DIR / project_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(project_id: str, name: str, payload: Any) -> Path:
    path = project_dir(project_id) / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return path


def write_text(project_id: str, name: str, text: str) -> Path:
    path = project_dir(project_id) / name
    path.write_text(text if text.endswith("\n") else text + "\n")
    return path


def copy_file(project_id: str, name: str, source: Path) -> Path:
    destination = project_dir(project_id) / name
    shutil.copy2(source, destination)
    return destination


async def save_url(project_id: str, name: str, url: str, timeout: float = 180) -> Path:
    destination = project_dir(project_id) / name
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        destination.write_bytes(response.content)
    if destination.stat().st_size == 0:
        raise RuntimeError(f"Downloaded empty artifact for {name}")
    return destination
