"""
Generate Scene Image Node - Creates a composited first frame using Nano Banana Pro.

I2V models use the provided image as frame 1 — the prompt only controls animation.
Feeding a product photo on white background when the prompt describes a person
holding the product doesn't work. This node generates a photorealistic scene
image (person holding product in setting) to use as the I2V starting frame.

Uses fal-ai/nano-banana-pro/edit to composite the product into the scene.
"""

import logging
import os
import time
from typing import Any

from src.pipeline.utils import upload_image_to_fal
from src.tracing import trace_span

logger = logging.getLogger(__name__)

NANO_BANANA_ENDPOINT = "fal-ai/nano-banana-pro/edit"


def generate_scene_image_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a scene image compositing the product into a TikTok-style setting.

    Uses Nano Banana Pro to create a photorealistic first frame showing
    a person holding/interacting with the product in the analyzed scene.

    Args:
        state: Pipeline state with 'scene_description', 'product_images',
               and 'video_analysis'

    Returns:
        State update with 'scene_image_url' or 'error'
    """
    scene_description = state.get("scene_description", "")
    product_images = state.get("product_images", [])

    # Scene description is required — it comes from generate_prompt
    if not scene_description:
        logger.warning("No scene description available, skipping scene image generation")
        return {"current_step": "scene_image_skipped"}

    if not product_images:
        logger.warning("No product images available, skipping scene image generation")
        return {"current_step": "scene_image_skipped"}

    # Check for FAL_KEY
    fal_key = os.getenv("FAL_KEY")
    if not fal_key:
        return {
            "error": "FAL_KEY not set — cannot generate scene image",
            "current_step": "scene_image_failed",
        }

    logger.info("    ↳ Starting scene image generation (Nano Banana Pro)")
    logger.info(f"    ↳ Scene prompt: {scene_description[:120]}...")

    # Upload product image to fal CDN
    product_image = product_images[0]
    logger.info("    ↳ Uploading product image to Fal CDN...")
    product_image_url = upload_image_to_fal(product_image, fal_key)

    if not product_image_url:
        logger.warning("Failed to upload product image, skipping scene generation")
        return {"current_step": "scene_image_skipped"}

    logger.info(f"    ↳ Product image uploaded: {product_image_url[:60]}...")

    # Call Nano Banana Pro
    with trace_span(
        name="generate_scene_image",
        run_type="tool",
        inputs={
            "prompt": scene_description,
            "product_image_url": product_image_url,
            "endpoint": NANO_BANANA_ENDPOINT,
        },
    ) as span:
        start_time = time.time()

        try:
            result = _call_nano_banana(
                fal_key=fal_key,
                product_image_url=product_image_url,
                prompt=scene_description,
            )
        except Exception as e:
            error_msg = f"Scene image generation failed: {e}"
            logger.error(f"    ↳ {error_msg}")
            span.set_error(error_msg)
            # Non-fatal — pipeline can fall back to product image in generate_video
            return {"current_step": "scene_image_failed"}

        latency_ms = (time.time() - start_time) * 1000

        # fal.ai image models return {"images": [{"url": "..."}]}
        images = result.get("images", [])
        scene_image_url = images[0].get("url") if images else None

        if not scene_image_url:
            error_msg = f"Nano Banana returned no image. Result keys: {list(result.keys())}"
            logger.error(f"    ↳ {error_msg}")
            span.set_error(error_msg)
            return {"current_step": "scene_image_failed"}

        span.set_outputs(
            outputs={
                "scene_image_url": scene_image_url,
                "latency_ms": latency_ms,
            },
        )

        logger.info(f"    ↳ Scene image generated in {latency_ms/1000:.1f}s")
        logger.info(f"    ↳ Scene image URL: {scene_image_url}")

    return {
        "scene_image_url": scene_image_url,
        "current_step": "scene_image_generated",
    }


def _call_nano_banana(
    fal_key: str,
    product_image_url: str,
    prompt: str,
) -> dict[str, Any]:
    """
    Call Nano Banana Pro /edit endpoint via fal_client.

    Args:
        fal_key: Fal.ai API key
        product_image_url: Fal CDN URL of the product image
        prompt: Scene description prompt

    Returns:
        API result dict

    Raises:
        Exception: If the API call fails
    """
    import fal_client

    os.environ["FAL_KEY"] = fal_key

    logger.info(f"    ↳ Calling Nano Banana Pro: {NANO_BANANA_ENDPOINT}")

    start_time = time.time()
    last_status = [None]

    def on_queue_update(update):
        elapsed = int(time.time() - start_time)
        if hasattr(update, "status"):
            status = update.status
            if status != last_status[0]:
                last_status[0] = status
                status_msg = {
                    "IN_QUEUE": "Queued, waiting for GPU...",
                    "IN_PROGRESS": "Generating scene image...",
                    "COMPLETED": "Scene image complete!",
                }.get(status, status)
                logger.info(f"    ↳ [{elapsed}s] Nano Banana: {status_msg}")

    result = fal_client.subscribe(
        NANO_BANANA_ENDPOINT,
        arguments={
            "image_urls": [product_image_url],
            "prompt": prompt,
            "aspect_ratio": "9:16",
            "output_format": "png",
        },
        with_logs=True,
        on_queue_update=on_queue_update,
    )

    if not result:
        raise RuntimeError("Nano Banana Pro returned empty result")

    return result
