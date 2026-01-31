"""
Pipeline API routes - Simple UGC generation pipeline.

Endpoints:
- POST /pipeline/start - Start a pipeline job
- GET /pipeline/jobs/{job_id} - Get job status
- GET /pipeline/health - Health check
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# JOB STORAGE (In-memory for development)
# =============================================================================


class JobStore:
    """Simple in-memory job storage."""

    def __init__(self):
        self.jobs: dict[str, dict[str, Any]] = {}

    def create(self, job_id: str, initial_state: dict[str, Any]) -> None:
        self.jobs[job_id] = {
            "state": initial_state,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

    def get(self, job_id: str) -> Optional[dict[str, Any]]:
        return self.jobs.get(job_id)

    def update(self, job_id: str, state_update: dict[str, Any]) -> None:
        if job_id in self.jobs:
            self.jobs[job_id]["state"].update(state_update)
            self.jobs[job_id]["updated_at"] = datetime.utcnow().isoformat()

    def delete(self, job_id: str) -> bool:
        if job_id in self.jobs:
            del self.jobs[job_id]
            return True
        return False

    def get_state(self, job_id: str) -> Optional[dict[str, Any]]:
        job = self.jobs.get(job_id)
        return job["state"] if job else None


# Global job store
job_store = JobStore()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class PipelineConfigModel(BaseModel):
    """Pipeline configuration options."""

    claude_model: str = Field(
        default="claude-sonnet-4-20250514", description="Claude model to use"
    )
    num_frames: int = Field(default=5, description="Number of frames to extract")
    video_model: str = Field(default="kling", description="Video model (kling or sora)")
    video_duration: int = Field(default=5, description="Video duration in seconds")
    aspect_ratio: str = Field(default="9:16", description="Video aspect ratio")


class StartPipelineRequest(BaseModel):
    """Request to start the pipeline."""

    video_url: str = Field(..., description="TikTok/Reel URL to analyze")
    product_description: str = Field(default="", description="Product description")
    product_images: list[str] = Field(
        default_factory=list, description="Product images (base64 or URLs)"
    )
    config: Optional[PipelineConfigModel] = Field(
        default=None, description="Pipeline configuration"
    )


class PipelineResponse(BaseModel):
    """Response for pipeline operations."""

    job_id: str
    status: str
    message: str = ""


class JobStatusResponse(BaseModel):
    """Response for job status."""

    job_id: str
    status: str
    current_step: str = ""
    error: str = ""
    video_analysis: Optional[dict[str, Any]] = None
    video_prompt: str = ""
    suggested_script: str = ""
    generated_video_url: str = ""
    created_at: str = ""
    updated_at: str = ""


# =============================================================================
# BACKGROUND TASKS
# =============================================================================


async def run_pipeline_async(job_id: str, initial_state: dict[str, Any]) -> None:
    """
    Run the pipeline in the background.

    Args:
        job_id: Job identifier
        initial_state: Initial pipeline state
    """
    from src.pipeline import stream_pipeline

    try:
        logger.info(f"Starting pipeline for job {job_id}")

        # Update status to running
        job_store.update(job_id, {"status": "running"})

        # Stream through the pipeline
        for node_name, state_update in stream_pipeline(initial_state):
            logger.info(f"Job {job_id}: {node_name} completed")

            # Update job store with each state update
            job_store.update(job_id, state_update)

            # Check for errors
            if state_update.get("error"):
                logger.error(
                    f"Job {job_id} failed at {node_name}: {state_update.get('error')}"
                )
                job_store.update(job_id, {"status": "failed"})
                return

        # Mark as completed
        job_store.update(
            job_id,
            {
                "status": "completed",
                "current_step": "done",
            },
        )
        logger.info(f"Pipeline completed for job {job_id}")

    except Exception as e:
        logger.exception(f"Pipeline error for job {job_id}")
        job_store.update(
            job_id,
            {
                "status": "failed",
                "error": str(e),
            },
        )


# =============================================================================
# API ENDPOINTS
# =============================================================================


@router.post("/pipeline/start", response_model=PipelineResponse)
async def start_pipeline(
    request: StartPipelineRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start the UGC generation pipeline.

    This endpoint:
    1. Downloads the TikTok video
    2. Extracts frames
    3. Analyzes with Claude Vision
    4. Generates a video prompt
    5. Generates the video

    The job runs in the background. Poll /pipeline/jobs/{job_id} for status.
    """
    from src.pipeline import create_initial_state

    try:
        job_id = str(uuid.uuid4())

        # Build config dict
        config = {}
        if request.config:
            config = request.config.model_dump()

        # Create initial state
        initial_state = create_initial_state(
            video_url=request.video_url,
            product_description=request.product_description,
            product_images=request.product_images,
            config=config,
            job_id=job_id,
        )

        # Store job
        job_store.create(job_id, initial_state)

        # Start background task
        background_tasks.add_task(run_pipeline_async, job_id, initial_state)

        return PipelineResponse(
            job_id=job_id,
            status="started",
            message="Pipeline started. Poll /pipeline/jobs/{job_id} for status.",
        )

    except Exception as e:
        logger.exception("Failed to start pipeline")
        raise HTTPException(
            status_code=500, detail=f"Failed to start pipeline: {str(e)}"
        )


@router.get("/pipeline/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a pipeline job.

    Returns the current state including:
    - status (pending, running, completed, failed)
    - current_step
    - video_analysis (if completed)
    - video_prompt (if generated)
    - generated_video_url (if completed)
    """
    job = job_store.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = job["state"]

    return JobStatusResponse(
        job_id=job_id,
        status=state.get("status", "unknown"),
        current_step=state.get("current_step", ""),
        error=state.get("error", ""),
        video_analysis=state.get("video_analysis"),
        video_prompt=state.get("video_prompt", ""),
        suggested_script=state.get("suggested_script", ""),
        generated_video_url=state.get("generated_video_url", ""),
        created_at=job.get("created_at", ""),
        updated_at=job.get("updated_at", ""),
    )


@router.delete("/pipeline/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job from storage."""
    if job_store.delete(job_id):
        return {"status": "deleted", "job_id": job_id}
    raise HTTPException(status_code=404, detail=f"Job {job_id} not found")


@router.get("/pipeline/health")
async def pipeline_health():
    """
    Health check for the pipeline.

    Returns status of dependencies and configuration.
    """
    import os

    from src.tracing import is_tracing_enabled

    return {
        "status": "ok",
        "tracing_enabled": is_tracing_enabled(),
        "api_keys": {
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
            "fal": bool(os.getenv("FAL_KEY")),
            "langsmith": bool(os.getenv("LANGCHAIN_API_KEY")),
        },
    }
