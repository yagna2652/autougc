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
from pydantic import BaseModel, Field, model_validator

from src.pipeline.utils.fal_upload import upload_image_to_fal

logger = logging.getLogger(__name__)

router = APIRouter()

O3_ENDPOINT = "fal-ai/kling-video/o3/standard/reference-to-video"


# ---------- Request / Response models ----------


class ShotPrompt(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=512)
    duration: int = Field(default=5, ge=3, le=15)


class GenerateRequest(BaseModel):
    prompt: str = Field(default="", description="Single-shot prompt (use @Element1 to reference product)")
    multi_prompt: list[ShotPrompt] | None = Field(default=None, description="Multi-shot prompts (mutually exclusive with prompt)")
    shot_type: str = Field(default="customize", description="Shot type when using multi_prompt")
    start_image_url: str = Field(..., min_length=1, description="URL of the starting frame image")
    product_images: list[str] = Field(default_factory=list, description="Product reference images for identity element")
    duration: int = Field(default=5, ge=3, le=15, description="Video duration in seconds (3-15)")
    aspect_ratio: str = Field(default="9:16", description="Aspect ratio (e.g. 9:16, 16:9, 1:1)")
    cfg_scale: float = Field(default=0.5, ge=0.0, le=1.0, description="Classifier-free guidance scale")
    end_image_url: str | None = Field(default=None, description="Optional end frame (defaults to start_image)")
    negative_prompt: str = Field(default="blur, distort, and low quality", description="What to avoid in the video")
    product_video_url: str | None = Field(default=None, description="Motion reference video for the product element")

    @model_validator(mode="after")
    def check_prompt_or_multi_prompt(self):
        has_prompt = bool(self.prompt and self.prompt.strip())
        has_multi = bool(self.multi_prompt and len(self.multi_prompt) > 0)
        if not has_prompt and not has_multi:
            raise ValueError("Either prompt or multi_prompt must be provided")
        if has_prompt and has_multi:
            raise ValueError("prompt and multi_prompt are mutually exclusive")
        return self


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
    references = urls[1:4] if len(urls) > 1 else [frontal]

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
    multi_prompt: list[dict[str, Any]] | None = None,
    shot_type: str = "customize",
) -> dict[str, Any]:
    """Call Fal O3 reference-to-video API (blocking)."""
    import fal_client

    os.environ["FAL_KEY"] = fal_key

    api_input: dict[str, Any] = {
        "start_image_url": start_image_url,
        "aspect_ratio": aspect_ratio,
        "cfg_scale": cfg_scale,
        "generate_audio": False,
    }

    if multi_prompt:
        api_input["multi_prompt"] = multi_prompt
        api_input["shot_type"] = shot_type
    else:
        api_input["prompt"] = prompt
        api_input["duration"] = duration

    if end_image_url and not multi_prompt:
        api_input["end_image_url"] = end_image_url

    if negative_prompt:
        api_input["negative_prompt"] = negative_prompt

    if elements:
        api_input["elements"] = elements

    if multi_prompt:
        total_dur = sum(int(s["duration"]) for s in multi_prompt)
        logger.info(f"Calling Fal O3 multi-shot: {len(multi_prompt)} shots, {total_dur}s total, aspect={aspect_ratio}")
    else:
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
    trace_id = None
    prompt_version_id = None

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    # Auto-save prompt version + create trace
    from api.routes.prompts import store as prompt_store

    def fail_trace(msg: str):
        if prompt_store and trace_id:
            try:
                prompt_store.update_trace(trace_id, status="error", error_message=msg)
            except Exception:
                pass

    # Build stored prompt text + model_config for versioning
    if req.multi_prompt:
        stored_prompt = "\n---\n".join(s.prompt for s in req.multi_prompt)
        model_config = {
            "aspect_ratio": req.aspect_ratio,
            "cfg_scale": req.cfg_scale,
            "multi_prompt": [{"prompt": s.prompt, "duration": s.duration} for s in req.multi_prompt],
            "shot_type": req.shot_type,
        }
    else:
        stored_prompt = req.prompt
        model_config = {"duration": req.duration, "aspect_ratio": req.aspect_ratio, "cfg_scale": req.cfg_scale}

    if prompt_store:
        try:
            version = prompt_store.save_version(
                prompt=stored_prompt,
                negative_prompt=req.negative_prompt or "",
                model_config=model_config,
            )
            prompt_version_id = version["id"]
            trace_id = prompt_store.save_trace(
                prompt_version_id=prompt_version_id,
                job_id=job_id,
                start_image_url=req.start_image_url,
                end_image_url=req.end_image_url,
                product_images=req.product_images or None,
                product_video_url=req.product_video_url,
                status="pending",
            )
        except Exception as e:
            logger.warning(f"Failed to save prompt version/trace: {e}")

    yield sse("job_start", {
        "job_id": job_id,
        "prompt_version_id": prompt_version_id,
        "trace_id": trace_id,
    })

    fal_key = os.getenv("FAL_KEY")
    if not fal_key:
        yield sse("error", {"message": "FAL_KEY not set on server"})
        return

    # Upload start image
    yield sse("status", {"step": "uploading", "message": "Uploading images..."})
    try:
        # Upload independent assets in parallel
        uploads = [asyncio.to_thread(_upload_if_needed, req.start_image_url, fal_key)]
        need_end = not req.multi_prompt and req.end_image_url
        if need_end:
            uploads.append(asyncio.to_thread(_upload_if_needed, req.end_image_url, fal_key))
        if req.product_video_url:
            uploads.append(asyncio.to_thread(_upload_if_needed, req.product_video_url, fal_key))

        results = await asyncio.gather(*uploads)
        idx = 0
        start_url = results[idx]; idx += 1
        end_url = results[idx] if need_end else (None if req.multi_prompt else start_url)
        if need_end:
            idx += 1
        product_vid_url = results[idx] if req.product_video_url else None
    except Exception as e:
        fail_trace(f"Image upload failed: {e}")
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
            fail_trace(f"Element preparation failed: {e}")
            yield sse("error", {"message": f"Element preparation failed: {e}"})
            return

    # Generate video
    yield sse("status", {"step": "generating", "message": "Generating video (2-5 min)..."})
    start_time = time.time()

    try:
        multi_prompt_dicts = (
            [{"prompt": s.prompt, "duration": str(s.duration)} for s in req.multi_prompt]
            if req.multi_prompt
            else None
        )
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
            multi_prompt=multi_prompt_dicts,
            shot_type=req.shot_type,
        )
    except Exception as e:
        fail_trace(str(e))
        yield sse("error", {"message": f"Video generation failed: {e}"})
        return

    elapsed = round(time.time() - start_time, 1)
    video_url = result.get("video", {}).get("url", "")

    if not video_url:
        fail_trace("No video URL returned")
        yield sse("error", {"message": "Generation succeeded but no video URL returned"})
        return

    if prompt_store and trace_id:
        try:
            prompt_store.update_trace(trace_id, video_url=video_url, elapsed_seconds=elapsed, status="success")
        except Exception:
            pass

    yield sse("done", {
        "video_url": video_url,
        "elapsed_seconds": elapsed,
        "job_id": job_id,
        "prompt_version_id": prompt_version_id,
        "trace_id": trace_id,
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
