"""
Download Video Node - Downloads TikTok/Reel videos for analysis.

Simple node that downloads a video from a URL for local processing.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def download_video_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Download video from URL for local processing.

    Args:
        state: Pipeline state with 'video_url'

    Returns:
        State update with 'video_path' or 'error'
    """
    video_url = state.get("video_url", "")

    if not video_url:
        return {
            "error": "No video URL provided",
            "current_step": "download_failed",
        }

    logger.info(f"Downloading video from: {video_url}")

    try:
        from api.video_downloader import download_video

        result = download_video(video_url)

        if not result.get("success"):
            error_msg = result.get("error", "Unknown download error")
            logger.error(f"Video download failed: {error_msg}")
            return {
                "error": f"Failed to download video: {error_msg}",
                "current_step": "download_failed",
            }

        video_path = result.get("path", "")

        if not video_path:
            return {
                "error": "Download succeeded but no path returned",
                "current_step": "download_failed",
            }

        logger.info(f"Video downloaded to: {video_path}")

        return {
            "video_path": video_path,
            "current_step": "video_downloaded",
        }

    except ImportError:
        # video_downloader not available, check if video_path already exists
        video_path = state.get("video_path", "")
        if video_path:
            logger.info(f"Using existing video path: {video_path}")
            return {
                "current_step": "video_downloaded",
            }

        return {
            "error": "Video downloader not available and no local video path provided",
            "current_step": "download_failed",
        }

    except Exception as e:
        logger.exception("Unexpected error downloading video")
        return {
            "error": f"Unexpected error: {str(e)}",
            "current_step": "download_failed",
        }
