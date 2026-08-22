import argparse
import asyncio
import json
import shutil
from pathlib import Path

import httpx

from app.artifacts import DEMO_DIR, copy_file, project_dir, write_json
from app.config import BACKEND_DIR

DEMO_PROMPT = "Why fine-tuning LLMs manually is obsolete with Pioneer AI"
DEMO_VIBE = "A dramatic, wise 18th-century philosopher in an oil painting style"


def parse_sse(raw: str) -> list[dict]:
    events: list[dict] = []
    for block in raw.split("\n\n"):
        for line in block.splitlines():
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload:
                continue
            events.append(json.loads(payload))
    return events


def require_done(events: list[dict], label: str) -> dict:
    errors = [event for event in events if event.get("stage") == "error" or event.get("level") == "error"]
    if errors:
        raise RuntimeError(f"{label} failed: {errors[-1]}")
    done = [event for event in events if event.get("stage") == "done"]
    if not done:
        raise RuntimeError(f"{label} ended without a done event: {events[-3:] if events else []}")
    return done[-1]


async def ensure_driving_video(path: Path) -> Path:
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required to synthesize a demo driving video")
    process = await asyncio.create_subprocess_exec(
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=0x1b140c:s=720x1280:d=10:r=25",
        "-vf",
        (
            "drawbox=x=260:y=180:w=200:h=240:color=0xd4b48c:t=fill,"
            "drawbox=x='260+40*sin(2*PI*t)':y=440:w=80:h=220:color=0xc4a070:t=fill,"
            "drawbox=x='380-40*sin(2*PI*t)':y=440:w=80:h=220:color=0xc4a070:t=fill,"
            "drawbox=x=310:y=140:w=100:h=50:color=0x3a2414:t=fill"
        ),
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(path),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0 or not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg failed to create driving video: {stderr.decode(errors='replace')[-1500:]}")
    return path


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run the live Charismate demo pipeline once")
    parser.add_argument("--api", default="http://127.0.0.1:8003")
    parser.add_argument("--prompt", default=DEMO_PROMPT)
    parser.add_argument("--vibe", default=DEMO_VIBE)
    parser.add_argument("--mode", default="replace", choices=["move", "replace"])
    parser.add_argument("--driving", type=Path, default=BACKEND_DIR / "demo-artifacts" / "_shared" / "driving.mp4")
    args = parser.parse_args()

    driving = await ensure_driving_video(args.driving)
    async with httpx.AsyncClient(timeout=httpx.Timeout(1200.0, connect=30.0)) as client:
        health = await client.get(f"{args.api}/health")
        health.raise_for_status()
        created = await client.post(
            f"{args.api}/api/projects",
            json={"name": "Demo run", "target_prompt": args.prompt, "avatar_vibe": args.vibe},
        )
        created.raise_for_status()
        project_id = created.json()["id"]
        print(f"project_id={project_id}", flush=True)

        script_response = await client.post(
            f"{args.api}/api/generate-script",
            json={
                "target_prompt": args.prompt,
                "avatar_vibe": args.vibe,
                "project_id": project_id,
            },
        )
        script_response.raise_for_status()
        script_events = parse_sse(script_response.text)
        script_done = require_done(script_events, "generate")
        payload = script_done.get("payload") or {}
        audio_url = payload.get("audio_url")
        if not audio_url:
            raise RuntimeError(f"generate-script done event missing audio_url: {script_done}")
        write_json(project_id, "generate-events.json", script_events)
        print(json.dumps({"script": payload.get("script"), "entities": payload.get("entities")}, indent=2), flush=True)

        with driving.open("rb") as handle:
            render_response = await client.post(
                f"{args.api}/api/render-video",
                data={
                    "avatar_vibe": args.vibe,
                    "audio_url": audio_url,
                    "mode": args.mode,
                    "project_id": project_id,
                },
                files={"driving_video": ("driving.mp4", handle, "video/mp4")},
            )
        render_response.raise_for_status()
        render_events = parse_sse(render_response.text)
        render_done = require_done(render_events, "render")
        write_json(project_id, "render-events.json", render_events)
        print(json.dumps(render_done.get("payload"), indent=2), flush=True)

    latest = DEMO_DIR / "latest"
    if latest.is_symlink() or latest.exists():
        latest.unlink() if latest.is_symlink() or latest.is_file() else shutil.rmtree(latest)
    latest.symlink_to(project_dir(project_id), target_is_directory=True)
    copy_file(project_id, "driving-source.mp4", driving)
    print(f"artifacts={project_dir(project_id)}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
