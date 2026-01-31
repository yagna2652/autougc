"""
Generate Video Node - Calls video generation APIs to create the final video.

This node takes the finalized prompt and calls video generation APIs
(Sora 2 or Kling via Fal.ai) to generate the actual video.

Supports both:
- Text-to-video: Generate video purely from prompt
- Image-to-video: Generate video using a starting frame/product image
"""

import logging
import os
import time
from typing import Any

from src.pipeline.state import (
    PipelineState,
    PipelineStatus,
    PipelineStep,
    mark_completed,
    mark_failed,
    update_progress,
)

logger = logging.getLogger(__name__)

# Model endpoints on Fal.ai
MODEL_ENDPOINTS = {
    # Text-to-video endpoints
    "sora2": "fal-ai/sora-2/text-to-video",
    "sora2pro": "fal-ai/sora-2/text-to-video/pro",
    "kling": "fal-ai/kling-video/v2.5-turbo/pro/text-to-video",
    # Image-to-video endpoints
    "sora2_i2v": "fal-ai/sora-2/image-to-video",
    "sora2pro_i2v": "fal-ai/sora-2/image-to-video/pro",
    "kling_i2v": "fal-ai/kling-video/v2.5-turbo/pro/image-to-video",
}


def generate_video_node(state: PipelineState) -> dict[str, Any]:
    """
    Generate video using Fal.ai API (Sora 2 or Kling).

    This node:
    1. Takes the final_prompt from previous nodes
    2. Optionally uses a starting frame for image-to-video
    3. Calls the appropriate video generation API
    4. Returns the generated video URL

    Args:
        state: Current pipeline state with final_prompt

    Returns:
        Partial state update with generated_video_url and completion status
    """
    final_prompt = state.get("final_prompt", "")

    if not final_prompt:
        return mark_failed(state, "No prompt available for video generation")

    logger.info("Starting video generation")

    try:
        # Update progress
        progress_update = update_progress(state, PipelineStep.GENERATING_VIDEO, 11)

        # Get config
        config = state.get("config", {})
        video_model = config.get("video_model", "sora2")
        video_duration = config.get("video_duration", 5)
        aspect_ratio = config.get("aspect_ratio", "9:16")
        use_image_to_video = config.get("use_image_to_video", True)

        # Check for FAL_KEY
        fal_key = os.getenv("FAL_KEY")
        if not fal_key:
            return {
                **progress_update,
                **mark_failed(
                    state,
                    "FAL_KEY not set",
                    {"hint": "Set FAL_KEY environment variable for video generation"},
                ),
            }

        # Determine if we should use image-to-video
        starting_frame_url = state.get("starting_frame_url", "")
        uploaded_image_url = state.get("uploaded_image_url", "")
        product_images = state.get("product_images", [])

        # Priority for image source: starting_frame > uploaded_image > first product image
        image_url = ""
        if use_image_to_video:
            if starting_frame_url:
                image_url = starting_frame_url
                logger.info("Using starting frame for image-to-video")
            elif uploaded_image_url:
                image_url = uploaded_image_url
                logger.info("Using uploaded image for image-to-video")
            elif product_images:
                # Need to upload product image first
                image_url = _upload_image_to_fal(product_images[0], fal_key)
                if image_url:
                    logger.info("Uploaded product image for image-to-video")

        # Select endpoint based on mode
        use_i2v = bool(image_url) and use_image_to_video
        endpoint = _select_endpoint(video_model, use_i2v)

        if not endpoint:
            return {
                **progress_update,
                **mark_failed(
                    state,
                    f"Unknown video model: {video_model}",
                    {"valid_models": list(MODEL_ENDPOINTS.keys())},
                ),
            }

        # Truncate prompt if too long
        max_prompt_length = 1500
        truncated_prompt = (
            final_prompt[:max_prompt_length] + "..."
            if len(final_prompt) > max_prompt_length
            else final_prompt
        )

        # Build API input
        api_input = _build_api_input(
            model=video_model,
            prompt=truncated_prompt,
            duration=video_duration,
            aspect_ratio=aspect_ratio,
            image_url=image_url if use_i2v else None,
        )

        # Call Fal.ai API
        result = _call_fal_api(endpoint, api_input, fal_key)

        if not result:
            return {
                **progress_update,
                **mark_failed(state, "Video generation API returned no result"),
            }

        video_url = result.get("video_url", "")

        if not video_url:
            return {
                **progress_update,
                **mark_failed(
                    state,
                    "Video generation completed but no video URL returned",
                    {"api_response": result},
                ),
            }

        logger.info(f"Video generated successfully: {video_url}")

        # Build video metadata
        video_metadata = {
            "model": video_model,
            "endpoint": endpoint,
            "duration": video_duration,
            "aspect_ratio": aspect_ratio,
            "mode": "image-to-video" if use_i2v else "text-to-video",
            "prompt_length": len(truncated_prompt),
            "used_starting_frame": bool(starting_frame_url),
            "used_product_image": bool(image_url) and not starting_frame_url,
        }

        # Mark pipeline as completed
        completion_update = mark_completed(state)

        return {
            **progress_update,
            **completion_update,
            "generated_video_url": video_url,
            "video_metadata": video_metadata,
        }

    except Exception as e:
        logger.exception("Unexpected error during video generation")
        return mark_failed(
            state,
            f"Video generation failed: {str(e)}",
            {"exception_type": type(e).__name__},
        )


