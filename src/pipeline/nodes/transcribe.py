"""
Transcribe Node - Converts audio to text with timestamps.

This node uses the existing Transcriber (Whisper) to convert
extracted audio into a transcript with word-level timestamps.
"""

import logging
from typing import Any

from src.pipeline.state import (
    PipelineState,
    PipelineStep,
    Transcript,
    mark_failed,
    update_progress,
)

logger = logging.getLogger(__name__)


def transcribe_node(state: PipelineState) -> dict[str, Any]:
    """
    Transcribe audio to text with timestamps.

    This node:
    1. Takes an extracted audio file path
    2. Runs speech-to-text (Whisper local or API)
    3. Returns transcript with segments and timestamps

    Args:
        state: Current pipeline state with audio_path

    Returns:
        Partial state update with transcript and progress
    """
    from src.analyzer.transcriber import Transcriber

    audio_path = state.get("audio_path", "")

    if not audio_path:
        return mark_failed(state, "No audio path available for transcription")

    logger.info(f"Transcribing audio from: {audio_path}")

    try:
        # Update progress
        progress_update = update_progress(state, PipelineStep.TRANSCRIBING, 3)

        # Get config
        config = state.get("config", {})
        whisper_mode = config.get("whisper_mode", "local")
        whisper_model = config.get("whisper_model", "base")

        # Initialize transcriber
        transcriber = Transcriber(
            mode=whisper_mode,
            model=whisper_model,
        )

        # Transcribe audio
        transcript_result = transcriber.transcribe(audio_path)

        if not transcript_result:
            return {
                **progress_update,
                **mark_failed(state, "Transcription returned no result"),
            }

        # Convert to our Transcript TypedDict format
        transcript: Transcript = {
            "full_text": transcript_result.full_text,
            "segments": [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                }
                for seg in transcript_result.segments
            ],
            "language": transcript_result.language,
        }

        logger.info(
            f"Transcription complete: {len(transcript['segments'])} segments, "
            f"language: {transcript.get('language', 'unknown')}"
        )

        return {
            **progress_update,
            "transcript": transcript,
        }

    except FileNotFoundError as e:
        logger.error(f"Audio file not found: {e}")
        return mark_failed(
            state,
            f"Audio file not found: {audio_path}",
            {"exception": str(e)},
        )

    except Exception as e:
        logger.exception("Unexpected error during transcription")
        return mark_failed(
            state,
            f"Failed to transcribe audio: {str(e)}",
            {"exception_type": type(e).__name__},
        )
