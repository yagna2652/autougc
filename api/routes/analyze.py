"""
Analysis API routes.

Endpoints for starting video analysis jobs and checking job status.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import uuid
import asyncio

from api.job_manager import job_manager, JobStatus
from api.video_downloader import VideoDownloader

router = APIRouter()
video_downloader = VideoDownloader()


class AnalyzeRequest(BaseModel):
    """Request body for video analysis."""
    video_url: str = Field(..., description="TikTok video URL to analyze")
    options: Optional[Dict[str, Any]] = Field(
        default={
            "enhanced": True,
            "whisper_mode": "local",
            "num_frames": 5,
            "scene_frames": 20
        },
        description="Analysis options"
    )


class AnalyzeResponse(BaseModel):
    """Response for video analysis request."""
    job_id: str
    status: str
    message: str
    progress_url: str


class JobResponse(BaseModel):
    """Response for job status request."""
    job_id: str
    status: str
    progress: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_video(request: AnalyzeRequest):
    """
    Start a video analysis job.

    This endpoint:
    1. Downloads the TikTok video
    2. Queues an analysis job
    3. Returns a job_id for polling status

    Args:
        request: Analysis request with video URL and options

    Returns:
        Job information including job_id and progress_url
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Create job
        await job_manager.create_job(job_id)

        # Download video in background
        async def download_and_process():
            try:
                # Update progress
                job_manager._progress_callback(job_id, "Downloading video...", 0, 11)

                # Download video
                video_path = await asyncio.get_event_loop().run_in_executor(
                    None,
                    video_downloader.download,
                    request.video_url
                )

                # Start processing
                await job_manager.process_job(
                    job_id=job_id,
                    video_path=str(video_path),
                    options=request.options or {}
                )

                # Cleanup video file after processing
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    video_downloader.cleanup,
                    video_path
                )

            except Exception as e:
                # Mark job as failed
                if job_id in job_manager.jobs:
                    job_manager.jobs[job_id].status = JobStatus.FAILED
                    job_manager.jobs[job_id].error = str(e)

        # Start background task
        asyncio.create_task(download_and_process())

        return AnalyzeResponse(
            job_id=job_id,
            status="queued",
            message="Video analysis job created successfully",
            progress_url=f"/api/v1/jobs/{job_id}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create analysis job: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """
    Get the status of an analysis job.

    Args:
        job_id: Unique job identifier

    Returns:
        Job status, progress, and result (if completed)

    Raises:
        HTTPException: If job not found
    """
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    return JobResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        result=job.result,
        error=job.error
    )


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a completed or failed job.

    Args:
        job_id: Unique job identifier

    Returns:
        Success message

    Raises:
        HTTPException: If job not found
    """
    success = job_manager.delete_job(job_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    return {"message": f"Job {job_id} deleted successfully"}
