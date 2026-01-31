"""
Download Video Node - Downloads TikTok/Reel videos for analysis.

This node handles downloading videos from various social media platforms
using the existing video_downloader utility.
"""

import logging
from typing import Any

from src.pipeline.state import (
    PipelineState,
    PipelineStatus,
    PipelineStep,
    mark_failed,
    update_progress,
)

logger = logging.getLogger(__name__)


def download_video_node(state: PipelineState) -> dict[str, Any]:
    """
    Download video from URL for local processing.

    This node:
    1. Takes a video URL (TikTok, Instagram Reel, etc.)
    2. Downloads it to a local temporary file
    3. Returns the local path for subsequent processing

    Args:
        state: Current pipeline state with video_url

    Returns:
        Partial state update with video_path and progress
    """
    from api.video_downloader import download_video

    video_url = state.get("video_url", "")

    if not video_url:
        return mark_failed(state, "No video URL provided")

    logger.info(f"Downloading video from: {video_url}")

    try:
        # Update progress
        progress_update = update_progress(state, PipelineStep.DOWNLOADING_VIDEO, 1)

        # Download the video
        result = download_video(video_url)

        if not result.get("success"):
            error_msg = result.get("error", "Unknown download error")
            logger.error(f"Video download failed: {error_msg}")
            return {
                **progress_update,
                **mark_failed(state, f"Failed to download video: {error_msg}"),
            }

        video_path = result.get("path", "")

        if not video_path:
            return {
                **progress_update,
                **mark_failed(state, "Download succeeded but no path returned"),
            }

        logger.info(f"Video downloaded to: {video_path}")

        # Track temp file for cleanup
        temp_files = state.get("temp_files", [])
        temp_files.append(video_path)

        return {
            **progress_update,
            "video_path": video_path,
            "status": PipelineStatus.RUNNING.value,
            "temp_files": temp_files,
        }

    except ImportError:
        # video_downloader not available, check if video_path already exists
        # This allows using local files directly
        video_path = state.get("video_path", "")
        if video_path:
            logger.info(f"Using existing video path: {video_path}")
            return {
                **update_progress(state, PipelineStep.DOWNLOADING_VIDEO, 1),
                "status": PipelineStatus.RUNNING.value,
            }

        return mark_failed(
            state,
            "Video downloader not available and no local video path provided",
            {"hint": "Install yt-dlp or provide a local video_path"},
        )

    except Exception as e:
        logger.exception("Unexpected error downloading video")
        return mark_failed(
            state,
            f"Unexpected error downloading video: {str(e)}",
            {"exception_type": type(e).__name__},
        )


def download_video_node_async(state: PipelineState) -> dict[str, Any]:
    """
    Async version of download_video_node for use with async pipelines.

    This is a wrapper that can be used if the pipeline is run asynchronously.
    """
    # For now, delegate to sync version
    # Can be made truly async if needed
    return download_video_node(state)
