"""
Pipeline API routes - LangGraph-based UGC generation pipeline.

This module provides API endpoints that use the new LangGraph pipeline
for video analysis and UGC generation. It replaces the old plumbing
with proper state management and ensures mechanics prompts are used.

Endpoints:
- POST /pipeline/start - Start a full pipeline job
- POST /pipeline/analyze - Run only the analysis phase
- POST /pipeline/generate-prompt - Run only prompt generation
- GET /pipeline/jobs/{job_id} - Get job status
- GET /pipeline/jobs/{job_id}/stream - Stream job updates (SSE)
- DELETE /pipeline/jobs/{job_id} - Cancel/delete a job
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# JOB STORAGE (In-memory for development, use Redis in production)
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


class ProductContextModel(BaseModel):
    """Rich product context for custom mechanics."""

    type: str = Field(default="", description="Product type")
    interactions: list[str] = Field(
        default_factory=list, description="Key interactions"
    )
    tactile_features: list[str] = Field(
        default_factory=list, description="Tactile features"
    )
    sound_features: list[str] = Field(
        default_factory=list, description="Sound features"
    )
    size_description: str = Field(default="", description="Size context")
    highlight_feature: str = Field(default="", description="Primary feature")
    custom_instructions: str = Field(default="", description="Custom context")


class PipelineConfigModel(BaseModel):
    """Pipeline configuration options."""

    # Analysis settings
    whisper_mode: str = Field(default="local", description="Whisper mode: local or api")
    whisper_model: str = Field(default="base", description="Whisper model size")
    claude_model: str = Field(
        default="claude-sonnet-4-20250514", description="Claude model"
    )
    num_frames: int = Field(default=5, description="Frames for basic analysis")
    num_frames_for_scenes: int = Field(default=20, description="Frames for scenes")
    enable_enhanced_analysis: bool = Field(
        default=True, description="Enable scene/pacing analysis"
    )

    # Mechanics settings
    enable_mechanics: bool = Field(
        default=True, description="Enable mechanics-enhanced prompts"
    )
    product_category: str = Field(default="general", description="Product category")
    target_duration: float = Field(default=8.0, description="Target video duration")
    energy_level: str = Field(default="medium", description="Energy level")

    # Video generation settings
    video_model: str = Field(default="sora2", description="Video model")
    video_duration: int = Field(default=5, description="Video duration in seconds")
    aspect_ratio: str = Field(default="9:16", description="Aspect ratio")
    use_image_to_video: bool = Field(default=True, description="Use image-to-video")


class StartPipelineRequest(BaseModel):
    """Request to start the full pipeline."""

    video_url: str = Field(..., description="TikTok/Reel URL to analyze")
    product_images: list[str] = Field(
        default_factory=list, description="Product images (base64 or URLs)"
    )
    product_description: str = Field(default="", description="Product description")
    product_context: Optional[ProductContextModel] = Field(
        default=None, description="Rich product context"
    )
    config: Optional[PipelineConfigModel] = Field(
        default=None, description="Pipeline configuration"
    )
    skip_video_generation: bool = Field(
        default=False, description="Skip final video generation step"
    )


class GeneratePromptRequest(BaseModel):
    """Request to generate prompts from existing blueprint."""

    blueprint: dict[str, Any] = Field(..., description="Video blueprint data")
    blueprint_summary: Optional[dict[str, Any]] = Field(
        default=None, description="Simplified blueprint for UI"
    )
    product_images: list[str] = Field(
        default_factory=list, description="Product images"
    )
    product_description: str = Field(default="", description="Product description")
    product_context: Optional[ProductContextModel] = Field(
        default=None, description="Rich product context"
    )
    config: Optional[PipelineConfigModel] = Field(
        default=None, description="Pipeline configuration"
    )


class PipelineResponse(BaseModel):
    """Response for pipeline operations."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status")
    message: str = Field(default="", description="Status message")


class JobStatusResponse(BaseModel):
    """Response for job status queries."""

    job_id: str
    status: str
    current_step: str
    progress: dict[str, Any]
    error: Optional[str] = None

    # Results (populated when completed)
    blueprint: Optional[dict[str, Any]] = None
    blueprint_summary: Optional[dict[str, Any]] = None
    base_prompt: Optional[str] = None
    mechanics_prompt: Optional[str] = None
    final_prompt: Optional[str] = None
    prompt_source: Optional[str] = None
    generated_video_url: Optional[str] = None

    # Metadata
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


# =============================================================================
# PIPELINE EXECUTION
# =============================================================================


