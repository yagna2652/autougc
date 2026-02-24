"""
Pipeline API routes - Simple UGC generation pipeline.

Endpoints:
- POST /pipeline/start - Start a pipeline job
- GET /pipeline/jobs/{job_id} - Get job status
- GET /pipeline/stream/{job_id} - SSE stream of pipeline events
- GET /pipeline/health - Health check
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# SIMPLE API KEY AUTH
# =============================================================================


def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")) -> str:
    """Verify the API key from request header."""
    expected_key = os.getenv("API_KEY")

    # If no API_KEY configured, allow all requests (dev mode)
    if not expected_key:
        return "no-key-configured"

    if not x_api_key:
        raise HTTPException(
            status_code=401, detail="Missing API key. Include X-API-Key header."
        )

    if x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API key.")

    return x_api_key


# =============================================================================
# JOB STORAGE (In-memory for development)
# =============================================================================


class JobStore:
    """Simple in-memory job storage."""

    def __init__(self):
        self.jobs: dict[str, dict[str, Any]] = {}
        self.event_logs: dict[str, list] = {}

    def create(self, job_id: str, initial_state: dict[str, Any]) -> None:
        self.jobs[job_id] = {
            "state": initial_state,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        self.event_logs[job_id] = []

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

    def push_event(self, job_id: str, event: dict) -> None:
        if job_id in self.event_logs:
            self.event_logs[job_id].append(event)

    def get_events(self, job_id: str) -> list:
        return self.event_logs.get(job_id, [])


# Global job store
job_store = JobStore()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class ProductIdentityPack(BaseModel):
    """Multi-angle product reference images for identity fidelity."""

    front: str = Field(default="", description="Front view image (base64 or URL)")
    side_45: str = Field(default="", description="45-degree angle view")
    back: str = Field(default="", description="Back view")
    top: str = Field(default="", description="Top view")
    close_up_logo: str = Field(default="", description="Close-up of logo/markings")
    close_up_material: str = Field(
        default="", description="Close-up of material texture"
    )


class PipelineConfigModel(BaseModel):
    """Pipeline configuration options."""

    vision_model: str = Field(
        default="openai/gpt-4o-mini", description="OpenRouter vision model to use"
    )
    num_frames: int = Field(default=5, description="Number of frames to extract")
    video_model: str = Field(
        default="sora", description="Video model (sora, kling, or kling-v3)"
    )
    video_duration: int = Field(default=5, description="Video duration in seconds")
    aspect_ratio: str = Field(default="9:16", description="Video aspect ratio")
    i2v_image_index: int = Field(
        default=0, description="Which product image to use for I2V (0-indexed)"
    )

    # Identity fidelity controls (fastest gains from research report)
    use_identity_pack: bool = Field(
        default=False, description="Enable multi-reference identity pack"
    )
    use_tail_image: bool = Field(
        default=False, description="Use same image as end frame for consistency"
    )
    segment_duration: int = Field(
        default=2,
        description="Duration per segment for anchor strategy (2-3s recommended)",
    )
    use_anchor_frames: bool = Field(
        default=False, description="Generate keyframes first, then motion segments"
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
    product_identity_pack: Optional[ProductIdentityPack] = Field(
        default=None,
        description="Multi-angle product reference images for identity fidelity",
    )
    product_category: Optional[str] = Field(
        default=None,
        description="Product category (auto-detected if not provided)",
    )
    product_mechanics: str = Field(
        default="",
        description="Physical interaction rules/mechanics (auto-loaded if empty)",
    )
    fal_key: Optional[str] = Field(
        default=None, description="Fal.ai API key (overrides FAL_KEY env var)"
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
    scene_image_url: str = ""  # Fal CDN URL of generated scene image
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
    "analyze_video": "Analyzing video style with vision model...",
    "generate_prompt": "Generating video prompt...",
    "generate_scene_image": "Generating scene image with Nano Banana Pro...",
    "generate_video": "Generating video with AI (this may take 2-5 minutes)...",
}

# Ordered list of pipeline nodes
NODE_ORDER = [
    "download_video",
    "extract_frames",
    "analyze_video",
    "generate_prompt",
    "generate_scene_image",
    "generate_video",
]


def _get_filtered_output(node_name: str, state_update: dict) -> dict:
    """Return a filtered output dict for each node (no base64 images)."""
    if node_name == "download_video":
        return {"video_path": state_update.get("video_path")}
    elif node_name == "extract_frames":
        return {"frame_count": len(state_update.get("frames", []))}
    elif node_name == "analyze_video":
        return {"video_analysis": state_update.get("video_analysis")}
    elif node_name == "generate_prompt":
        return {
            "video_prompt": state_update.get("video_prompt"),
            "suggested_script": state_update.get("suggested_script"),
            "scene_description": state_update.get("scene_description"),
        }
    elif node_name == "generate_scene_image":
        return {"scene_image_url": state_update.get("scene_image_url")}
    elif node_name == "generate_video":
        return {
            "generated_video_url": state_update.get("generated_video_url"),
            "i2v_image_url": state_update.get("i2v_image_url"),
        }
    return {}


async def run_pipeline_async(job_id: str, initial_state: dict[str, Any]) -> None:
    """
    Run the pipeline in the background, pushing SSE events as nodes complete.

    Args:
        job_id: Job identifier
        initial_state: Initial pipeline state
    """
    from src.pipeline import stream_pipeline

    try:
        logger.info(f"{'=' * 60}")
        logger.info(f"PIPELINE STARTED | Job: {job_id[:8]}...")
        logger.info(f"{'=' * 60}")

        # Update status to running
        job_store.update(job_id, {"status": "running"})

        # Push node_start for the first node
        job_store.push_event(
            job_id,
            {"type": "node_start", "node": NODE_ORDER[0], "ts": time.time()},
        )

        def sync_runner() -> None:
            """Run the blocking pipeline generator in a thread."""
            step_count = 0
            total_steps = len(NODE_ORDER)

            for node_name, state_update in stream_pipeline(initial_state):
                step_count += 1
                step_desc = STEP_DESCRIPTIONS.get(node_name, node_name)

                logger.info(f"")
                logger.info(f"[{step_count}/{total_steps}] ✓ {node_name} COMPLETED")

                # Log details
                if node_name == "download_video" and state_update.get("video_path"):
                    logger.info(f"    → Video saved to: {state_update['video_path']}")

                if node_name == "extract_frames" and state_update.get("frames"):
                    logger.info(
                        f"    → Extracted {len(state_update['frames'])} frames"
                    )

                if node_name == "analyze_video" and state_update.get("video_analysis"):
                    analysis = state_update["video_analysis"]
                    style = analysis.get("style", "unknown")
                    energy = analysis.get("energy", "unknown")
                    logger.info(f"    → Style: {style}, Energy: {energy}")

                if node_name == "generate_prompt" and state_update.get("video_prompt"):
                    prompt = state_update["video_prompt"]
                    logger.info(f"    → Prompt length: {len(prompt)} chars")
                    logger.info(f"    → Preview: {prompt[:100]}...")

                if node_name == "generate_scene_image" and state_update.get(
                    "scene_image_url"
                ):
                    logger.info(
                        f"    → Scene image URL: {state_update['scene_image_url']}"
                    )

                if node_name == "generate_video" and state_update.get(
                    "generated_video_url"
                ):
                    logger.info(
                        f"    → Video URL: {state_update['generated_video_url']}"
                    )

                # Build filtered output (strips base64 images)
                filtered_output = _get_filtered_output(node_name, state_update)

                # Push node_done event
                job_store.push_event(
                    job_id,
                    {
                        "type": "node_done",
                        "node": node_name,
                        "output": filtered_output,
                        "ts": time.time(),
                    },
                )

                # Update job store with full state
                job_store.update(job_id, state_update)

                # Check for errors
                if state_update.get("error"):
                    logger.error(f"")
                    logger.error(f"{'=' * 60}")
                    logger.error(f"PIPELINE FAILED at {node_name}")
                    logger.error(f"Error: {state_update.get('error')}")
                    logger.error(f"{'=' * 60}")
                    job_store.update(job_id, {"status": "failed"})
                    job_store.push_event(
                        job_id,
                        {
                            "type": "done",
                            "status": "failed",
                            "error": state_update.get("error"),
                            "ts": time.time(),
                        },
                    )
                    return

                # Push node_start for the next node
                if step_count < total_steps:
                    job_store.push_event(
                        job_id,
                        {
                            "type": "node_start",
                            "node": NODE_ORDER[step_count],
                            "ts": time.time(),
                        },
                    )

            # Mark as completed
            job_store.update(
                job_id,
                {"status": "completed", "current_step": "done"},
            )
            job_store.push_event(
                job_id,
                {"type": "done", "status": "completed", "ts": time.time()},
            )
            logger.info(f"")
            logger.info(f"{'=' * 60}")
            logger.info(f"PIPELINE COMPLETED | Job: {job_id[:8]}...")
            logger.info(f"{'=' * 60}")

        # Run the blocking pipeline in a thread to keep the event loop free
        await asyncio.to_thread(sync_runner)

    except Exception as e:
        logger.exception(f"Pipeline error for job {job_id}")
        logger.error(f"")
        logger.error(f"{'=' * 60}")
        logger.error(f"PIPELINE CRASHED | Job: {job_id[:8]}...")
        logger.error(f"Exception: {str(e)}")
        logger.error(f"{'=' * 60}")
        job_store.update(
            job_id,
            {"status": "failed", "error": str(e)},
        )
        job_store.push_event(
            job_id,
            {"type": "done", "status": "failed", "error": str(e), "ts": time.time()},
        )


# =============================================================================
# API ENDPOINTS
# =============================================================================


@router.post("/pipeline/start", response_model=PipelineResponse)
async def start_pipeline(
    request: StartPipelineRequest,
    background_tasks: BackgroundTasks,
    _: str = Depends(verify_api_key),
):
    """
    Start the UGC generation pipeline.

    This endpoint:
    1. Downloads the TikTok video
    2. Extracts frames
    3. Analyzes with Claude Vision
    4. Generates a video prompt
    5. Generates the video

    The job runs in the background. Poll /pipeline/jobs/{job_id} for status,
    or stream events via GET /pipeline/stream/{job_id}.
    """
    from src.pipeline import create_initial_state

    try:
        job_id = str(uuid.uuid4())

        # Build config dict
        config = {}
        if request.config:
            config = request.config.model_dump()

        # Create initial state
        identity_pack = (
            request.product_identity_pack.model_dump()
            if request.product_identity_pack
            else None
        )
        initial_state = create_initial_state(
            video_url=request.video_url,
            product_description=request.product_description,
            product_images=request.product_images,
            product_identity_pack=identity_pack,
            product_category=request.product_category,
            product_mechanics=request.product_mechanics,
            config=config,
            job_id=job_id,
        )

        # Store job
        job_store.create(job_id, initial_state)

        # Apply runtime API key overrides
        if request.fal_key:
            os.environ["FAL_KEY"] = request.fal_key

        # Start background task
        background_tasks.add_task(run_pipeline_async, job_id, initial_state)

        return PipelineResponse(
            job_id=job_id,
            status="started",
            message="Pipeline started. Stream events via /pipeline/stream/{job_id}.",
        )

    except Exception as e:
        logger.exception("Failed to start pipeline")
        raise HTTPException(
            status_code=500, detail=f"Failed to start pipeline: {str(e)}"
        )


@router.get("/pipeline/stream/{job_id}")
async def stream_job_events(job_id: str):
    """
    Stream pipeline events via Server-Sent Events.

    No auth required — job_id UUID is effectively the access token.
    Events: node_start, node_done, done, ping
    """
    if not job_store.get(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    async def generator():
        cursor = 0
        last_ping = time.time()

        while True:
            events = job_store.get_events(job_id)

            # Drain any buffered events
            while cursor < len(events):
                event = events[cursor]
                yield f"data: {json.dumps(event)}\n\n"
                cursor += 1
                # Stop after sending the terminal event
                if event.get("type") == "done":
                    return

            # Keepalive ping every 15 seconds
            if time.time() - last_ping > 15:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                last_ping = time.time()

            await asyncio.sleep(0.2)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/pipeline/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    _: str = Depends(verify_api_key),
):
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
        scene_image_url=state.get("scene_image_url", ""),
        i2v_image_url=state.get("i2v_image_url", ""),
        generated_video_url=state.get("generated_video_url", ""),
        created_at=job.get("created_at", ""),
        updated_at=job.get("updated_at", ""),
    )


@router.delete("/pipeline/jobs/{job_id}")
async def delete_job(
    job_id: str,
    _: str = Depends(verify_api_key),
):
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
    from src.tracing import is_tracing_enabled

    return {
        "status": "ok",
        "tracing_enabled": is_tracing_enabled(),
        "auth_enabled": bool(os.getenv("API_KEY")),
        "api_keys": {
            "openrouter": bool(os.getenv("OPENROUTER_API_KEY")),
            "fal": bool(os.getenv("FAL_KEY")),
            "langsmith": bool(os.getenv("LANGCHAIN_API_KEY")),
        },
    }
