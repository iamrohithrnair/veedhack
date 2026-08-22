# Charismate backend

FastAPI backend for live research, two-sentence script generation, speech synthesis,
avatar animation, and lip-sync. Pipeline output is produced only by Tavily, Pioneer,
OpenAI, and fal; there are no canned API fallbacks. Built-in templates are product
presets seeded into SQLite.

## Setup and run

From `backend/`:

```bash
cp .env.local.example .env.local
# Fill the API keys in .env.local.
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Python 3.14 is selected by `.python-version`. SQLite is initialized during application
lifespan at `DATABASE_PATH`. Configuration loads `.env.local` first and then `.env`;
secret keys may be absent at startup, but the pipeline stage that needs one returns a
clear SSE error.

Run the optional scripts from `backend/`:

```bash
uv run python scripts/probe_tavily.py
uv run python scripts/probe_gliner.py
uv run python scripts/probe_openai.py
uv run python scripts/probe_fal.py
uv run python scripts/seed_corpus.py "creator marketing" "founder storytelling"
uv run python scripts/train_gliner2.py --from-tavily --ner-only --target-rows 500 --per-topic 10
uv run python scripts/run_demo_pipeline.py --api http://127.0.0.1:8003
uv run pytest
```

`train_gliner2.py` preserves existing `.env.local` lines and updates only
`PIONEER_MODEL_ID` after successful training.

## HTTP API

All ordinary endpoints use JSON. Errors before an SSE response starts use FastAPI's
standard `{"detail": ...}` JSON shape.

| Method | Path | Request | Response |
|---|---|---|---|
| GET | `/health` | — | `{"status":"ok"}` |
| GET | `/api/projects` | — | Project array |
| POST | `/api/projects` | `{"name":string,"target_prompt"?:string,"avatar_vibe"?:string,"metadata"?:object}` | Created project |
| GET | `/api/projects/{id}` | — | Project including ordered `events` |
| PATCH | `/api/projects/{id}` | Any editable project fields | Updated project |
| DELETE | `/api/projects/{id}` | — | `204` |
| GET | `/api/avatars` | — | Avatar array |
| POST | `/api/avatars` | `{"name":string,"vibe"?:string,"image_url":url,"metadata"?:object}` | Created avatar |
| DELETE | `/api/avatars/{id}` | — | `204` |
| GET | `/api/templates` | — | Template array |
| POST | `/api/templates` | `{"name":string,"description"?:string,"prompt":object,"metadata"?:object}` | Created template |
| DELETE | `/api/templates/{id}` | — | `204`; built-ins return `409` |
| GET | `/api/dashboard/stats` | — | Project/avatar/wallet aggregate |
| GET | `/api/wallet` | — | Wallet ledger |

### Generate script

`POST /api/generate-script`, content type `application/json`:

```json
{
  "target_prompt": "Explain why founders should turn customer calls into short videos",
  "avatar_vibe": "warm and confident",
  "project_id": "optional-existing-project-uuid"
}
```

The endpoint returns `text/event-stream`. If `project_id` is omitted a project is
created. The real pipeline is Tavily search → Pioneer GLiNER2 inference → streamed
OpenAI Responses generation with `gpt-5.6-sol` and `store=false` → OpenAI `tts-1`
voice `onyx` → fal public upload.

### Render video

`POST /api/render-video`, content type `multipart/form-data`:

```bash
curl -N http://localhost:8000/api/render-video \
  -F 'avatar_vibe=warm and confident' \
  -F 'audio_url=https://example.com/audio.mp3' \
  -F 'mode=move' \
  -F 'project_id=PROJECT_UUID' \
  -F 'avatar_image_url=https://example.com/avatar.png' \
  -F 'driving_video=@./driving.mp4'
```

`avatar_image_url` is optional. `mode` is `move` or `replace`. The upload limit is
250 MB. When ffmpeg is available the driving video is transcoded to H.264/AAC MP4;
transcode errors abort the pipeline. Without ffmpeg, input must already be `.mp4`.
The real pipeline is fal upload → `fal-ai/nano-banana` when an avatar image is not
reused → `fal-ai/wan/v2.2-14b/animate/{mode}` at 480p/turbo/6 steps →
`veed/lipsync/v2`.

## SSE contract

Every SSE `data` value is a JSON object and is persisted before emission:

```json
{
  "stage": "tavily",
  "level": "info",
  "message": "Extracting industry context...",
  "payload": {},
  "timestamp": "2026-08-22T12:00:00+00:00"
}
```

`stage` values include `tavily`, `gliner`, `openai`, `script_delta`, `tts`,
`upload`, `avatar`, `animate`, `lipsync`, `done`, and `error`. `script_delta`
payloads contain `{"delta":"..."}`. A terminal `done` payload contains final URLs and
the project ID. A terminal `error` contains `error_type`; the project is marked
`failed`. Clients should stop on either terminal stage.

## Environment

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Responses and TTS |
| `TAVILY_API_KEY` | Web research |
| `PIONEER_API_KEY` | GLiNER2 inference/training |
| `FAL_KEY` | Upload, image, animation, lip-sync |
| `PIONEER_MODEL_ID` | Tuned model; defaults to `fastino/gliner2-base-v1` |
| `DATABASE_PATH` | SQLite path |
| `PIONEER_BASE_URL` | Pioneer API origin |
| `OPENAI_MODEL` | Defaults to `gpt-5.6-sol` |
| `PIPELINE_TIMEOUT_SECONDS` | Timeout for each fal queued operation |
| `CORS_ORIGINS` | Comma-separated origins; defaults to localhost:3000 |
