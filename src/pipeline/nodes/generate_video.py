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

from src.pipeline.utils import (
    select_identity_references,
    upload_image_to_fal,
)
from src.pipeline.utils.prompt_safety import sanitize_video_prompt
from src.tracing import is_tracing_enabled, trace_span

logger = logging.getLogger(__name__)

# Model endpoints on Fal.ai (Image-to-Video)
MODEL_ENDPOINTS = {
    "sora": "fal-ai/sora-2/image-to-video/pro",
    "kling": "fal-ai/kling-video/v2.1/pro/image-to-video",
    "kling-v3": "fal-ai/kling-video/v3/pro/image-to-video",
}

# Approximate pricing per second (USD) for I2V
MODEL_PRICING_PER_SECOND = {
    "sora": 0.50,  # ~$0.50/second (verify actual I2V pricing)
    "kling": 0.12,  # ~$0.12/second (verify actual I2V pricing)
}


def _is_content_policy_violation(error_text: str) -> bool:
    """Detect provider moderation/content-check failures."""
    text = (error_text or "").lower()
    return "content_policy_violation" in text or "content checker" in text


def _build_safety_fallback_prompt(original_prompt: str) -> str:
    """
    Build a concise, low-risk fallback prompt that preserves core intent.
    """
    cleaned = sanitize_video_prompt(original_prompt, max_words=80)

    return (
        "Photoreal product demonstration video. "
        "A hand interacts with the product in a natural, neutral way. "
        "Show gentle press and release actions with smooth camera motion, "
        "stable framing, and realistic lighting. "
        "Keep focus on product details and consistent shape/materials. "
        f"{cleaned}"
    ).strip()


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

    logger.info("    ↳ Starting Image-to-Video generation")

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

    # Identity fidelity controls (fastest gains)
    use_tail_image = config.get("use_tail_image", False)
    use_identity_pack = config.get("use_identity_pack", False)
    segment_duration = config.get(
        "segment_duration", 2 if config.get("use_anchor_frames") else video_duration
    )
    use_anchor_frames = config.get("use_anchor_frames", False)

    # Use scene image (from Nano Banana Pro) if available, otherwise fall back to product image
    scene_image_url = state.get("scene_image_url", "")

    if scene_image_url:
        # Scene image already on fal CDN — use it directly
        i2v_image_url = scene_image_url
        logger.info(
            "    ↳ Using scene image as I2V starting frame (Nano Banana output)"
        )
        logger.info(f"    ↳ Scene image URL: {i2v_image_url[:60]}...")
    else:
        # Fallback: upload product image to Fal CDN
        logger.info("    ↳ No scene image available, falling back to product image")

        # Validate image index
        if i2v_image_index >= len(product_images):
            logger.warning(
                f"i2v_image_index {i2v_image_index} out of range, using index 0"
            )
            i2v_image_index = 0

        selected_image = product_images[i2v_image_index]
        logger.info(
            f"    ↳ Uploading product image {i2v_image_index + 1} to Fal CDN..."
        )

        i2v_image_url = upload_image_to_fal(selected_image, fal_key)

        if not i2v_image_url:
            return {
                "error": "Failed to upload product image to Fal CDN. Cannot proceed with I2V generation.",
                "current_step": "generation_failed",
            }

        logger.info(f"    ↳ Image uploaded successfully: {i2v_image_url[:60]}...")

    # Apply segment duration for anchor frame strategy
    if use_anchor_frames:
        video_duration = segment_duration
        logger.info(
            f"    ↳ Using anchor frame strategy with {video_duration}s segments"
        )

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

    # Prepare tail image for consistency (use same as start frame)
    tail_image_url = None
    if use_tail_image:
        tail_image_url = i2v_image_url
        logger.info("    ↳ Using tail_image_url for end-frame consistency")

    # Prepare identity pack images if enabled
    identity_images = None
    if use_identity_pack:
        identity_pack = state.get("product_identity_pack", {})
        if identity_pack:
            selected_sources, selection_reasons = select_identity_references(
                identity_pack=identity_pack,
                video_analysis=state.get("video_analysis", {}),
                scene_description=state.get("scene_description", ""),
            )
            identity_images = _normalize_identity_images(selected_sources, fal_key)
            if identity_images:
                logger.info(
                    f"    ↳ Using identity pack with {len(identity_images)} reference images"
                )
                if selection_reasons:
                    logger.info(
                        "    ↳ Selector reasons: "
                        + ", ".join(selection_reasons[: len(identity_images)])
                    )
            else:
                logger.warning(
                    "    ↳ Identity pack enabled, but no valid references after normalization"
                )

    # Sanitize prompt before first request to reduce moderation failures.
    safe_video_prompt = sanitize_video_prompt(video_prompt)
    if safe_video_prompt != video_prompt:
        logger.info("    ↳ Sanitized video prompt for policy safety")

    # Get endpoint
    endpoint = MODEL_ENDPOINTS.get(video_model, MODEL_ENDPOINTS["sora"])

    # Calculate estimated cost
    price_per_second = MODEL_PRICING_PER_SECOND.get(video_model, 0.50)
    estimated_cost_usd = price_per_second * video_duration

    logger.info(f"    ↳ Model: {video_model} ({endpoint})")
    logger.info(f"    ↳ Duration: {video_duration}s, Aspect ratio: {aspect_ratio}")
    logger.info(f"    ↳ Estimated cost: ${estimated_cost_usd:.2f}")

    # Trace the video generation
    with trace_span(
        name="generate_video",
        run_type="tool",
        inputs={
            "prompt": safe_video_prompt[:200] + "..."
            if len(safe_video_prompt) > 200
            else safe_video_prompt,
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
            # Call Fal.ai I2V API with identity fidelity controls
            result = _call_fal_api(
                fal_key=fal_key,
                endpoint=endpoint,
                image_url=i2v_image_url,
                prompt=safe_video_prompt,
                duration=video_duration,
                aspect_ratio=aspect_ratio,
                tail_image_url=tail_image_url,
                identity_images=identity_images,
            )
        except FalApiError as e:
            # One-shot moderation fallback for otherwise valid prompts.
            if _is_content_policy_violation(str(e)):
                fallback_prompt = _build_safety_fallback_prompt(safe_video_prompt)
                logger.warning(
                    "Fal content policy rejected prompt; retrying once with a safer fallback prompt"
                )
                try:
                    result = _call_fal_api(
                        fal_key=fal_key,
                        endpoint=endpoint,
                        image_url=i2v_image_url,
                        prompt=fallback_prompt,
                        duration=video_duration,
                        aspect_ratio=aspect_ratio,
                        tail_image_url=tail_image_url,
                        identity_images=identity_images,
                    )
                except Exception as retry_error:
                    error_msg = f"Fal.ai API error after moderation fallback: {str(retry_error)}"
                    logger.error(error_msg)
                    span.set_error(error_msg)
                    return {
                        "error": error_msg,
                        "current_step": "generation_failed",
                        "i2v_image_url": i2v_image_url,
                    }

            error_msg = f"Fal.ai API error: {str(e)}"
            if not _is_content_policy_violation(str(e)):
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
            error_msg = (
                f"Video generation succeeded but no URL in response. Result: {result}"
            )
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
    tail_image_url: str | None = None,
    identity_images: list[str] | None = None,
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
        tail_image_url: Optional end frame image for consistency
        identity_images: Optional list of reference images for identity pack

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

    logger.info(f"    ↳ Calling Fal.ai I2V: {endpoint}")
    logger.info(f"    ↳ This typically takes 2-5 minutes, please wait...")

    # Build API input based on model
    is_kling = "kling-video" in endpoint
    is_kling_v3 = "/v3/" in endpoint

    if "kling" in endpoint:
        if is_kling_v3:
            api_input = {
                "prompt": prompt,
                "start_image_url": image_url,
                "duration": str(duration),
                "aspect_ratio": aspect_ratio,
            }
            # Kling v3 expects end_image_url (not tail_image_url).
            if tail_image_url:
                api_input["end_image_url"] = tail_image_url
                logger.info("    ↳ Added end_image_url for Kling V3")

            # Kling v3 elements require an image set with frontal + reference images.
            if identity_images:
                # Keep payload small but valid. Provide 1 frontal + >=1 reference.
                frontal = identity_images[0]
                references = identity_images[1:2]
                if not references:
                    # Duplicate frontal so schema requirements are still met.
                    references = [frontal]

                api_input["elements"] = [
                    {
                        "frontal_image_url": frontal,
                        "reference_image_urls": references,
                    }
                ]
                logger.info(
                    "    ↳ Added Kling V3 identity element "
                    f"(frontal + {len(references)} reference image(s))"
                )
        else:
            api_input = {
                "prompt": prompt,
                "image_url": image_url,
                "duration": str(duration),
                "aspect_ratio": aspect_ratio,
            }
            # Add tail_image_url for end-frame consistency (Kling 2.1+)
            if tail_image_url and is_kling:
                api_input["tail_image_url"] = tail_image_url
                logger.info("    ↳ Added tail_image_url for Kling")
    else:
        # Sora 2 I2V format (limited options)
        api_input = {
            "prompt": prompt,
            "image_url": image_url,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        }

    logger.info(f"    ↳ API input: duration={duration}s, aspect_ratio={aspect_ratio}")
    logger.info(f"    ↳ Prompt preview: {prompt[:80]}...")

    # Track status changes to avoid duplicate logs
    last_status = [None]  # Use list to allow mutation in closure
    start_time = time.time()

    # Define a progress callback for fal_client
    def on_queue_update(update):
        elapsed = int(time.time() - start_time)

        if hasattr(update, "status"):
            status = update.status
            # Only log if status changed
            if status != last_status[0]:
                last_status[0] = status
                status_msg = {
                    "IN_QUEUE": "Queued, waiting for GPU...",
                    "IN_PROGRESS": "Generating video...",
                    "COMPLETED": "Video generation complete!",
                }.get(status, status)
                logger.info(f"    ↳ [{elapsed}s] Fal.ai: {status_msg}")

        if hasattr(update, "logs") and update.logs:
            for log in update.logs:
                if hasattr(log, "message"):
                    logger.info(f"    ↳ [{elapsed}s] {log.message}")

    # Call API and wait for result
    result = fal_client.subscribe(
        endpoint,
        arguments=api_input,
        with_logs=True,
        on_queue_update=on_queue_update,
    )

    if not result:
        raise FalApiError("Fal.ai returned empty result")

    return result


def _normalize_identity_images(
    image_sources: list[str],
    fal_key: str,
) -> list[str]:
    """
    Normalize identity references to hosted image URLs for API consumption.
    """
    normalized: list[str] = []

    for source in image_sources:
        if not source:
            continue

        # Already hosted on Fal CDN.
        if source.startswith("https://") and (
            "fal.media" in source or "fal.run" in source
        ):
            normalized.append(source)
            continue

        uploaded_url = upload_image_to_fal(source, fal_key)
        if uploaded_url:
            normalized.append(uploaded_url)
        else:
            logger.warning("    ↳ Failed to normalize identity reference; skipping")

    # Dedupe while preserving order.
    seen = set()
    unique_urls = []
    for url in normalized:
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    return unique_urls
