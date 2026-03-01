"""
Generate Video — Direct O3 reference-to-video endpoint.

Single endpoint: POST /generate → SSE stream of progress → video URL.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.pipeline.utils.fal_upload import upload_image_to_fal

logger = logging.getLogger(__name__)

router = APIRouter()

O3_ENDPOINT = "fal-ai/kling-video/o3/standard/reference-to-video"


# ---------- Request / Response models ----------


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Video prompt (use @Element1 to reference product)")
    start_image_url: str = Field(..., min_length=1, description="URL of the starting frame image")
    product_images: list[str] = Field(default_factory=list, description="Product reference images for identity element")
    duration: int = Field(default=5, ge=3, le=15, description="Video duration in seconds (3-15)")
    aspect_ratio: str = Field(default="9:16", description="Aspect ratio (e.g. 9:16, 16:9, 1:1)")
    cfg_scale: float = Field(default=0.5, ge=0.0, le=1.0, description="Classifier-free guidance scale")
    end_image_url: str | None = Field(default=None, description="Optional end frame (defaults to start_image)")
    negative_prompt: str = Field(default="blur, distort, and low quality", description="What to avoid in the video")
    product_video_url: str | None = Field(default=None, description="Motion reference video for the product element")


# ---------- Helpers ----------


def _upload_if_needed(url: str, fal_key: str) -> str:
    """Upload to Fal CDN if not already hosted there."""
    if "fal.media" in url or "fal.run" in url:
        return url
    uploaded = upload_image_to_fal(url, fal_key)
    if not uploaded:
        raise ValueError(f"Failed to upload image: {url[:80]}")
    return uploaded


def _build_elements(
    product_images: list[str],
    fal_key: str,
    video_url: str | None = None,
) -> list[dict[str, Any]] | None:
    """Build Fal elements payload from product images."""
    if not product_images:
        return None

    urls = []
    for img in product_images:
        uploaded = _upload_if_needed(img, fal_key)
        urls.append(uploaded)

    frontal = urls[0]
    references = urls[1:5] if len(urls) > 1 else [frontal]

    element: dict[str, Any] = {"frontal_image_url": frontal, "reference_image_urls": references}
    if video_url:
        element["video_url"] = video_url

    return [element]


def _call_fal_o3(
    fal_key: str,
    prompt: str,
    start_image_url: str,
    duration: int,
    aspect_ratio: str,
    cfg_scale: float,
    end_image_url: str | None,
    elements: list[dict[str, Any]] | None,
    negative_prompt: str | None = None,
) -> dict[str, Any]:
    """Call Fal O3 reference-to-video API (blocking)."""
    import fal_client

    os.environ["FAL_KEY"] = fal_key

    api_input: dict[str, Any] = {
        "prompt": prompt,
        "start_image_url": start_image_url,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "cfg_scale": cfg_scale,
        "generate_audio": False,
    }

    if end_image_url:
        api_input["end_image_url"] = end_image_url

    if negative_prompt:
        api_input["negative_prompt"] = negative_prompt

    if elements:
        api_input["elements"] = elements

    logger.info(f"Calling Fal O3: duration={duration}s, aspect={aspect_ratio}")
    logger.info(f"Prompt: {prompt[:100]}...")

    result = fal_client.subscribe(
        O3_ENDPOINT,
        arguments=api_input,
        with_logs=True,
    )

    if not result:
        raise RuntimeError("Fal returned empty result")

    return result


# ---------- SSE streaming ----------


async def _generate_stream(req: GenerateRequest):
    """Run generation in a thread and yield SSE events."""
    job_id = str(uuid.uuid4())[:8]

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    yield sse("job_start", {"job_id": job_id})

    fal_key = os.getenv("FAL_KEY")
    if not fal_key:
        yield sse("error", {"message": "FAL_KEY not set on server"})
        return

    # Upload start image
    yield sse("status", {"step": "uploading", "message": "Uploading images..."})
    try:
        start_url = await asyncio.to_thread(_upload_if_needed, req.start_image_url, fal_key)
        end_url = None
        if req.end_image_url:
            end_url = await asyncio.to_thread(_upload_if_needed, req.end_image_url, fal_key)
        else:
            end_url = start_url  # Loop anchor: end = start
        product_vid_url = None
        if req.product_video_url:
            product_vid_url = await asyncio.to_thread(_upload_if_needed, req.product_video_url, fal_key)
    except Exception as e:
        yield sse("error", {"message": f"Image upload failed: {e}"})
        return

    # Build elements
    elements = None
    if req.product_images:
        yield sse("status", {"step": "elements", "message": f"Preparing {len(req.product_images)} product reference(s)..."})
        try:
            elements = await asyncio.to_thread(
                _build_elements, req.product_images, fal_key, video_url=product_vid_url,
            )
        except Exception as e:
            yield sse("error", {"message": f"Element preparation failed: {e}"})
            return

    # Generate video
    yield sse("status", {"step": "generating", "message": "Generating video (2-5 min)..."})
    start_time = time.time()

    try:
        result = await asyncio.to_thread(
            _call_fal_o3,
            fal_key=fal_key,
            prompt=req.prompt,
            start_image_url=start_url,
            duration=req.duration,
            aspect_ratio=req.aspect_ratio,
            cfg_scale=req.cfg_scale,
            end_image_url=end_url,
            elements=elements,
            negative_prompt=req.negative_prompt,
        )
    except Exception as e:
        yield sse("error", {"message": f"Video generation failed: {e}"})
        return

    elapsed = round(time.time() - start_time, 1)
    video_url = result.get("video", {}).get("url", "")

    if not video_url:
        yield sse("error", {"message": "Generation succeeded but no video URL returned"})
        return

    yield sse("done", {
        "video_url": video_url,
        "elapsed_seconds": elapsed,
        "job_id": job_id,
    })


# ---------- Route ----------


@router.post("/generate")
async def generate_video(req: GenerateRequest):
    """Generate a video using O3 reference-to-video. Returns SSE stream."""
    return StreamingResponse(
        _generate_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
