"""
Extract Frames Node - Extracts key frames from video for visual analysis.

This node uses the existing FrameExtractor to extract representative
frames from a video file for subsequent visual analysis with Claude Vision.
"""

import base64
import logging
from pathlib import Path
from typing import Any

from src.pipeline.state import (
    PipelineState,
    PipelineStep,
    mark_failed,
    update_progress,
)

logger = logging.getLogger(__name__)


def extract_frames_node(state: PipelineState) -> dict[str, Any]:
    """
    Extract key frames from video for visual analysis.

    This node:
    1. Takes a local video file path
    2. Extracts N evenly-spaced frames
    3. Returns paths to frames and optionally base64-encoded versions

    Args:
        state: Current pipeline state with video_path

    Returns:
        Partial state update with frames, frames_base64, and progress
    """
    from src.analyzer.frame_extractor import FrameExtractor

    video_path = state.get("video_path", "")

    if not video_path:
        return mark_failed(state, "No video path available for frame extraction")

    logger.info(f"Extracting frames from: {video_path}")

    try:
        # Update progress
        progress_update = update_progress(state, PipelineStep.EXTRACTING_FRAMES, 4)

        # Get config
        config = state.get("config", {})
        num_frames = config.get("num_frames", 5)
        num_frames_for_scenes = config.get("num_frames_for_scenes", 20)
        enable_enhanced = config.get("enable_enhanced_analysis", True)

        # Use more frames if enhanced analysis is enabled
        frames_to_extract = num_frames_for_scenes if enable_enhanced else num_frames

        # Initialize extractor
        extractor = FrameExtractor()

        # Extract frames
        frame_paths = extractor.extract(video_path, num_frames=frames_to_extract)

        if not frame_paths:
            return {
                **progress_update,
                **mark_failed(state, "Frame extraction returned no frames"),
            }

        logger.info(f"Extracted {len(frame_paths)} frames")

        # Convert frames to base64 for API calls
        frames_base64 = []
        for frame_path in frame_paths:
            try:
                frame_b64 = _encode_frame_to_base64(frame_path)
                if frame_b64:
                    frames_base64.append(frame_b64)
            except Exception as e:
                logger.warning(f"Failed to encode frame {frame_path}: {e}")

        logger.info(f"Encoded {len(frames_base64)} frames to base64")

        # Track temp files for cleanup
        temp_files = state.get("temp_files", [])
        temp_files.extend(frame_paths)

        return {
            **progress_update,
            "frames": frame_paths,
            "frames_base64": frames_base64,
            "temp_files": temp_files,
        }

    except FileNotFoundError as e:
        logger.error(f"Video file not found: {e}")
        return mark_failed(
            state,
            f"Video file not found: {video_path}",
            {"exception": str(e)},
        )

    except Exception as e:
        logger.exception("Unexpected error extracting frames")
        return mark_failed(
            state,
            f"Failed to extract frames: {str(e)}",
            {"exception_type": type(e).__name__},
        )


def _encode_frame_to_base64(frame_path: str) -> str | None:
    """
    Encode a frame image to base64 for API calls.

    Args:
        frame_path: Path to the frame image file

    Returns:
        Base64-encoded string with data URL prefix, or None on failure
    """
    path = Path(frame_path)

    if not path.exists():
        logger.warning(f"Frame file does not exist: {frame_path}")
        return None

    # Determine media type from extension
    extension = path.suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    media_type = media_types.get(extension, "image/jpeg")

    try:
        with open(path, "rb") as f:
            image_data = f.read()

        b64_data = base64.b64encode(image_data).decode("utf-8")
        return f"data:{media_type};base64,{b64_data}"

    except Exception as e:
        logger.warning(f"Failed to read frame file {frame_path}: {e}")
        return None
