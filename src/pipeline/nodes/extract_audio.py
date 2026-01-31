"""
Extract Audio Node - Extracts audio track from video for transcription.

This node uses the existing AudioExtractor to extract the audio track
from a downloaded video file for subsequent speech-to-text processing.
"""

import logging
from typing import Any

from src.pipeline.state import (
    PipelineState,
    PipelineStep,
    mark_failed,
    update_progress,
)

logger = logging.getLogger(__name__)


def extract_audio_node(state: PipelineState) -> dict[str, Any]:
    """
    Extract audio track from video file.

    This node:
    1. Takes a local video file path
    2. Extracts the audio track using ffmpeg
    3. Returns the path to the extracted audio file

    Args:
        state: Current pipeline state with video_path

    Returns:
        Partial state update with audio_path and progress
    """
    from src.analyzer.audio_extractor import AudioExtractor

    video_path = state.get("video_path", "")

    if not video_path:
        return mark_failed(state, "No video path available for audio extraction")

    logger.info(f"Extracting audio from: {video_path}")

    try:
        # Update progress
        progress_update = update_progress(state, PipelineStep.EXTRACTING_AUDIO, 2)

        # Initialize extractor
        extractor = AudioExtractor()

        # Extract audio
        audio_path = extractor.extract(video_path)

        if not audio_path:
            return {
                **progress_update,
                **mark_failed(state, "Audio extraction returned no path"),
            }

        logger.info(f"Audio extracted to: {audio_path}")

        # Track temp file for cleanup
        temp_files = state.get("temp_files", [])
        temp_files.append(audio_path)

        return {
            **progress_update,
            "audio_path": audio_path,
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
        logger.exception("Unexpected error extracting audio")
        return mark_failed(
            state,
            f"Failed to extract audio: {str(e)}",
            {"exception_type": type(e).__name__},
        )
