# Charismate API contract

Base URL: `http://localhost:8000`

## Streaming events

Both pipeline endpoints return `text/event-stream`. Every frame contains one
JSON object:

```text
data: {"stage":"tavily","level":"info","message":"Extracting industry context...","payload":{},"timestamp":"2026-08-22T14:00:00Z"}
```

`stage` is one of `tavily`, `gliner`, `openai`, `script_delta`, `tts`, `upload`,
`avatar`, `animate`, `lipsync`, `done`, or `error`. Script tokens use
`payload: {"delta": "..."}`. A terminal `done` event contains the completed
resource URLs.

## `POST /api/generate-script`

JSON body:

```json
{
  "target_prompt": "Why manual fine-tuning is obsolete",
  "avatar_vibe": "An 18th-century philosopher",
  "project_id": "optional-project-uuid"
}
```

The final event payload contains `project_id`, `entities`, `script`, and
`audio_url`.

## `POST /api/render-video`

Multipart fields:

- `driving_video`: required WebM or MP4
- `avatar_vibe`: required string
- `audio_url`: required URL from script generation
- `mode`: `move` or `replace`
- `project_id`: required project UUID
- `avatar_image_url`: optional previously generated avatar URL

The final event payload contains `avatar_image_url`,
`intermediate_video_url`, and `final_video_url`.

## Resource endpoints

- `GET|POST /api/projects`
- `GET|PATCH|DELETE /api/projects/{id}`
- `GET|POST /api/avatars`
- `DELETE /api/avatars/{id}`
- `GET|POST /api/templates`
- `DELETE /api/templates/{id}`
- `GET /api/dashboard/stats`
- `GET /api/wallet`
