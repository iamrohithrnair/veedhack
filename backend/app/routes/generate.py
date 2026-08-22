import asyncio
import os
import re
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env.local", override=False)

import fal_client
from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI
from sse_starlette.sse import EventSourceResponse
from tavily import TavilyClient

from app import db
from app.artifacts import copy_file, write_json, write_text
from app.config import get_settings
from app.models import ScriptRequest
from app.pioneer.finetune import PioneerClient
from app.pioneer.normalize import normalize_inference
from app.sse import emit, emit_error, make_event

router = APIRouter(prefix="/api")


def _research_text(response: dict[str, Any]) -> str:
    results = response.get("results")
    if not isinstance(results, list) or not results:
        raise RuntimeError("Tavily returned no research results")
    paragraphs: list[str] = []
    for item in results:
        if isinstance(item, dict):
            content = item.get("content")
            url = item.get("url")
            if isinstance(content, str) and content.strip():
                paragraphs.append(f"Source: {url or 'unknown'}\n{content.strip()}")
    if not paragraphs:
        raise RuntimeError("Tavily results did not contain usable content")
    return "\n\n".join(paragraphs)[:8000]


async def _ensure_project(body: ScriptRequest) -> dict[str, Any]:
    if body.project_id:
        project = await db.get_row("projects", body.project_id)
        if project is None:
            raise HTTPException(404, "Project not found")
        await db.update_project(
            body.project_id,
            {"target_prompt": body.target_prompt, "avatar_vibe": body.avatar_vibe},
        )
        return project
    return await db.create_project(
        {
            "name": body.target_prompt[:80],
            "target_prompt": body.target_prompt,
            "avatar_vibe": body.avatar_vibe,
            "status": "researching",
        }
    )


