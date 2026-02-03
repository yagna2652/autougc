"""
FastAPI server for AutoUGC video generation.

Simple API that exposes the UGC generation pipeline:
- POST /api/v1/pipeline/start - Start a pipeline job
- GET /api/v1/pipeline/jobs/{job_id} - Get job status
- GET /api/v1/pipeline/health - Health check
"""

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AutoUGC API",
    description="Simple UGC video generation from TikTok analysis",
    version="2.0.0",
)

# CORS configuration for Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "AutoUGC API",
        "version": "2.0.0",
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "AutoUGC API",
        "version": "2.0.0",
        "endpoints": {
            "health": "/health",
            "pipeline_start": "POST /api/v1/pipeline/start",
            "pipeline_job_status": "GET /api/v1/pipeline/jobs/{job_id}",
            "pipeline_health": "GET /api/v1/pipeline/health",
        },
    }


# Import and include pipeline router
from api.routes.pipeline import router as pipeline_router

app.include_router(pipeline_router, prefix="/api/v1", tags=["pipeline"])


if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
