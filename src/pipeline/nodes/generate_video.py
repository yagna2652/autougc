"""
Generate Video Node - Calls I2V (image-to-video) APIs to create the final video.

Uses product images as the starting frame - the video model is conditioned
on the actual product image, not just a text description.

Requires product images - there is no T2V fallback.
"""

import logging
import os
import time
from typing import Any

from src.pipeline.utils import upload_image_to_fal
from src.tracing import is_tracing_enabled, trace_span

logger = logging.getLogger(__name__)

# Model endpoints on Fal.ai (Image-to-Video)
MODEL_ENDPOINTS = {
    "sora": "fal-ai/sora-2/image-to-video/pro",
    "kling": "fal-ai/kling-video/v2.1/pro/image-to-video",
}

# Approximate pricing per second (USD) for I2V
MODEL_PRICING_PER_SECOND = {
    "sora": 0.50,  # ~$0.50/second (verify actual I2V pricing)
    "kling": 0.12,  # ~$0.12/second (verify actual I2V pricing)
}


def generate_video_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Generate video using Fal.ai I2V API (Sora or Kling).

    Requires product_images - uploads the selected image to Fal CDN
    and uses it as the starting frame for video generation.

    Args:
        state: Pipeline state with 'video_prompt' and 'product_images'

    Returns:
        State update with 'generated_video_url', 'i2v_image_url', or 'error'
    """
    video_prompt = state.get("video_prompt", "")
    product_images = state.get("product_images", [])

    if not video_prompt:
        return {
            "error": "No video prompt available for generation",
            "current_step": "generation_failed",
        }

    # Product images are REQUIRED for I2V
    if not product_images:
        return {
            "error": "Product images required for video generation. I2V pipeline needs an image as starting frame.",
            "current_step": "generation_failed",
        }

    logger.info("Starting I2V video generation")

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
    i2v_image_index = config.get("i2v_image_index", 0)

    # Validate image index
    if i2v_image_index >= len(product_images):
        logger.warning(
            f"i2v_image_index {i2v_image_index} out of range, using index 0"
        )
        i2v_image_index = 0

    # Upload product image to Fal CDN
    selected_image = product_images[i2v_image_index]
    logger.info(f"Uploading product image {i2v_image_index} to Fal CDN")

    i2v_image_url = upload_image_to_fal(selected_image, fal_key)

    if not i2v_image_url:
        return {
            "error": "Failed to upload product image to Fal CDN. Cannot proceed with I2V generation.",
            "current_step": "generation_failed",
        }

    logger.info(f"Product image uploaded: {i2v_image_url}")

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
    logger.info(f"I2V image: {i2v_image_url}")
    logger.info(f"Prompt: {video_prompt[:100]}...")

    # Calculate estimated cost
    price_per_second = MODEL_PRICING_PER_SECOND.get(video_model, 0.50)
    estimated_cost_usd = price_per_second * video_duration

    # Trace the video generation
    with trace_span(
        name="generate_video",
        run_type="tool",
        inputs={
            "prompt": video_prompt[:200] + "..." if len(video_prompt) > 200 else video_prompt,
            "image_url": i2v_image_url,
            "model": video_model,
            "duration": video_duration,
            "aspect_ratio": aspect_ratio,
        },
        metadata={
            "video_model": video_model,
            "endpoint": endpoint,
            "mode": "i2v",
        },
    ) as span:
        start_time = time.time()

        try:
            # Call Fal.ai I2V API
            result = _call_fal_api(
                fal_key=fal_key,
                endpoint=endpoint,
                image_url=i2v_image_url,
                prompt=video_prompt,
                duration=video_duration,
                aspect_ratio=aspect_ratio,
            )
        except FalApiError as e:
            error_msg = f"Fal.ai API error: {str(e)}"
            logger.error(error_msg)
            span.set_error(error_msg)
            return {
                "error": error_msg,
                "current_step": "generation_failed",
                "i2v_image_url": i2v_image_url,
            }
        except Exception as e:
            error_msg = f"Video generation failed: {str(e)}"
            logger.exception(error_msg)
            span.set_error(error_msg)
            return {
                "error": error_msg,
                "current_step": "generation_failed",
                "i2v_image_url": i2v_image_url,
            }

        latency_ms = (time.time() - start_time) * 1000

        video_url = result.get("video", {}).get("url", "")

        if not video_url:
            error_msg = f"Video generation succeeded but no URL in response. Result: {result}"
            logger.error(error_msg)
            span.set_error(error_msg)
            return {
                "error": "Video generation succeeded but no URL returned",
                "current_step": "generation_failed",
                "i2v_image_url": i2v_image_url,
            }

        # Set trace outputs with cost
        span.set_outputs(
            outputs={
                "video_url": video_url,
                "i2v_image_url": i2v_image_url,
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
        "i2v_image_url": i2v_image_url,
        "current_step": "video_generated",
    }


class FalApiError(Exception):
    """Custom exception for Fal.ai API errors."""
    pass


def _call_fal_api(
    fal_key: str,
    endpoint: str,
    image_url: str,
    prompt: str,
    duration: int,
    aspect_ratio: str,
) -> dict[str, Any]:
    """
    Call Fal.ai I2V API to generate video from image.

    Args:
        fal_key: Fal.ai API key
        endpoint: API endpoint
        image_url: Fal CDN URL of the starting image
        prompt: Video generation prompt (motion description)
        duration: Video duration in seconds
        aspect_ratio: Aspect ratio (e.g., "9:16")

    Returns:
        API result

    Raises:
        FalApiError: If the API call fails
    """
    try:
        import fal_client
    except ImportError:
        raise FalApiError("fal_client not installed. Run: pip install fal-client")

    # Set the API key in environment (fal_client reads from FAL_KEY)
    os.environ["FAL_KEY"] = fal_key

    logger.info(f"Calling Fal.ai I2V: {endpoint}")

    # Build API input based on model (both use image_url for I2V)
    if "kling" in endpoint:
        api_input = {
            "prompt": prompt,
            "image_url": image_url,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio,
        }
    else:
        # Sora 2 I2V format
        api_input = {
            "prompt": prompt,
            "image_url": image_url,
            "duration": duration,  # Already validated/adjusted above
            "aspect_ratio": aspect_ratio,
        }

    logger.info(f"API input: {api_input}")

    # Call API and wait for result
    result = fal_client.subscribe(
        endpoint,
        arguments=api_input,
        with_logs=True,
    )

    if not result:
        raise FalApiError("Fal.ai returned empty result")

    return result