async def _stream_script(body: ScriptRequest, project_id: str) -> AsyncIterator[dict[str, str]]:
    settings = get_settings()
    audio_path: Path | None = None
    try:
        await db.update_project(project_id, {"status": "researching"})
        yield await emit(project_id, make_event("tavily", "info", "Extracting industry context..."))
        tavily_key = settings.require("tavily_api_key")
        tavily = TavilyClient(api_key=tavily_key)
        research = await asyncio.to_thread(
            tavily.search,
            query=body.target_prompt,
            search_depth="advanced",
            max_results=5,
            include_answer=False,
            include_raw_content=False,
        )
        research_text = _research_text(research)
        await db.update_project(project_id, {"research": research, "status": "extracting"})
        yield await emit(
            project_id,
            make_event("tavily", "success", "Industry context extracted", {"result_count": len(research["results"])}),
        )

        pioneer_key = settings.require("pioneer_api_key")
        model_id = settings.pioneer_model_id or "fastino/gliner2-base-v1"
        yield await emit(
            project_id,
            make_event("gliner", "info", "Slicing data with tuned GLiNER2...", {"model_id": model_id}),
        )
        async with PioneerClient(pioneer_key, settings.pioneer_base_url) as pioneer:
            pioneer_result = await pioneer.inference(
                {
                    "model_id": model_id,
                    "text": (
                        f"Target: {body.target_prompt}\n\n"
                        f"Research:\n{research_text[:900]}"
                    ),
                    "schema": {
                        "entities": {
                            "Core_Subject": "The central product, technology, or idea being discussed",
                            "Pain_Point": "A concrete problem, costly workflow, or frustration",
                            "Action_Hook": "A recommended next step, solution, or call to action",
                        },
                        "classifications": [
                            {
                                "task": "Emotional_Vibe",
                                "labels": [
                                    "outrage",
                                    "excitement",
                                    "warning",
                                    "confidence",
                                ],
                            }
                        ],
                    },
                    "threshold": 0.05,
                    "include_confidence": True,
                    "include_spans": True,
                    "store": False,
                }
            )
        extracted = normalize_inference(pioneer_result)
        write_json(project_id, "research.json", research)
        write_json(project_id, "pioneer-raw.json", pioneer_result)
        write_json(project_id, "extracted.json", extracted)
        await db.update_project(project_id, {"extracted": extracted, "status": "writing"})
        yield await emit(
            project_id,
            make_event("gliner", "success", "Structured context extracted", {"entities": extracted, "model_id": model_id}),
        )

        openai_key = settings.require("openai_api_key")
        client = AsyncOpenAI(api_key=openai_key)
        vibe = body.avatar_vibe or extracted["Emotional_Vibe"]
        system_prompt = (
            "You are a world-class, unhinged, theatrical Pitch Doctor. Transform factual "
            "tech/corporate data into a dramatic, hilarious, 2-sentence video monologue for a "
            "stylized avatar. RULES: 1. NO CORPORATE JARGON. 2. PATTERN INTERRUPT: Start with a "
            'loud, dramatic hook ("Hark!", "Fools!"). 3. THE VILLAIN: Frame the Pain_Point as an '
            "existential threat. 4. LENGTH: Exactly two punchy sentences, max 10 seconds spoken. "
            "5. FORMAT: Return strictly the spoken text."
        )
        exact_prompt = (
            f"Target: {body.target_prompt}\nAvatar vibe: {vibe}\n"
            f"Core subject: {extracted['Core_Subject']}\nPain point: {extracted['Pain_Point']}\n"
            f"Emotional vibe: {extracted['Emotional_Vibe']}\nAction hook: {extracted['Action_Hook']}\n"
            f"Research:\n{research_text}"
        )
        yield await emit(project_id, make_event("openai", "info", "Writing unhinged script..."))
        script_parts: list[str] = []
        stream = await client.responses.create(
            model=settings.openai_model,
            instructions=system_prompt,
            input=exact_prompt,
            stream=True,
            store=False,
        )
        async for item in stream:
            if item.type == "response.output_text.delta":
                delta = item.delta
                script_parts.append(delta)
                yield await emit(
                    project_id,
                    make_event("script_delta", "info", "Script token", {"delta": delta}),
                )
        script = "".join(script_parts).strip()
        if not script:
            raise RuntimeError("OpenAI returned an empty script")
        sentence_endings = re.findall(r"""[.!?]+["'’”)\]]*(?=\s|$)""", script)
        has_standalone_hook = re.match(r"^\s*(?:Hark|Fools)!\s+", script, re.IGNORECASE)
        valid_sentence_count = len(sentence_endings) == 2 or (
            bool(has_standalone_hook) and len(sentence_endings) == 3
        )
        if not valid_sentence_count:
            raise RuntimeError(
                "OpenAI did not honor the theatrical two-sentence contract "
                f"({len(sentence_endings)} punctuation-delimited sentences found)"
            )
        write_text(project_id, "script.txt", script)
        await db.update_project(project_id, {"script": script, "status": "voicing"})
        yield await emit(project_id, make_event("openai", "success", "Script complete", {"script": script}))

        yield await emit(project_id, make_event("tts", "info", "Generating onyx voice track..."))
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_file:
            audio_path = Path(audio_file.name)
        async with client.audio.speech.with_streaming_response.create(
            model=settings.openai_tts_model,
            voice=settings.openai_tts_voice,
            input=script,
            response_format="mp3",
        ) as speech:
            await speech.stream_to_file(audio_path)
        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise RuntimeError("OpenAI TTS produced an empty audio file")

        fal_key = settings.require("fal_key")
        os.environ["FAL_KEY"] = fal_key
        audio_url = await fal_client.upload_file_async(str(audio_path))
        if not isinstance(audio_url, str) or not audio_url.startswith(("https://", "http://")):
            raise RuntimeError("fal upload did not return a valid public audio URL")
        copy_file(project_id, "audio.mp3", audio_path)
        write_json(
            project_id,
            "script-pipeline.json",
            {
                "project_id": project_id,
                "entities": extracted,
                "script": script,
                "audio_url": audio_url,
                "model_id": model_id,
            },
        )
        await db.update_project(project_id, {"audio_url": audio_url, "status": "script_ready"})
        yield await emit(
            project_id,
            make_event("tts", "success", "Voice track uploaded", {"audio_url": audio_url}),
        )
        yield await emit(
            project_id,
            make_event(
                "done",
                "success",
                "Script pipeline complete",
                {
                    "project_id": project_id,
                    "entities": extracted,
                    "script": script,
                    "audio_url": audio_url,
                },
            ),
        )
    except Exception as error:
        await db.update_project(project_id, {"status": "failed"})
        yield await emit_error(project_id, "error", error)
    finally:
        if audio_path:
            audio_path.unlink(missing_ok=True)


@router.post("/generate-script")
async def generate_script(body: ScriptRequest) -> EventSourceResponse:
    project = await _ensure_project(body)
    return EventSourceResponse(_stream_script(body, project["id"]))
