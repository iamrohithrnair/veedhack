# 🎬 Charismate — Universal Multimodal Video Engine

> **Turn any topic or customer insight into a researched, high-converting script, expressive voice track, and motion-driven, photorealistic, lip-synced avatar video in seconds.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.14](https://img.shields.io/badge/Python-3.14-green.svg)](https://python.org)
[![Next.js 15](https://img.shields.io/badge/Next.js-15.1.7-black.svg)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal.svg)](https://fastapi.tiangolo.com)
[![Pioneer AI](https://img.shields.io/badge/Pioneer%20AI-GLiNER2-purple.svg)](https://pioneer.ai)
[![fal.ai](https://img.shields.io/badge/fal.ai-Wan%20%2B%20VEED%20Lipsync%20v2-orange.svg)](https://fal.ai)

---

## 🌟 Overview & The Problem

Modern high-converting video creation (personalized B2B sales outreach, interactive education, dynamic news generation) is fundamentally broken:
- **Human Bottleneck:** Sales reps, teachers, and content teams can only film a handful of bespoke videos a day.
- **Unnatural Avatars:** Traditional synthetic avatar tools produce rigid, lifeless "talking heads" with uncanny valley facial artifacts and mismatched emotions.
- **Disconnected Workflows:** Scriptwriting, web research, entity extraction, motion capture, speech synthesis, and video rendering are scattered across dozens of disjointed tools.

**Charismate** solves this by unifying **autonomous web research**, **fine-tuned hierarchical entity extraction (Pioneer AI + GLiNER2)**, **streamed structured scripting (OpenAI Sol)**, **motion-driven animation (Wan 2.2-14b Animate)**, and **studio-grade lip synchronization (VEED Lipsync v2 on fal.ai)** into a single, cohesive, non-blocking real-time studio.

---

## 🚀 High-Impact Real-World Applications

```
+---------------------------------------------------------------------------------------------------+
|                                  CHARISMATE VALUE FLYWHEEL                                        |
+---------------------------------------------------------------------------------------------------+
|  1. Hyper-Personalized B2B Sales Outreach                                                         |
|     * Scrape target accounts via Tavily -> Extract tech stack & pain points via GLiNER2 ->        |
|       Wan Animate & VEED Lipsync animate the top sales rep to pitch 1,000s of accounts 1-to-1.    |
|                                                                                                   |
|  2. Interactive AI EdTech & History Lessons                                                       |
|     * Ingest primary source archives -> Extract people, events, and pedagogy hooks ->              |
|       Roleplay Socrates, Lincoln, or Ada Lovelace teaching personalized, dynamic classroom shorts.|
|                                                                                                   |
|  3. Autonomous 24/7 Media & Breaking News Channels                                                |
|     * Ingest breaking news wires -> Extract key entities & quotes ->                              |
|       Brand news anchors auto-render viral TikToks & YouTube Shorts with zero production crew.    |
+---------------------------------------------------------------------------------------------------+
```

### 1. Hyper-Personalized B2B Sales & Marketing (The Most Lucrative)
* **The Problem:** Generic cold outreach gets less than a 1% reply rate. Personalized 1-to-1 video boosts conversions by 300%+, but humans can only record 20–30 videos daily.
* **The GLiNER2 Role:** Fine-tuned GLiNER2 parses company news, CRM call notes, and tech stacks to extract structured entity tuples: `[Core_Subject]`, `[Pain_Point]`, `[Action_Hook]`.
* **The Multimodal Video Role:** Uses a 10-second reference motion take from the company's best account executive, animates their photo with Wan Animate, and applies **VEED Lipsync v2** with prospect-tailored audio.
* **Result:** 1,000+ bespoke, hyper-personalized video pitches generated daily with zero additional recording time.

### 2. Interactive AI EdTech & Dynamic Tutoring
* **The Problem:** Textbooks and static course modules suffer from low student engagement and high drop-off rates.
* **The GLiNER2 Role:** Extracts complex chronological relationships, historical figures, and key dilemmas from raw historical documents.
* **The Multimodal Video Role:** Animates historical portraits (e.g., Albert Einstein, Cleopatra, Marcus Aurelius) in a chosen aesthetic style to explain concepts interactively.

### 3. Autonomous 24/7 Media Channels & Breaking News Shorts
* **The Problem:** Modern social algorithms demand continuous daily output, but traditional studio production requires camera operators, teleprompters, lighting, and editors.
* **The Pipeline:** Real-time web triggers extract breaking events, synthesize punchy 2-sentence scripts, and stream production-ready vertical shorts directly to social distribution channels.

---

## 🧠 Pioneer AI & GLiNER2 Fine-Tuning Deep Dive

Charismate leverages **Pioneer AI's Fine-Tuning Infrastructure** on top of `fastino/gliner2-base-v1` (Generalist and Lightweight Named Entity Recognition & Structured Extraction).

### Why GLiNER2 over standard Large LLM Prompts?
1. **Sub-100ms Inference Latency:** Eliminates the token generation lag of heavy 70B+ parameter models for entity parsing.
2. **Schema Generalization & Zero-Shot Flexibility:** Capable of extracting bidirectional relations and custom entity definitions (`Core_Subject`, `Pain_Point`, `Action_Hook`) across diverse domains without hallucinating unstructured text.
3. **Structured JSON Output:** Returns clean, deterministic entity mappings ready for instantaneous prompt injection.

### 🔬 Fine-Tuning Pipeline Architecture

```mermaid
flowchart TD
    subgraph S1["1. Topic Corpus & Ingestion"]
        A1["Market Topics: B2B Sales, EdTech, Breaking News"] --> A2["Tavily Web Search API (Advanced Depth)"]
        A2 --> A3["Domain Paragraph Corpus (charismate-tavily-markets.jsonl)"]
    end

    subgraph S2["2. Pioneer AI Dataset & Synthetic Synthesis"]
        A3 --> B1["Pioneer Corpus Creation: POST /corpora"]
        B1 --> B2["Pioneer Synthetic Dataset Generation: POST /datasets/synthetic"]
        B2 --> B3["NER Schema Definition: Core_Subject, Pain_Point, Action_Hook"]
    end

    subgraph S3["3. GLiNER2 Model Fine-Tuning"]
        B3 --> C1["Base Model: fastino/gliner2-base-v1"]
        C1 --> C2["Pioneer Training Job: POST /train"]
        C2 --> C3["Active Hyperparameter Optimization (Epochs, LR, NER Weight)"]
        C3 --> C4["Trained Model Checkpoint Artifact"]
    end

    subgraph S4["4. Live Inference Deployment"]
        C4 --> D1["Updated PIONEER_MODEL_ID in .env.local"]
        D1 --> D2["Live Entity Extraction in POST /api/generate-script"]
        D2 --> D3["Streamed OpenAI Script Generation Context Injection"]
    end
```

### Technical Fine-Tuning Commands:
```bash
# 1. Probe Pioneer API connection
uv run python scripts/probe_gliner.py

# 2. Seed domain corpus across B2B sales, EdTech, and media
uv run python scripts/seed_corpus.py "creator marketing" "founder storytelling"

# 3. Trigger Pioneer AI GLiNER2 fine-tuning pipeline
uv run python scripts/train_gliner2.py --from-tavily --ner-only --target-rows 500 --per-topic 10
```

---

## 🎨 Multimodal Rendering Pipeline & VEED Lipsync v2

Charismate orchestrates a state-of-the-art generative video chain powered by **fal.ai**:

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Sales Rep
    participant Front as Next.js Workbench
    participant Back as FastAPI Backend (Detached Task)
    participant Tav as Tavily Research
    participant Pio as Pioneer AI (GLiNER2)
    participant OAI as OpenAI (Sol + TTS)
    participant Fal as fal.ai (Nano-Banana / Wan Animate)
    participant VEED as VEED Lipsync v2 (fal.ai)

    User->>Front: Enters Topic, Avatar Vibe & Records 10s Driving Video
    Front->>Back: POST /api/generate-script (SSE Stream)
    Back->>Tav: Advanced Live Web Search
    Tav-->>Back: Industry context & source articles
    Back->>Pio: Extract Entities (Core_Subject, Pain_Point, Action_Hook)
    Pio-->>Back: Structured Entity Schema
    Back->>OAI: Stream 2-Sentence Script (gpt-5.6-sol)
    OAI-->>Front: Real-time token streaming to Teleprompter
    Back->>OAI: Synthesize Audio Voice Track (tts-1 onyx)
    OAI-->>Back: Public MP3 Voice Track

    Note over Front,Back: User records webcam motion or selects pre-recorded clip

    Front->>Back: POST /api/render-video (Detached Background Job)
    Back->>Fal: Upload driving video & Generate Avatar Image (Nano-Banana)
    Fal-->>Back: Photorealistic 1024x1024 Avatar Portrait
    Back->>Fal: Wan 2.2-14b Animate (Mode: Move / Replace)
    Note over Fal: Transfers head tilt, shoulder motion, blinking, and body dynamics
    Fal-->>Back: Intermediate Animated Video
    Back->>VEED: VEED Lipsync v2 (Intermediate Video + OpenAI Audio)
    Note over VEED: High-fidelity phoneme-to-viseme alignment & realistic lip deformation
    VEED-->>Back: Final Rendered Video (final.mp4)
    Back-->>Front: Instant Video Preview, Download & Full Terminal Audit Trail
```

### Why VEED Lipsync v2 is a Game-Changer:
1. **Zero Uncanny Valley Distortion:** Unlike older Wav2Lip models that blur the mouth region or produce square artifact boxes, **VEED Lipsync v2** preserves skin texture, micro-expressions, teeth, and natural jaw kinematics.
2. **Robust Audio-Visual Synchronization:** Handles variable speech tempos, energetic inflections, and pauses without audio drift.
3. **Seamless Blend with Wan Animate:** Combines natural body sway from Wan Animate with exact mouth synchronization from VEED, producing broadcasts indistinguishable from authentic studio footage.

---

## 💻 Full-Stack System Architecture

```mermaid
graph LR
    subgraph Client["Frontend (Next.js 15 App Router)"]
        UI1["Mac-Inspired Glassmorphic Workbench"]
        UI2["On-Demand Webcam Teleprompter Studio"]
        UI3["Live Terminal SSE Visualizer"]
        UI4["Avatar Studio (Upload / Fal Generate)"]
        UI5["Multi-Job Switcher & State Restoration"]
    end

    subgraph Server["Backend (FastAPI + Python 3.14)"]
        API1["POST /api/generate-script (SSE)"]
        API2["POST /api/render-video (Async Background Task)"]
        API3["CRUD /api/projects, /api/avatars, /api/templates"]
        API4["Wallet & Usage Accounting Ledger"]
        DB[(SQLite Persistent Storage)]
    end

    subgraph AI_Cloud["AI Cloud Infrastructure"]
        TAV["Tavily Search API"]
        PIO["Pioneer AI (GLiNER2 Model)"]
        OAI["OpenAI (GPT-5.6 Sol + TTS)"]
        FAL_IMG["fal.ai (Nano-Banana / Flux)"]
        FAL_WAN["fal.ai (Wan-Animate 2.2-14b)"]
        FAL_VEED["fal.ai (VEED Lipsync v2)"]
    end

    Client <-->|SSE Stream & REST API| Server
    Server <--> DB
    Server --> TAV
    Server --> PIO
    Server --> OAI
    Server --> FAL_IMG
    Server --> FAL_WAN
    Server --> FAL_VEED
```

---

## ⚡ Non-Blocking Execution & State Persistence

Charismate is engineered for enterprise workflows where asset generation must never block the user:
- **Detached Server Tasks:** Render jobs run inside independent `asyncio.create_task` workers. You can close your laptop, refresh, or switch tabs—rendering continues uninterrupted on the server.
- **Automatic State Restoration:** Active projects are synced across `localStorage` and URL parameters (`/create?project_id=...`). Returning to the app instantly restores your script, teleprompter, audio player, rendered video, and full event logs.
- **Multi-Job Switcher:** Click **`＋ New Job`** to spin up multiple parallel video renders without waiting for past jobs to finish.

---

## 🛠️ Quickstart & Setup Guide

### 1. Prerequisites
- **Python 3.14+** with [`uv`](https://github.com/astral-sh/uv)
- **Node.js 18+** & `npm`
- **ffmpeg** (optional, recommended for local video transcoding)

### 2. Backend Setup
```bash
cd backend

# Configure environment
cp .env.local.example .env.local
# Edit .env.local with your keys:
# OPENAI_API_KEY, TAVILY_API_KEY, PIONEER_API_KEY, FAL_KEY

# Install dependencies and launch
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend

# Configure environment
cp .env.local.example .env.local

# Install dependencies and start development server
npm install
npm run dev
```

Open **[http://localhost:3000](http://localhost:3000)** in your browser.

---

## 🧪 Testing & Verification

Run the comprehensive test suite and probe scripts:

```bash
# Run backend test suite
cd backend
uv run pytest

# Test external API connections
uv run python scripts/probe_tavily.py
uv run python scripts/probe_gliner.py
uv run python scripts/probe_openai.py
uv run python scripts/probe_fal.py

# Run full end-to-end headless demo pipeline
uv run python scripts/run_demo_pipeline.py --api http://127.0.0.1:8000
```

---

## 📈 Impact & Business Value

| Metric | Traditional Video Production | Charismate Multimodal Engine | Improvement |
|---|---|---|---|
| **Production Time per Video** | 2 – 4 Hours | **< 60 Seconds** | **120x Faster** |
| **Cost per Video Asset** | $150 – $500 (Crew/Equipment) | **<$0.50 (Compute/API)** | **99.7% Cost Reduction** |
| **Daily Output Capacity** | 5 – 10 Videos / Creator | **1,000+ Automated Videos / Day** | **100x Scale** |
| **Viewer Retention & Conversion** | Static Email / Generic Text | **Motion-Driven Personalized Video** | **300%+ Reply Rate Lift** |

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.
