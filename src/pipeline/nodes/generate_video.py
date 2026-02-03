"""
Generate Video Node - Calls video generation APIs to create the final video.

Simple node that takes a video prompt and generates a video using Fal.ai
(Sora or Kling models).
"""

import logging
import os
import time
from typing import Any

from src.tracing import is_tracing_enabled, trace_span

logger = logging.getLogger(__name__)

# Model endpoints on Fal.ai
MODEL_ENDPOINTS = {
    "sora": "fal-ai/sora-2/text-to-video",
    "kling": "fal-ai/kling-video/v2.5-turbo/pro/text-to-video",
}

# Approximate pricing per second (USD)
MODEL_PRICING_PER_SECOND = {
    "sora": 0.50,  # ~$0.50/second
    "kling": 0.10,  # ~$0.10/second
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
    video_model = config.get("video_model", "sora")
    video_duration = config.get("video_duration", 5)
    aspect_ratio = config.get("aspect_ratio", "9:16")

    # Sora 2 only supports 4, 8, or 12 second durations
    if "sora" in video_model:
        valid_sora_durations = [4, 8, 12]
        if video_duration not in valid_sora_durations:
            # Map to nearest valid duration
            video_duration = min(
                valid_sora_durations, key=lambda x: abs(x - video_duration)
            )
            logger.info(
                f"Adjusted duration to {video_duration}s for Sora 2 (valid: 4, 8, 12)"
            )

    # Get endpoint
    endpoint = MODEL_ENDPOINTS.get(video_model, MODEL_ENDPOINTS["sora"])

    logger.info(f"Using model: {video_model} ({endpoint})")
    logger.info(f"Prompt: {video_prompt[:100]}...")

    try:
        # Calculate estimated cost
        price_per_second = MODEL_PRICING_PER_SECOND.get(video_model, 0.50)
        estimated_cost_usd = price_per_second * video_duration

        # Trace the video generation
        with trace_span(
            name="generate_video",
            run_type="tool",
            inputs={
                "prompt": video_prompt[:200] + "..." if len(video_prompt) > 200 else video_prompt,
                "model": video_model,
                "duration": video_duration,
                "aspect_ratio": aspect_ratio,
            },
            metadata={
                "video_model": video_model,
                "endpoint": endpoint,
            },
        ) as span:
            start_time = time.time()

            # Call Fal.ai API
            result = _call_fal_api(
                fal_key=fal_key,
                endpoint=endpoint,
                prompt=video_prompt,
                duration=video_duration,
                aspect_ratio=aspect_ratio,
            )

            latency_ms = (time.time() - start_time) * 1000

            if not result:
                span.set_error("Video generation failed - no result returned")
                return {
                    "error": "Video generation failed - no result returned",
                    "current_step": "generation_failed",
                }

            video_url = result.get("video", {}).get("url", "")

            if not video_url:
                span.set_error("Video generation succeeded but no URL returned")
                return {
                    "error": "Video generation succeeded but no URL returned",
                    "current_step": "generation_failed",
                }

            # Set trace outputs with cost
            span.set_outputs(
                outputs={
                    "video_url": video_url,
                    "duration_seconds": video_duration,
                    "latency_ms": latency_ms,
                },
                metadata={
                    "cost_usd": estimated_cost_usd,
                    "price_per_second": price_per_second,
                },
            )

            logger.info(f"Video generated: {video_url} (cost: ${estimated_cost_usd:.2f})")

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
        import fal_client

        # Set the API key in environment (fal_client reads from FAL_KEY)
        os.environ["FAL_KEY"] = fal_key

        logger.info(f"Calling Fal.ai: {endpoint}")

        # Build API input based on model
        if "kling" in endpoint:
            api_input = {
                "prompt": prompt,
                "duration": str(duration),
                "aspect_ratio": aspect_ratio,
            }
        else:
            # Sora 2 format - duration must be 4, 8, or 12
            api_input = {
                "prompt": prompt,
                "duration": duration,  # Already validated/adjusted above
                "aspect_ratio": aspect_ratio,
            }

        # Call API and wait for result
        result = fal_client.subscribe(
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