def _select_endpoint(model: str, use_i2v: bool) -> str | None:
    """
    Select the appropriate Fal.ai endpoint.

    Args:
        model: Model name (sora2, sora2pro, kling)
        use_i2v: Whether to use image-to-video

    Returns:
        Endpoint string or None if invalid model
    """
    if use_i2v:
        endpoint_key = f"{model}_i2v"
    else:
        endpoint_key = model

    return MODEL_ENDPOINTS.get(endpoint_key)


def _build_api_input(
    model: str,
    prompt: str,
    duration: int,
    aspect_ratio: str,
    image_url: str | None,
) -> dict[str, Any]:
    """
    Build the API input for Fal.ai.

    Args:
        model: Model name
        prompt: Video generation prompt
        duration: Duration in seconds
        aspect_ratio: Aspect ratio (9:16, 16:9)
        image_url: Optional image URL for i2v mode

    Returns:
        API input dictionary
    """
    # Kling uses string duration, Sora uses integer
    if model == "kling":
        kling_duration = "5" if duration <= 5 else "10"
        api_input = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": kling_duration,
        }
    else:
        # Sora 2 / Sora 2 Pro
        sora_duration = 4 if duration <= 4 else (8 if duration <= 8 else 12)
        api_input = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": sora_duration,
        }

    # Add image URL if using image-to-video
    if image_url:
        api_input["image_url"] = image_url

    return api_input


def _call_fal_api(
    endpoint: str,
    api_input: dict[str, Any],
    fal_key: str,
) -> dict[str, Any] | None:
    """
    Call Fal.ai API for video generation.

    Args:
        endpoint: Fal.ai endpoint
        api_input: API input parameters
        fal_key: Fal.ai API key

    Returns:
        API result or None on failure
    """
    try:
        from fal_client import FalClient, submit

        # Configure client
        client = FalClient(key=fal_key)

        logger.info(f"Submitting to Fal.ai endpoint: {endpoint}")
        logger.debug(f"API input: {api_input}")

        # Submit and wait for result
        # Using subscribe for synchronous wait
        result = client.subscribe(
            endpoint,
            arguments=api_input,
            with_logs=False,
        )

        if result and hasattr(result, "video"):
            return {"video_url": result.video.url}
        elif result and isinstance(result, dict):
            video = result.get("video", {})
            if isinstance(video, dict):
                return {"video_url": video.get("url", "")}
            elif hasattr(video, "url"):
                return {"video_url": video.url}

        return result

    except ImportError:
        # Try alternative import
        try:
            import fal

            fal.config({"credentials": fal_key})

            logger.info(f"Submitting to Fal.ai endpoint: {endpoint}")

            result = fal.subscribe(
                endpoint,
                input=api_input,
                logs=False,
            )

            if result and result.data:
                data = result.data
                if hasattr(data, "video"):
                    return {"video_url": data.video.url}
                elif isinstance(data, dict) and "video" in data:
                    video = data["video"]
                    return {
                        "video_url": video.get("url", "")
                        if isinstance(video, dict)
                        else video.url
                    }

            return None

        except ImportError:
            logger.error("Neither fal_client nor fal package available")
            return None

    except Exception as e:
        logger.error(f"Fal.ai API error: {e}")
        return None


def _upload_image_to_fal(
    image_data: str,
    fal_key: str,
) -> str | None:
    """
    Upload an image to Fal.ai for use in image-to-video.

    Args:
        image_data: Base64-encoded image data
        fal_key: Fal.ai API key

    Returns:
        Uploaded image URL or None on failure
    """
    try:
        import base64
        import tempfile
        from pathlib import Path

        # If it's already a URL, return it
        if image_data.startswith("http"):
            return image_data

        # Extract base64 data
        if image_data.startswith("data:"):
            parts = image_data.split(";base64,")
            if len(parts) == 2:
                image_bytes = base64.b64decode(parts[1])
            else:
                return None
        else:
            image_bytes = base64.b64decode(image_data)

        # Save to temp file and upload
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        try:
            from fal_client import FalClient

            client = FalClient(key=fal_key)
            url = client.upload_file(tmp_path)
            return url

        except ImportError:
            try:
                import fal

                fal.config({"credentials": fal_key})
                url = fal.upload_file(tmp_path)
                return url

            except ImportError:
                logger.error("Cannot upload image: fal package not available")
                return None

        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

    except Exception as e:
        logger.error(f"Failed to upload image: {e}")
        return None
