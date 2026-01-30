# AutoUGC Setup Guide

Complete setup instructions for running the full AutoUGC system with TikTok analysis.

## Architecture

The system consists of two servers:

1. **FastAPI Backend** (Port 8000) - Python-based TikTok video analyzer
2. **Next.js Frontend** (Port 3000) - Web UI for the complete workflow

## Prerequisites

- Python 3.9+
- Node.js 18+
- FFmpeg (for video processing)
- Anthropic API Key

## Installation

### 1. Install Python Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Install API server dependencies
pip install -r requirements-api.txt
```

### 2. Install Node Dependencies

```bash
cd web
npm install
cd ..
```

### 3. Configure Environment Variables

The `.env` file in the root directory should have:
```bash
ANTHROPIC_API_KEY=your_anthropic_key_here
```

The `web/.env.local` file should have:
```bash
FAL_KEY=your_fal_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
FASTAPI_URL=http://localhost:8000
```

## Running the System

You need to run **both servers simultaneously** in separate terminals.

### Terminal 1: Start FastAPI Backend

```bash
# From project root
python -m uvicorn api.server:app --reload --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Terminal 2: Start Next.js Frontend

```bash
cd web
npm run dev
```

Expected output:
```
▲ Next.js 14.x.x
- Local:        http://localhost:3000
```

## Verification

### 1. Test Backend Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "service": "AutoUGC Analyzer API",
  "version": "1.0.0"
}
```

### 2. Test Frontend

Open your browser to http://localhost:3000

You should see the AutoUGC interface with 4 steps.

### 3. Test Full Flow

1. Paste a TikTok URL in Step 1
2. Click "Analyze TikTok"
3. Watch the progress bar (takes 2-5 minutes)
4. Blueprint data should populate automatically
5. Continue to Step 2 to upload product images
6. Generate video in Step 4

## How It Works

### Step 1: TikTok Analysis (New!)

**Old behavior:** Used mock/hardcoded data
**New behavior:** Real video analysis

1. User pastes TikTok URL
2. Frontend calls `/api/analyze-video` (Next.js proxy)
3. Next.js forwards to FastAPI at `http://localhost:8000/api/v1/analyze`
4. FastAPI downloads video using yt-dlp
5. FastAPI runs BlueprintGenerator with progress callbacks
6. Frontend polls `/api/analyze-video/{job_id}` every 3 seconds
7. Progress updates show in UI
8. When complete, blueprint data populates the UI

### Steps 2-4: Product & Video Generation (Unchanged)

These steps work exactly as before:
- Step 2: Upload product images
- Step 3: Claude analyzes images and generates smart prompt
- Step 4: Fal.ai generates video (Sora 2 or Kling)

## Troubleshooting

### "Failed to connect to analysis service"

- Make sure FastAPI is running on port 8000
- Check `web/.env.local` has `FASTAPI_URL=http://localhost:8000`

### "Analysis failed: Failed to download video"

- Check TikTok URL is valid and accessible
- yt-dlp may need updating: `pip install -U yt-dlp`

### Video analysis is slow

- Normal: 2-5 minutes per video
- Depends on video length and scene complexity
- Whisper transcription is the slowest step

### Port already in use

```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

## API Endpoints

### FastAPI Backend (Port 8000)

- `GET /health` - Health check
- `POST /api/v1/analyze` - Start video analysis job
- `GET /api/v1/jobs/{job_id}` - Get job status and result
- `DELETE /api/v1/jobs/{job_id}` - Delete completed job

### Next.js Proxy (Port 3000)

- `POST /api/analyze-video` - Proxy to FastAPI analyze endpoint
- `GET /api/analyze-video/[jobId]` - Proxy to FastAPI job status
- `POST /api/analyze` - Claude product image analysis (unchanged)
- `POST /api/generate` - Fal.ai video generation (unchanged)

## Development Notes

### Progress Callbacks

The BlueprintGenerator now supports progress callbacks:

```python
def progress_callback(step_name: str, step_num: int, total: int):
    print(f"[{step_num}/{total}] {step_name}")

blueprint = generator.generate(
    video_path="video.mp4",
    progress_callback=progress_callback
)
```

### Job Manager

Jobs are stored in-memory and auto-cleaned when deleted. For production, consider:
- Redis for job storage
- Celery for task queue
- Database for job persistence

### Video Cleanup

Downloaded TikTok videos are automatically deleted after analysis. Temp files are cleaned up unless `keep_temp_files=True`.

## Production Considerations

For production deployment:

1. **Use a task queue** (Celery, RQ, or similar)
2. **Add authentication** to protect API endpoints
3. **Rate limiting** to prevent abuse
4. **File storage** (S3, etc.) instead of temp directories
5. **Database** for job persistence
6. **Webhooks** instead of polling for job status
7. **HTTPS** for both servers
8. **CORS** configuration for production domains
