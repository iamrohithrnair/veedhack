# Charismate

Charismate turns a topic into a researched two-sentence pitch, generates its
voice track, captures a ten-second performance, and renders a motion-driven,
lip-synced avatar video.

## Services

- `frontend/` — Next.js App Router interface
- `backend/` — FastAPI pipeline and Pioneer training utilities
- `contracts/` — shared API contract

## Configuration

No API responses are mocked. Before starting either service:

1. Copy `backend/.env.local.example` to `backend/.env.local`.
2. Add valid OpenAI, Tavily, Pioneer, and fal keys.
3. Copy `frontend/.env.local.example` to `frontend/.env.local`.

Service-specific setup and commands are documented in each service README.

## Pipeline

Tavily search → Pioneer GLiNER2 → OpenAI script → OpenAI speech → fal avatar
generation → Wan Animate motion transfer → VEED lip-sync.
