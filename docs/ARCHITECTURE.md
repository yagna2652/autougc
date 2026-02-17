# AutoUGC Architecture (Single Source of Truth)

Last updated: 2026-02-12
Owner: AutoUGC engineering
Status: Canonical runtime architecture for this repository

## 1. Purpose

This document is the authoritative description of how AutoUGC currently works in code.
If any other doc conflicts with this file, trust this file.

## 2. Product Summary

AutoUGC generates a new UGC-style ad video from:
- a reference TikTok/Reel URL (style source)
- one or more product images (required)
- optional product description and category

The system analyzes reference video style, generates a motion-focused prompt + script, creates a scene image for first-frame conditioning, then generates an image-to-video ad.

## 3. System Components

### 3.1 FastAPI Backend (Python)
- Entry point: `api/server.py`
- Base URL (dev): `http://localhost:8000`
- Responsibilities:
  - accept pipeline start requests
  - manage async background jobs
  - expose job status for polling
  - run LangGraph pipeline nodes

### 3.2 Pipeline Engine (LangGraph)
- Graph: `src/pipeline/graphs/simple_pipeline.py`
- State type: `src/pipeline/state.py`
- Node implementations: `src/pipeline/nodes/*.py`
- Execution model:
  - sequential stateful workflow
  - conditional early stop on error
  - streamed node updates for job progress

### 3.3 Frontend (Next.js)
- Entry page: `web/src/app/page.tsx`
- Proxy API route: `web/src/app/api/pipeline/route.ts`
- Responsibilities:
  - collect user inputs
  - start backend job
  - poll job status
  - visualize pipeline node progress
  - show outputs (analysis JSON, prompt/script, scene image, generated video)

## 4. End-to-End Runtime Flow

1. User enters TikTok URL, uploads product image(s), picks model (`sora` or `kling`).
2. Frontend calls `POST /api/pipeline` with `action: "start"` (Next.js route).
3. Next.js forwards to backend `POST /api/v1/pipeline/start`.
4. Backend creates job (in-memory), launches background task.
5. LangGraph pipeline executes node-by-node:
   1. `download_video`
   2. `extract_frames`
   3. `analyze_video`
   4. `generate_prompt`
   5. `generate_scene_image`
   6. `generate_video`
6. Frontend polls `POST /api/pipeline` with `action: "status"` every ~2s.
7. On completion, frontend renders final outputs and allows video download.

## 5. Pipeline Nodes (Current Behavior)

### 5.1 `download_video`
- File: `src/pipeline/nodes/download_video.py`
- Uses: `api/video_downloader.py` (`yt-dlp`)
- Output:
  - `video_path`
  - `current_step = "video_downloaded"`

### 5.2 `extract_frames`
- File: `src/pipeline/nodes/extract_frames.py`
- Uses: `src/analyzer/frame_extractor.py` (`ffprobe` + `ffmpeg`)
- Default frames: `config.num_frames` (default 5)
- Output:
  - `frames` (local file paths)
  - `current_step = "frames_extracted"`

### 5.3 `analyze_video`
- File: `src/pipeline/nodes/analyze_video.py`
- Provider: OpenRouter via OpenAI SDK compatibility
- Default vision model: `openai/gpt-4o-mini` (see `src/pipeline/utils/openrouter_utils.py`)
- Input: extracted frame images
- Output:
  - `video_analysis` (structured style analysis JSON)
  - `current_step = "video_analyzed"`

### 5.4 `generate_prompt`
- File: `src/pipeline/nodes/generate_prompt.py`
- Provider: OpenRouter text model (default `openai/gpt-4o-mini`)
- Inputs:
  - `video_analysis`
  - `product_description`
  - `product_mechanics`
  - `product_images`
  - interaction library (`assets/interaction_library/index.json`)
- Outputs:
  - `video_prompt` (motion-focused I2V prompt)
  - `suggested_script`
  - `scene_description`
  - `current_step = "prompt_generated"`

### 5.5 `generate_scene_image`
- File: `src/pipeline/nodes/generate_scene_image.py`
- Provider: Fal endpoint `fal-ai/nano-banana-pro/edit`
- Purpose: create photorealistic first frame where product appears in-context
- Outputs:
  - success: `scene_image_url`, `current_step = "scene_image_generated"`
  - skip/fail: `scene_image_skipped` or `scene_image_failed` (pipeline can continue)

