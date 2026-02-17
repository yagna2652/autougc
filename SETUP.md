# AutoUGC Setup Guide

This guide is for running the current AutoUGC stack locally.

Canonical architecture reference:
- `docs/ARCHITECTURE.md`

## 1. Prerequisites

- Python 3.11+
- Node.js 18+
- `ffmpeg` + `ffprobe` installed and available in `PATH`

Install ffmpeg (macOS):

```bash
brew install ffmpeg
```

## 2. Install Dependencies

From repo root:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-api.txt
```

Frontend:

```bash
cd web
npm install
cd ..
```

## 3. Configure Environment

### 3.1 Root `.env`

Required keys for full pipeline:

```bash
OPENROUTER_API_KEY=your_openrouter_key
FAL_KEY=your_fal_key
```

Optional (LangSmith tracing):

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=autougc-pipeline
```

### 3.2 Frontend `web/.env.local`

```bash
PYTHON_API_URL=http://localhost:8000
```

## 4. Start Services

You need both servers:
- FastAPI backend on `:8000`
- Next.js frontend on `:3000`

### Option A: Start script

```bash
./start-dev.sh
```

Stop:

```bash
./stop-dev.sh
```

### Option B: Manual

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

## 5. Verify

Backend health:

```bash
curl http://localhost:8000/health
```

Pipeline health:

```bash
curl http://localhost:8000/api/v1/pipeline/health
```

Frontend health proxy:

```bash
curl http://localhost:3000/api/pipeline
```

## 6. Run A Full Job (UI)

1. Open `http://localhost:3000`
2. Enter a TikTok/Reel URL
3. Upload at least one product image
4. Select model (`sora` or `kling`)
5. Click `Generate`
6. Wait for pipeline completion and inspect node outputs

## 7. Current API Surface

Backend:
- `POST /api/v1/pipeline/start`
- `GET /api/v1/pipeline/jobs/{job_id}`
- `DELETE /api/v1/pipeline/jobs/{job_id}`
- `GET /api/v1/pipeline/health`

Next.js proxy:
- `POST /api/pipeline` with:
  - `{ "action": "start", ... }`
  - `{ "action": "status", "jobId": "..." }`
- `GET /api/pipeline`

## 8. Troubleshooting

### Backend not reachable from frontend

- Check backend is running on `:8000`
- Check `web/.env.local` has `PYTHON_API_URL=http://localhost:8000`

### Download fails at `download_video`

- Validate TikTok/Reel URL
- Update downloader:

```bash
source venv/bin/activate
pip install -U yt-dlp
```

### Frame extraction fails

- Verify `ffmpeg` and `ffprobe`:

```bash
ffmpeg -version
ffprobe -version
```

### Analysis/prompt generation fails

- Ensure `OPENROUTER_API_KEY` is present in root `.env`
- Check OpenRouter credits/limits

### Scene/video generation fails

- Ensure `FAL_KEY` is present in root `.env`
- Check Fal credits/queue status

### Port conflicts

```bash
lsof -ti:8000 | xargs kill -9
lsof -ti:3000 | xargs kill -9
```

## 9. Operational Notes

- Job storage is in-memory only (lost on server restart).
- Product images are currently required by pipeline state validation.
- Polling is used for progress (no webhooks).
