import asyncio
import os
import shutil
import tempfile
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env.local", override=False)

import fal_client
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sse_starlette.sse import EventSourceResponse

from app import db
from app.artifacts import copy_file, save_url, write_json
from app.config import get_settings
from app.jobs import spawn
from app.sse import emit, emit_error, make_event

router = APIRouter(prefix="/api")


def _valid_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _find_url(value: Any, preferred: tuple[str, ...]) -> str | None:
    if isinstance(value, str) and _valid_url(value):
        return value
    if isinstance(value, dict):
        for key in preferred:
            found = _find_url(value.get(key), preferred)
            if found:
                return found
        for child in value.values():
            found = _find_url(child, preferred)
            if found:
                return found
    if isinstance(value, list):
        for child in value:
            found = _find_url(child, preferred)
            if found:
                return found
    return None


def _reported_cost(value: Any) -> float:
    if isinstance(value, dict):
        total = 0.0
        for key, child in value.items():
            if key.lower() in {"cost", "credits_used", "price"} and isinstance(child, (int, float)):
                total += float(child)
            elif isinstance(child, (dict, list)):
                total += _reported_cost(child)
        return total
    if isinstance(value, list):
        return sum(_reported_cost(child) for child in value)
    return 0.0


def _queue_payload(update: Any) -> dict[str, Any]:
    if hasattr(update, "model_dump"):
        return update.model_dump(mode="json")
    if hasattr(update, "__dict__"):
        return {key: str(value) for key, value in vars(update).items() if not key.startswith("_")}
    return {"update": str(update)}