async def run_full_pipeline_async(job_id: str, initial_state: dict[str, Any]) -> None:
    """
    Run the full pipeline in the background.

    Args:
        job_id: Job identifier
        initial_state: Initial pipeline state
    """
    from src.pipeline import stream_pipeline
    from src.pipeline.state import PipelineStatus

    try:
        logger.info(f"Starting pipeline for job {job_id}")

        # Update status to running
        job_store.update(job_id, {"status": PipelineStatus.RUNNING.value})

        # Stream through the pipeline
        for node_name, state_update in stream_pipeline(initial_state):
            logger.debug(f"Job {job_id}: {node_name} completed")

            # Update job store with each state update
            job_store.update(job_id, state_update)

            # Check for errors
            if state_update.get("status") == PipelineStatus.FAILED.value:
                logger.error(
                    f"Job {job_id} failed at {node_name}: {state_update.get('error')}"
                )
                return

        logger.info(f"Pipeline completed for job {job_id}")

    except Exception as e:
        logger.exception(f"Pipeline error for job {job_id}")
        job_store.update(
            job_id,
            {
                "status": PipelineStatus.FAILED.value,
                "error": str(e),
                "completed_at": datetime.utcnow().isoformat(),
            },
        )


async def run_prompt_generation_async(
    job_id: str, initial_state: dict[str, Any]
) -> None:
    """
    Run only the prompt generation phase.

    Args:
        job_id: Job identifier
        initial_state: Initial pipeline state (must include blueprint)
    """
    from src.pipeline.nodes import (
        analyze_product_node,
        finalize_prompt_node,
        generate_base_prompt_node,
        generate_mechanics_node,
    )
    from src.pipeline.state import PipelineStatus

    try:
        logger.info(f"Starting prompt generation for job {job_id}")
        job_store.update(job_id, {"status": PipelineStatus.RUNNING.value})

        state = initial_state.copy()

        # Step 1: Analyze product (if images provided)
        if state.get("product_images"):
            logger.info(f"Job {job_id}: Analyzing product...")
            result = analyze_product_node(state)
            state.update(result)
            job_store.update(job_id, result)

        # Step 2: Generate base prompt
        logger.info(f"Job {job_id}: Generating base prompt...")
        result = generate_base_prompt_node(state)
        state.update(result)
        job_store.update(job_id, result)

        if state.get("error"):
            logger.error(f"Job {job_id} failed: {state.get('error')}")
            return

        # Step 3: Generate mechanics prompt
        logger.info(f"Job {job_id}: Generating mechanics prompt...")
        result = generate_mechanics_node(state)
        state.update(result)
        job_store.update(job_id, result)

        # Step 4: Finalize prompt (THE KEY FIX!)
        logger.info(f"Job {job_id}: Finalizing prompt...")
        result = finalize_prompt_node(state)
        state.update(result)
        job_store.update(job_id, result)

        # Mark as completed
        job_store.update(
            job_id,
            {
                "status": PipelineStatus.COMPLETED.value,
                "completed_at": datetime.utcnow().isoformat(),
            },
        )

        prompt_source = result.get("prompt_metadata", {}).get("source", "unknown")
        logger.info(
            f"Prompt generation completed for job {job_id}, source: {prompt_source}"
        )

    except Exception as e:
        logger.exception(f"Prompt generation error for job {job_id}")
        job_store.update(
            job_id,
            {
                "status": "failed",
                "error": str(e),
                "completed_at": datetime.utcnow().isoformat(),
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
    Start the full UGC generation pipeline.

    This endpoint:
    1. Downloads and analyzes the TikTok video
    2. Generates a blueprint
    3. Creates prompts (with mechanics enhancement)
    4. Optionally generates video

    The job runs in the background. Poll /pipeline/jobs/{job_id} for status.
    """
    from src.pipeline import create_initial_state
    from src.pipeline.state import PipelineConfig

    try:
        job_id = str(uuid.uuid4())

        # Build config
        config_dict = request.config.model_dump() if request.config else {}
        config = PipelineConfig(**config_dict)

        # Build product context
        product_context = None
        if request.product_context:
            product_context = {
                "type": request.product_context.type,
                "interactions": request.product_context.interactions,
                "tactile_features": request.product_context.tactile_features,
                "sound_features": request.product_context.sound_features,
                "size_description": request.product_context.size_description,
                "highlight_feature": request.product_context.highlight_feature,
                "custom_instructions": request.product_context.custom_instructions,
            }

        # Create initial state
        initial_state = create_initial_state(
            video_url=request.video_url,
            product_images=request.product_images,
            product_description=request.product_description,
            product_context=product_context,
            config=config,
            job_id=job_id,
        )

        # Store job
        job_store.create(job_id, initial_state)

        # Start background task
        background_tasks.add_task(run_full_pipeline_async, job_id, initial_state)

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


@router.post("/pipeline/generate-prompt", response_model=PipelineResponse)
async def generate_prompt(
    request: GeneratePromptRequest,
    background_tasks: BackgroundTasks,
):
    """
    Generate prompts from an existing blueprint.

    Use this when you already have a blueprint (from previous analysis)
    and just want to generate/regenerate prompts.

    This endpoint ensures the mechanics-enhanced prompt is used when available.
    """
    from src.pipeline.state import PipelineConfig, create_initial_state

    try:
        job_id = str(uuid.uuid4())

        # Build config
        config_dict = request.config.model_dump() if request.config else {}
        config = PipelineConfig(**config_dict)

        # Build product context
        product_context = None
        if request.product_context:
            product_context = request.product_context.model_dump()

        # Create initial state with blueprint already populated
        initial_state = create_initial_state(
            video_url="",  # Not needed for prompt generation
            product_images=request.product_images,
            product_description=request.product_description,
            product_context=product_context,
            config=config,
            job_id=job_id,
        )

        # Add the provided blueprint
        initial_state["blueprint"] = request.blueprint
        if request.blueprint_summary:
            initial_state["blueprint_summary"] = request.blueprint_summary

        # Store job
        job_store.create(job_id, initial_state)

        # Start background task
        background_tasks.add_task(run_prompt_generation_async, job_id, initial_state)

        return PipelineResponse(
            job_id=job_id,
            status="started",
            message="Prompt generation started. Poll /pipeline/jobs/{job_id} for status.",
        )

    except Exception as e:
        logger.exception("Failed to start prompt generation")
        raise HTTPException(
            status_code=500, detail=f"Failed to start prompt generation: {str(e)}"
        )


@router.get("/pipeline/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the current status of a pipeline job.

    Returns the full state including:
    - Progress information
    - Blueprint (if analysis complete)
    - Prompts (if generation complete)
    - Video URL (if generation complete)
    """
    job = job_store.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    state = job["state"]

    # Extract prompt metadata
    prompt_metadata = state.get("prompt_metadata", {})

    return JobStatusResponse(
        job_id=job_id,
        status=state.get("status", "unknown"),
        current_step=state.get("current_step", ""),
        progress=state.get("progress", {}),
        error=state.get("error") or None,
        # Results
        blueprint=state.get("blueprint") or None,
        blueprint_summary=state.get("blueprint_summary") or None,
        base_prompt=state.get("base_prompt") or None,
        mechanics_prompt=state.get("mechanics_prompt") or None,
        final_prompt=state.get("final_prompt") or None,
        prompt_source=prompt_metadata.get("source") or None,
        generated_video_url=state.get("generated_video_url") or None,
        # Metadata
        created_at=job.get("created_at"),
        completed_at=state.get("completed_at") or None,
    )


@router.get("/pipeline/jobs/{job_id}/stream")
async def stream_job_status(job_id: str):
    """
    Stream job status updates using Server-Sent Events (SSE).

    This allows real-time progress updates in the frontend.
    """
    job = job_store.get(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    async def event_generator():
        """Generate SSE events for job status updates."""
        last_step = ""
        last_status = ""

        while True:
            job = job_store.get(job_id)
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break

            state = job["state"]
            current_step = state.get("current_step", "")
            current_status = state.get("status", "")

            # Send update if something changed
            if current_step != last_step or current_status != last_status:
                event_data = {
                    "job_id": job_id,
                    "status": current_status,
                    "current_step": current_step,
                    "progress": state.get("progress", {}),
                }

                # Include error if failed
                if current_status == "failed":
                    event_data["error"] = state.get("error", "Unknown error")

                # Include results if completed
                if current_status == "completed":
                    event_data["final_prompt"] = (
                        state.get("final_prompt", "")[:100] + "..."
                    )
                    event_data["prompt_source"] = state.get("prompt_metadata", {}).get(
                        "source"
                    )
                    if state.get("generated_video_url"):
                        event_data["video_url"] = state.get("generated_video_url")

                yield f"data: {json.dumps(event_data)}\n\n"

                last_step = current_step
                last_status = current_status

            # Stop streaming if job is done
            if current_status in ("completed", "failed"):
                break

            await asyncio.sleep(1)  # Poll every second

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.delete("/pipeline/jobs/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a pipeline job.

    This removes the job from storage. Use for cleanup after retrieving results.
    """
    success = job_store.delete(job_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return {"message": f"Job {job_id} deleted successfully"}


@router.get("/pipeline/health")
async def pipeline_health():
    """
    Health check for the pipeline API.

    Returns information about pipeline configuration and status.
    """
    import os

    return {
        "status": "ok",
        "pipeline_version": "1.0.0",
        "langgraph_enabled": True,
        "mechanics_enabled": True,
        "api_keys_configured": {
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
            "fal": bool(os.getenv("FAL_KEY")),
            "langsmith": bool(os.getenv("LANGCHAIN_API_KEY")),
        },
        "endpoints": {
            "start_pipeline": "POST /pipeline/start",
            "generate_prompt": "POST /pipeline/generate-prompt",
            "job_status": "GET /pipeline/jobs/{job_id}",
            "job_stream": "GET /pipeline/jobs/{job_id}/stream",
            "delete_job": "DELETE /pipeline/jobs/{job_id}",
        },
    }