### 5.6 `generate_video`
- File: `src/pipeline/nodes/generate_video.py`
- Provider: Fal image-to-video
- Endpoints:
  - `sora` -> `fal-ai/sora-2/image-to-video/pro`
  - `kling` -> `fal-ai/kling-video/v2.1/pro/image-to-video`
- Starting frame preference:
  - uses `scene_image_url` if available
  - falls back to uploaded product image
- Outputs:
  - `generated_video_url`
  - `i2v_image_url`
  - `current_step = "video_generated"`

## 6. API Contract (Backend)

All pipeline routes are under `/api/v1` from `api/routes/pipeline.py`.

### 6.1 Start Job
- `POST /api/v1/pipeline/start`
- Request fields:
  - `video_url` (required)
  - `product_description` (optional)
  - `product_images` (required by current state validation)
  - `product_category` (optional)
  - `config` (optional)
- Response:
  - `job_id`
  - `status: "started"`

### 6.2 Get Job Status
- `GET /api/v1/pipeline/jobs/{job_id}`
- Returns:
  - `status`, `current_step`, `error`
  - optional outputs (`video_analysis`, `video_prompt`, `suggested_script`, `scene_image_url`, `i2v_image_url`, `generated_video_url`)

### 6.3 Delete Job
- `DELETE /api/v1/pipeline/jobs/{job_id}`

### 6.4 Health
- `GET /api/v1/pipeline/health`
- Returns flags for tracing and key availability.

## 7. Frontend API Contract

Frontend does not call backend directly from UI code. It calls Next.js route:

- `POST /api/pipeline`
  - `action: "start"` -> starts backend job
  - `action: "status"` -> gets backend job status
- `GET /api/pipeline`
  - backend health passthrough

Mapping logic is in `web/src/app/api/pipeline/route.ts` and converts snake_case backend fields to camelCase frontend fields.

## 8. State Model

Canonical pipeline state is defined in `src/pipeline/state.py` as `PipelineState`.

Key fields:
- inputs: `video_url`, `product_description`, `product_images`, `product_category`, `product_mechanics`, `config`
- progress: `status`, `current_step`, `error`
- intermediates: `video_path`, `frames`, `video_analysis`, `video_prompt`, `suggested_script`, `scene_description`, `scene_image_url`, `i2v_image_url`
- output: `generated_video_url`

Note: `create_initial_state` currently requires `product_images` to be non-empty.

## 9. Configuration and Environment Variables

### 9.1 Required for full runtime
- `OPENROUTER_API_KEY` (analysis + prompt generation)
- `FAL_KEY` (scene image + I2V video generation)

### 9.2 Optional
- `LANGCHAIN_TRACING_V2=true`
- `LANGCHAIN_API_KEY`
- `LANGCHAIN_PROJECT` (default `autougc-pipeline`)

### 9.3 Local server URLs
- Backend default: `http://localhost:8000`
- Frontend proxy reads `PYTHON_API_URL` (defaults to `http://localhost:8000`)

## 10. Job Storage and Execution Guarantees

- Job store is in-memory (`JobStore` in `api/routes/pipeline.py`).
- Jobs are not persisted across server restarts.
- No distributed queue; background tasks run in FastAPI process.
- Suitable for local/dev and low-concurrency workflows.

## 11. Observability

- Structured logging in backend (`api/server.py`).
- Node-level progress logs in pipeline graph wrappers.
- Optional LangSmith tracing utilities in `src/tracing.py`.

## 12. Current Constraints and Risks

1. Documentation drift exists across older docs (`README.md`, `SETUP.md`, `web/README.md`) versus current runtime.
2. In-memory jobs are non-durable and not horizontally scalable.
3. Long-running generation depends on external provider queues and credits.
4. Product images are mandatory in current implementation.

## 13. Non-Goals (Current Codebase)

- No persistent DB for jobs/results.
- No auth/rate limiting layer.
- No webhook push completion; polling only.
- No guaranteed idempotency for repeated start requests.

## 14. Source of Truth Files

When this architecture doc needs re-validation, use these files first:
- `api/server.py`
- `api/routes/pipeline.py`
- `src/pipeline/graphs/simple_pipeline.py`
- `src/pipeline/state.py`
- `src/pipeline/nodes/*.py`
- `web/src/app/page.tsx`
- `web/src/app/api/pipeline/route.ts`
- `web/src/types/pipeline.ts`

