"""
Pipeline API routes - Simple UGC generation pipeline.

Endpoints:
- POST /pipeline/start - Start a pipeline job
- GET /pipeline/jobs/{job_id} - Get job status
- GET /pipeline/health - Health check
"""

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
    video_model: str = Field(default="sora", description="Video model (sora or kling)")
    video_duration: int = Field(default=5, description="Video duration in seconds")
    aspect_ratio: str = Field(default="9:16", description="Video aspect ratio")
    i2v_image_index: int = Field(
        default=0, description="Which product image to use for I2V (0-indexed)"
    )


class StartPipelineRequest(BaseModel):
    """Request to start the pipeline.

    Only video_url is required. If product info is not provided,
    the default product (mechanical keyboard keychain) is loaded
    automatically from assets/products/keychain/.
    """

    video_url: str = Field(..., description="TikTok/Reel URL to analyze")
    product_description: str = Field(
        default="",
        description="Product description (auto-loaded from default product if empty)",
    )
    product_images: list[str] = Field(
        default_factory=list,
        description="Product images as base64 or URLs (auto-loaded if empty)",
    )
    product_category: Optional[str] = Field(
        default=None,
        description="Product category (auto-detected if not provided)",
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
    i2v_image_url: str = ""  # Fal CDN URL used for I2V
    generated_video_url: str = ""
    created_at: str = ""
    updated_at: str = ""


# =============================================================================
# BACKGROUND TASKS
# =============================================================================


# Human-readable descriptions for each pipeline step
STEP_DESCRIPTIONS = {
    "download_video": "Downloading TikTok video...",
    "extract_frames": "Extracting key frames from video...",
    "analyze_video": "Analyzing video style with Claude Vision...",
    "generate_prompt": "Generating video prompt with Claude...",
    "generate_video": "Generating video with AI (this may take 2-5 minutes)...",
}


async def run_pipeline_async(job_id: str, initial_state: dict[str, Any]) -> None:
    """
    Run the pipeline in the background.

    Args:
        job_id: Job identifier
        initial_state: Initial pipeline state
    """
    from src.pipeline import stream_pipeline

    try:
        logger.info(f"{'='*60}")
        logger.info(f"PIPELINE STARTED | Job: {job_id[:8]}...")
        logger.info(f"{'='*60}")

        # Update status to running
        job_store.update(job_id, {"status": "running"})

        step_count = 0
        total_steps = len(STEP_DESCRIPTIONS)

        # Stream through the pipeline
        for node_name, state_update in stream_pipeline(initial_state):
            step_count += 1
            step_desc = STEP_DESCRIPTIONS.get(node_name, node_name)

            # Log completion with step number
            logger.info(f"")
            logger.info(f"[{step_count}/{total_steps}] ✓ {node_name} COMPLETED")

            # Log any interesting details from the state update
            if node_name == "download_video" and state_update.get("video_path"):
                logger.info(f"    → Video saved to: {state_update['video_path']}")

            if node_name == "extract_frames" and state_update.get("frames"):
                logger.info(f"    → Extracted {len(state_update['frames'])} frames")

            if node_name == "analyze_video" and state_update.get("video_analysis"):
                analysis = state_update["video_analysis"]
                style = analysis.get("style", "unknown")
                energy = analysis.get("energy", "unknown")
                logger.info(f"    → Style: {style}, Energy: {energy}")

            if node_name == "generate_prompt" and state_update.get("video_prompt"):
                prompt = state_update["video_prompt"]
                logger.info(f"    → Prompt length: {len(prompt)} chars")
                # Show first 100 chars of prompt
                logger.info(f"    → Preview: {prompt[:100]}...")

            if node_name == "generate_video" and state_update.get("generated_video_url"):
                logger.info(f"    → Video URL: {state_update['generated_video_url']}")

            # Update job store with each state update
            job_store.update(job_id, state_update)

            # Check for errors
            if state_update.get("error"):
                logger.error(f"")
                logger.error(f"{'='*60}")
                logger.error(f"PIPELINE FAILED at {node_name}")
                logger.error(f"Error: {state_update.get('error')}")
                logger.error(f"{'='*60}")
                job_store.update(job_id, {"status": "failed"})
                return

            # Log what's coming next
            if step_count < total_steps:
                next_steps = list(STEP_DESCRIPTIONS.keys())
                if step_count < len(next_steps):
                    next_step = next_steps[step_count]
                    next_desc = STEP_DESCRIPTIONS.get(next_step, next_step)
                    logger.info(f"")
                    logger.info(f"[{step_count + 1}/{total_steps}] → {next_desc}")

        # Mark as completed
        job_store.update(
            job_id,
            {
                "status": "completed",
                "current_step": "done",
            },
        )
        logger.info(f"")
        logger.info(f"{'='*60}")
        logger.info(f"PIPELINE COMPLETED | Job: {job_id[:8]}...")
        logger.info(f"{'='*60}")

    except Exception as e:
        logger.exception(f"Pipeline error for job {job_id}")
        logger.error(f"")
        logger.error(f"{'='*60}")
        logger.error(f"PIPELINE CRASHED | Job: {job_id[:8]}...")
        logger.error(f"Exception: {str(e)}")
        logger.error(f"{'='*60}")
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
        # If product info not provided, create_initial_state will auto-load default
        initial_state = create_initial_state(
            video_url=request.video_url,
            product_description=request.product_description,
            product_images=request.product_images,
            product_category=request.product_category,  # None triggers auto-load
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
        i2v_image_url=state.get("i2v_image_url", ""),
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
