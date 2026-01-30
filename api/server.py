"""
FastAPI server for AutoUGC video analysis backend.

This server exposes the Python BlueprintGenerator to the Next.js web UI,
allowing the frontend to analyze TikTok videos and get structured blueprints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="AutoUGC Analyzer API",
    description="Backend API for TikTok video analysis and blueprint generation",
    version="1.0.0",
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
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "AutoUGC Analyzer API",
        "endpoints": {
            "health": "/health",
            "analyze": "POST /api/v1/analyze",
            "job_status": "GET /api/v1/jobs/{job_id}",
            "mechanics_generate": "POST /api/v1/mechanics/generate",
            "mechanics_from_style": "POST /api/v1/mechanics/from-style",
            "mechanics_enhance": "POST /api/v1/mechanics/enhance",
            "mechanics_templates": "GET /api/v1/mechanics/templates",
        },
    }


# Import and include routers
from api.routes import analyze
from api.routes import mechanics

app.include_router(analyze.router, prefix="/api/v1", tags=["analysis"])
app.include_router(mechanics.router, prefix="/api/v1", tags=["mechanics"])


if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