async def _fal_updates(
    model: str,
    arguments: dict[str, Any],
    timeout: float,
) -> AsyncIterator[tuple[str, Any]]:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

    def callback(update: Any) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, ("progress", _queue_payload(update)))

    async def invoke() -> None:
        try:
            result = await asyncio.wait_for(
                fal_client.subscribe_async(
                    model,
                    arguments=arguments,
                    with_logs=True,
                    on_queue_update=callback,
                ),
                timeout=timeout,
            )
            await queue.put(("result", result))
        except Exception as error:
            await queue.put(("error", error))

    task = asyncio.create_task(invoke())
    try:
        while True:
            kind, value = await queue.get()
            yield kind, value
            if kind in {"result", "error"}:
                break
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def _transcode(source: Path, destination: Path) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        if source.suffix.lower() != ".mp4":
            raise RuntimeError("ffmpeg is not installed; driving_video must already be an MP4")
        return source
    process = await asyncio.create_subprocess_exec(
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(destination),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0 or not destination.exists() or destination.stat().st_size == 0:
        detail = stderr.decode(errors="replace")[-2000:]
        raise RuntimeError(f"ffmpeg failed to transcode driving video: {detail}")
    return destination


async def _execute_render_pipeline(
    *,
    project_id: str,
    avatar_vibe: str,
    audio_url: str,
    mode: Literal["move", "replace"],
    avatar_image_url: str | None,
    source_path: Path,
    queue: asyncio.Queue[dict[str, str] | None] | None = None,
) -> None:
    settings = get_settings()
    temp_dir = source_path.parent
    transcoded = temp_dir / "driving-video.mp4"
    started = time.monotonic()
    reported_cost = 0.0

    async def send_event(event: dict[str, str]) -> None:
        if queue is not None:
            await queue.put(event)

    try:
        if not _valid_url(audio_url):
            raise ValueError("audio_url must be a public HTTP(S) URL")
        fal_key = settings.require("fal_key")
        os.environ["FAL_KEY"] = fal_key
        await db.update_project(project_id, {"status": "rendering", "avatar_vibe": avatar_vibe})
        await send_event(await emit(project_id, make_event("upload", "info", "Preparing driving video")))

        upload_path = await _transcode(source_path, transcoded)
        copy_file(project_id, "driving.mp4", upload_path)
        driving_url = await fal_client.upload_file_async(str(upload_path))
        if not _valid_url(driving_url):
            raise RuntimeError("fal upload did not return a valid driving video URL")
        await db.update_project(project_id, {"driving_video_url": driving_url})
        await send_event(
            await emit(
                project_id,
                make_event("upload", "success", "Driving video uploaded", {"driving_video_url": driving_url}),
            )
        )

        image_url = avatar_image_url
        generated_avatar = image_url is None
        if image_url is not None and not _valid_url(image_url):
            raise ValueError("avatar_image_url must be a public HTTP(S) URL")
        if image_url is None:
            await send_event(await emit(project_id, make_event("avatar", "info", "Generating avatar image")))
            image_result: Any = None
            async for kind, value in _fal_updates(
                settings.fal_image_model,
                {
                    "prompt": (
                        "Photorealistic charismatic presenter, centered waist-up portrait, "
                        f"clean studio lighting, direct eye contact, personality: {avatar_vibe}"
                    ),
                    "num_images": 1,
                },
                settings.pipeline_timeout_seconds,
            ):
                if kind == "progress":
                    await send_event(await emit(project_id, make_event("avatar", "info", "Avatar generation progress", value)))
                elif kind == "error":
                    raise value
                else:
                    image_result = value
            image_url = _find_url(image_result, ("url", "images", "image"))
            if not _valid_url(image_url):
                raise RuntimeError("Avatar generation returned no valid image URL")
            reported_cost += _reported_cost(image_result)
        if generated_avatar:
            await db.insert_named_resource(
                "avatars",
                {
                    "name": f"{avatar_vibe[:60]} avatar",
                    "vibe": avatar_vibe,
                    "image_url": image_url,
                    "metadata": {"reused": False},
                },
            )
        await save_url(project_id, "avatar.png", image_url)
        await db.update_project(project_id, {"avatar_image_url": image_url})
        await send_event(await emit(project_id, make_event("avatar", "success", "Avatar ready", {"avatar_image_url": image_url})))

        animate_model = f"{settings.fal_animate_model}/{mode}"
        await send_event(await emit(project_id, make_event("animate", "info", "Animating avatar with Wan-Animate")))
        animation_result: Any = None
        async for kind, value in _fal_updates(
            animate_model,
            {
                "image_url": image_url,
                "video_url": driving_url,
                "resolution": "480p",
                "use_turbo": True,
                "num_inference_steps": 6,
            },
            settings.pipeline_timeout_seconds,
        ):
            if kind == "progress":
                await send_event(await emit(project_id, make_event("animate", "info", "Animation progress", value)))
            elif kind == "error":
                raise value
            else:
                animation_result = value
        video_url = _find_url(animation_result, ("video", "video_url", "url"))
        if not _valid_url(video_url):
            raise RuntimeError("Animation returned no valid video URL")
        reported_cost += _reported_cost(animation_result)
        await save_url(project_id, "intermediate.mp4", video_url)
        await db.update_project(project_id, {"video_url": video_url})
        await send_event(await emit(project_id, make_event("animate", "success", "Animation complete", {"video_url": video_url})))

        await send_event(await emit(project_id, make_event("lipsync", "info", "Synchronizing speech with VEED Lipsync v2")))
        lipsync_result: Any = None
        async for kind, value in _fal_updates(
            settings.fal_lipsync_model,
            {"video_url": video_url, "audio_url": audio_url},
            settings.pipeline_timeout_seconds,
        ):
            if kind == "progress":
                await send_event(await emit(project_id, make_event("lipsync", "info", "Lip-sync progress", value)))
            elif kind == "error":
                raise value
            else:
                lipsync_result = value
        final_url = _find_url(lipsync_result, ("video", "video_url", "url"))
        if not _valid_url(final_url):
            raise RuntimeError("Lip-sync returned no valid video URL")
        reported_cost += _reported_cost(lipsync_result)
        duration = time.monotonic() - started
        await save_url(project_id, "final.mp4", final_url)
        write_json(
            project_id,
            "render-pipeline.json",
            {
                "project_id": project_id,
                "avatar_image_url": image_url,
                "driving_video_url": driving_url,
                "intermediate_video_url": video_url,
                "final_video_url": final_url,
                "audio_url": audio_url,
                "mode": mode,
                "duration_seconds": duration,
            },
        )
        await db.update_project(
            project_id,
            {
                "audio_url": audio_url,
                "final_video_url": final_url,
                "status": "completed",
                "render_duration_seconds": duration,
            },
        )
        await db.wallet_adjust(
            reported_cost,
            {
                "last_project_id": project_id,
                "operation": "video_render",
                "provider_reported_cost": reported_cost,
            },
        )
        await send_event(
            await emit(
                project_id,
                make_event(
                    "done",
                    "success",
                    "Video render complete",
                    {
                        "project_id": project_id,
                        "avatar_image_url": image_url,
                        "intermediate_video_url": video_url,
                        "final_video_url": final_url,
                        "duration_seconds": duration,
                    },
                ),
            )
        )
    except Exception as error:
        await db.update_project(
            project_id,
            {"status": "failed", "render_duration_seconds": time.monotonic() - started},
        )
        await send_event(await emit_error(project_id, "error", error))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if queue is not None:
            await queue.put(None)


async def _render_stream(
    *,
    project_id: str,
    avatar_vibe: str,
    audio_url: str,
    mode: Literal["move", "replace"],
    avatar_image_url: str | None,
    driving_video: UploadFile,
) -> AsyncIterator[dict[str, str]]:
    temp_dir = Path(tempfile.mkdtemp(prefix="charismate-render-"))
    source = temp_dir / (Path(driving_video.filename or "driving-video").name)
    total = 0
    with source.open("wb") as output:
        while chunk := await driving_video.read(1024 * 1024):
            total += len(chunk)
            if total > 250 * 1024 * 1024:
                raise ValueError("driving_video exceeds the 250 MB limit")
            output.write(chunk)
    await driving_video.close()
    if total == 0:
        raise ValueError("driving_video is empty")

    queue: asyncio.Queue[dict[str, str] | None] = asyncio.Queue()
    spawn(
        _execute_render_pipeline(
            project_id=project_id,
            avatar_vibe=avatar_vibe,
            audio_url=audio_url,
            mode=mode,
            avatar_image_url=avatar_image_url,
            source_path=source,
            queue=queue,
        )
    )

    while True:
        event = await queue.get()
        if event is None:
            break
        yield event


@router.post("/render-video")
async def render_video(
    avatar_vibe: str = Form(..., min_length=1, max_length=500),
    audio_url: str = Form(...),
    mode: Literal["move", "replace"] = Form(...),
    project_id: str = Form(...),
    avatar_image_url: str | None = Form(None),
    driving_video: UploadFile = File(...),
) -> EventSourceResponse:
    project = await db.get_row("projects", project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    if project.get("audio_url") != audio_url:
        raise HTTPException(400, "audio_url must match the voice track generated for this project")
    if driving_video.content_type and not (
        driving_video.content_type.startswith("video/") or driving_video.content_type == "application/octet-stream"
    ):
        raise HTTPException(415, "driving_video must be a video upload")
    return EventSourceResponse(
        _render_stream(
            project_id=project_id,
            avatar_vibe=avatar_vibe,
            audio_url=audio_url,
            mode=mode,
            avatar_image_url=avatar_image_url,
            driving_video=driving_video,
        )
    )
