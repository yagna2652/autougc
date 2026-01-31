"""
FastAPI server for AutoUGC video analysis backend.

This server exposes the Python BlueprintGenerator to the Next.js web UI,
allowing the frontend to analyze TikTok videos and get structured blueprints.

Now includes LangGraph-based pipeline routes for proper state management
and mechanics prompt handling.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AutoUGC Analyzer API",
    description="Backend API for TikTok video analysis and blueprint generation",
    version="1.1.0",
)

# CORS configuration for Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint to verify server is running."""
    return {
        "status": "ok",
        "service": "AutoUGC Analyzer API",
        "version": "1.1.0",
        "langgraph_enabled": True,
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "AutoUGC Analyzer API",
        "endpoints": {
            "health": "/health",
            # Legacy endpoints
            "analyze": "POST /api/v1/analyze",
            "job_status": "GET /api/v1/jobs/{job_id}",
            "mechanics_generate": "POST /api/v1/mechanics/generate",
            "mechanics_from_style": "POST /api/v1/mechanics/from-style",
            "mechanics_enhance": "POST /api/v1/mechanics/enhance",
            "mechanics_templates": "GET /api/v1/mechanics/templates",
            # New LangGraph pipeline endpoints
            "pipeline_start": "POST /api/v1/pipeline/start",
            "pipeline_generate_prompt": "POST /api/v1/pipeline/generate-prompt",
            "pipeline_job_status": "GET /api/v1/pipeline/jobs/{job_id}",
            "pipeline_job_stream": "GET /api/v1/pipeline/jobs/{job_id}/stream",
            "pipeline_health": "GET /api/v1/pipeline/health",
        },
    }


# Import and include routers
from api.routes import analyze, mechanics, pipeline

app.include_router(analyze.router, prefix="/api/v1", tags=["analysis"])
app.include_router(mechanics.router, prefix="/api/v1", tags=["mechanics"])
app.include_router(pipeline.router, prefix="/api/v1", tags=["pipeline"])


if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
