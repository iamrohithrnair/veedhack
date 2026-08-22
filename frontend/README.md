# Charismate frontend

Next.js App Router frontend for the Charismate multimodal video workflow. Copy `.env.local.example` to `.env.local` when running locally and point `NEXT_PUBLIC_API_URL` at the orchestrator API.

## What to show in the demo

Open `/create`, generate a script from a topic and avatar direction, then record a ten-second webcam performance and render it. The three-column studio keeps the generated script and audio on the left, the teleprompter and real `MediaRecorder` capture in the center, and real SSE pipeline events, render progress, and the final video on the right. The dashboard and library pages intentionally show only records returned by the backend, with honest empty/offline states.
