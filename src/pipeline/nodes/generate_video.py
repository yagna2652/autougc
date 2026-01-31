"""
Generate Video Node - Calls video generation APIs to create the final video.

Simple node that takes a video prompt and generates a video using Fal.ai
(Sora or Kling models).
"""

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Model endpoints on Fal.ai
MODEL_ENDPOINTS = {
    "sora": "fal-ai/sora-2/text-to-video",
    "kling": "fal-ai/kling-video/v2.5-turbo/pro/text-to-video",
}


def generate_video_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Generate video using Fal.ai API (Sora or Kling).

    Args:
        state: Pipeline state with 'video_prompt'

    Returns:
        State update with 'generated_video_url' or 'error'
    """
    video_prompt = state.get("video_prompt", "")

    if not video_prompt:
        return {
            "error": "No video prompt available for generation",
            "current_step": "generation_failed",
        }

    logger.info("Starting video generation")

    # Check for FAL_KEY
    fal_key = os.getenv("FAL_KEY")
    if not fal_key:
        return {
            "error": "FAL_KEY not set - cannot generate video",
            "current_step": "generation_failed",
        }

    # Get config
    config = state.get("config", {})
    video_model = config.get("video_model", "kling")
    video_duration = config.get("video_duration", 5)
    aspect_ratio = config.get("aspect_ratio", "9:16")

    # Get endpoint
    endpoint = MODEL_ENDPOINTS.get(video_model, MODEL_ENDPOINTS["kling"])

    logger.info(f"Using model: {video_model} ({endpoint})")
    logger.info(f"Prompt: {video_prompt[:100]}...")

    try:
        # Call Fal.ai API
        result = _call_fal_api(
            fal_key=fal_key,
            endpoint=endpoint,
            prompt=video_prompt,
            duration=video_duration,
            aspect_ratio=aspect_ratio,
        )

        if not result:
            return {
                "error": "Video generation failed - no result returned",
                "current_step": "generation_failed",
            }

        video_url = result.get("video", {}).get("url", "")

        if not video_url:
            return {
                "error": "Video generation succeeded but no URL returned",
                "current_step": "generation_failed",
            }

        logger.info(f"Video generated: {video_url}")

        return {
            "generated_video_url": video_url,
            "current_step": "video_generated",
        }

    except Exception as e:
        logger.exception("Error generating video")
        return {
            "error": f"Video generation failed: {str(e)}",
            "current_step": "generation_failed",
        }


def _call_fal_api(
    fal_key: str,
    endpoint: str,
    prompt: str,
    duration: int,
    aspect_ratio: str,
) -> dict[str, Any] | None:
    """
    Call Fal.ai API to generate video.

    Args:
        fal_key: Fal.ai API key
        endpoint: API endpoint
        prompt: Video generation prompt
        duration: Video duration in seconds
        aspect_ratio: Aspect ratio (e.g., "9:16")

    Returns:
        API result or None on failure
    """
    try:
        from fal_client import FalClient

        # Configure client
        client = FalClient(key=fal_key)

        logger.info(f"Calling Fal.ai: {endpoint}")

        # Build API input based on model
        if "kling" in endpoint:
            api_input = {
                "prompt": prompt,
                "duration": str(duration),
                "aspect_ratio": aspect_ratio,
            }
        else:
            # Sora format
            api_input = {
                "prompt": prompt,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
            }

        # Call API and wait for result
        result = client.subscribe(
            endpoint,
            arguments=api_input,
            with_logs=True,
        )

        return result

    except ImportError:
        logger.error("fal_client not installed. Run: pip install fal-client")
        return None
    except Exception as e:
        logger.error(f"Fal.ai API error: {e}")
        return None
