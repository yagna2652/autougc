# AutoUGC

Reference-video-to-UGC pipeline for generating product ad videos.

AutoUGC takes:
- a TikTok/Reel URL (style reference)
- product image(s) (required)
- optional product description/category

and produces:
- structured style analysis
- a motion-focused generation prompt + short script
- a generated vertical ad video (Sora/Kling via Fal)

## Source Of Truth

Architecture and runtime behavior are canonical in:
- `docs/ARCHITECTURE.md`

If another document conflicts with that file, follow `docs/ARCHITECTURE.md`.

## Current Architecture

- Backend: FastAPI (`api/server.py`)
- Pipeline engine: LangGraph (`src/pipeline/graphs/simple_pipeline.py`)
- Frontend: Next.js (`web/`)
- External services:
  - OpenRouter (vision + text model calls)
  - Fal.ai (scene image + image-to-video generation)
  - yt-dlp + ffmpeg/ffprobe (video download + frame extraction)

Pipeline steps:
1. `download_video`
2. `extract_frames`
3. `analyze_video`
4. `generate_prompt`
5. `generate_scene_image`
6. `generate_video`

## Prerequisites

- Python 3.11+
- Node.js 18+
- `ffmpeg` and `ffprobe` in `PATH`

## Setup

### 1. Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-api.txt
```

### 2. Frontend dependencies

```bash
cd web
npm install
cd ..
```

### 3. Environment variables

Create root `.env`:

```bash
OPENROUTER_API_KEY=your_openrouter_key
FAL_KEY=your_fal_key
```

Optional tracing:

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=autougc-pipeline
```

Create `web/.env.local`:

```bash
PYTHON_API_URL=http://localhost:8000
```

## Run (Development)

Option A: helper scripts

```bash
./start-dev.sh
```

Stops both servers:

```bash
./stop-dev.sh
```

Option B: manual terminals

Terminal 1:

```bash
source venv/bin/activate
python -m uvicorn api.server:app --reload --port 8000
```

Terminal 2:

```bash
cd web
npm run dev
```

## API (Current)

Backend:
- `GET /health`
- `POST /api/v1/pipeline/start`
- `GET /api/v1/pipeline/jobs/{job_id}`
- `DELETE /api/v1/pipeline/jobs/{job_id}`
- `GET /api/v1/pipeline/health`

Frontend proxy:
- `POST /api/pipeline` (`action: "start"` or `"status"`)
- `GET /api/pipeline` (health passthrough)

## Notes

- Product images are required in the current implementation.
- Jobs are stored in-memory (non-persistent).
- Video generation depends on available Fal/OpenRouter credits.
