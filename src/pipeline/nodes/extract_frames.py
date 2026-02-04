"""
Extract Frames Node - Extracts key frames from video for visual analysis.

Simple node that extracts representative frames from a video file
for subsequent analysis with Claude Vision.
"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def extract_frames_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Extract key frames from video for visual analysis.

    Args:
        state: Pipeline state with 'video_path'

    Returns:
        State update with 'frames' list or 'error'
    """
    video_path = state.get("video_path", "")

    if not video_path:
        return {
            "error": "No video path available for frame extraction",
            "current_step": "extract_failed",
        }

    logger.info(f"Extracting frames from: {video_path}")

    try:
        from src.analyzer.frame_extractor import FrameExtractor

        # Get config
        config = state.get("config", {})
        num_frames = config.get("num_frames", 5)

        # Initialize extractor and extract frames
        extractor = FrameExtractor()
        frame_paths = extractor.extract(video_path, num_frames=num_frames)

        if not frame_paths:
            return {
                "error": "Frame extraction returned no frames",
                "current_step": "extract_failed",
            }

        # Convert to string paths
        frames = [str(p) for p in frame_paths]

        logger.info(f"Extracted {len(frames)} frames")

        return {
            "frames": frames,
            "current_step": "frames_extracted",
        }

    except FileNotFoundError as e:
        logger.error(f"Video file not found: {e}")
        return {
            "error": f"Video file not found: {video_path}",
            "current_step": "extract_failed",
        }

    except Exception as e:
        logger.exception("Unexpected error extracting frames")
        return {
            "error": f"Failed to extract frames: {str(e)}",
            "current_step": "extract_failed",
        }
