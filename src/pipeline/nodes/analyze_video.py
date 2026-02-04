"""
Analyze Video Node - Simple Claude Vision analysis of TikTok video frames.

This node takes extracted frames from a TikTok video and uses Claude Vision
to understand the video's style, content, and approach for recreation.

All LLM calls are traced via LangSmith for full observability.
"""

import logging
from typing import Any

import anthropic

from src.pipeline.utils import (
    encode_image_file,
    get_anthropic_client,
    get_anthropic_client_with_timeout,
    handle_api_error,
    handle_unexpected_error,
    parse_json_response,
)

logger = logging.getLogger(__name__)

# Default output fields for error handling
_ERROR_DEFAULTS = {"video_analysis": {}}


def analyze_video_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Analyze video frames using Claude Vision.

    Takes extracted frames and sends them to Claude Vision for analysis.
    Returns a simple, structured understanding of the video.

    Args:
        state: Pipeline state with 'frames' (list of frame paths)

    Returns:
        State update with 'video_analysis' dict
    """
    frames = state.get("frames", [])

    if not frames:
        logger.warning("No frames provided for analysis")
        return {
            "video_analysis": {},
            "error": "No frames to analyze",
        }

    logger.info(f"Analyzing {len(frames)} frames with Claude Vision")

    # Get Anthropic client
    client, model, error = get_anthropic_client(state, trace_name="analyze_video")
    if error:
        return {
            "video_analysis": {},
            "error": error,
        }

    try:
        # Build the message content with frames
        logger.info("Building analysis content from frames...")
        content = _build_analysis_content(frames)

        if not content:
            logger.error("Failed to build content - no valid frames")
            return {
                "video_analysis": {},
                "error": "Failed to encode any frames for analysis",
                "current_step": "analysis_failed",
            }

        logger.info(
            f"Content built with {len(content)} items, calling Claude Vision..."
        )

        # Call Claude Vision with timeout
        api_client = get_anthropic_client_with_timeout(
            timeout_seconds=120.0, connect_timeout=30.0
        )
        if not api_client:
            return {
                "video_analysis": {},
                "error": "ANTHROPIC_API_KEY not set",
            }

        response = api_client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": content}],
        )

        logger.info("Claude Vision response received")

        # Parse response
        response_text = response.content[0].text
        analysis = parse_json_response(response_text, context="video analysis")

        if not analysis:
            logger.warning("Could not parse video analysis response")
            return {
                "video_analysis": {"raw_response": response_text},
                "current_step": "video_analyzed",
            }

        logger.info(
            f"Video analysis complete: {analysis.get('style', 'unknown')} style"
        )

        return {
            "video_analysis": analysis,
            "current_step": "video_analyzed",
        }

    except anthropic.APIError as e:
        return handle_api_error(e, _ERROR_DEFAULTS, context="video analysis")
    except Exception as e:
        return handle_unexpected_error(e, _ERROR_DEFAULTS, context="video analysis")


def _build_analysis_content(frames: list[str]) -> list[dict[str, Any]]:
    """
    Build the content array for Claude Vision API.

    Args:
        frames: List of frame file paths

    Returns:
        Content array for Claude API
    """
    content = []

    # Add the analysis prompt
    prompt = """Analyze these frames from a TikTok video. I want to understand how to recreate a similar style video.

For each aspect, be SPECIFIC and DETAILED - I'll use this to generate a new video.

Analyze:

1. **SETTING & ENVIRONMENT**
   - Where is this filmed? (bedroom, bathroom, kitchen, outdoors, car, etc.)
   - What's in the background?
   - Is it messy/lived-in or clean/minimal?

2. **LIGHTING**
   - Natural or artificial?
   - Soft or harsh?
   - Direction (front-lit, backlit, side-lit)?
   - Time of day feel?

3. **CAMERA & FRAMING**
   - Distance from subject (close-up, medium, full body)?
   - Angle (eye-level, slightly above, below)?
   - Handheld or stable?
   - Portrait (9:16) orientation?

4. **PERSON (if present)**
   - Approximate age range
   - Gender presentation
   - What are they wearing?
   - Hair style/color
   - Makeup (if any)
   - Overall vibe (casual, polished, energetic, calm)

5. **ACTIONS & MOVEMENT**
   - What is the person doing?
   - Hand gestures?
   - Facial expressions?
   - Any product interaction?

6. **STYLE & MOOD**
   - Overall aesthetic (authentic/raw, polished, funny, serious, educational)
   - Energy level (high, medium, low)
   - Does it feel like a real person or staged?

7. **TEXT & GRAPHICS**
   - Any on-screen text?
   - Captions style?
   - Stickers or effects?

Respond in this JSON format:
{
    "setting": "specific description of where this is filmed",
    "lighting": "description of lighting setup",
    "camera": {
        "framing": "close-up/medium/full body",
        "angle": "eye-level/above/below",
        "movement": "handheld/stable/slight movement"
    },
    "person": {
        "age_range": "e.g., 20-25",
        "gender": "description",
        "appearance": "clothing, hair, makeup description",
        "vibe": "casual/polished/energetic/etc"
    },
    "actions": "what the person is doing in the video",
    "style": "overall video style/aesthetic",
    "energy": "high/medium/low",
    "mood": "the emotional tone",
    "text_overlays": "description of any text on screen",
    "what_makes_it_work": "why this video style is effective for UGC"
}

Return ONLY valid JSON."""

    content.append({"type": "text", "text": prompt})

    # Add frames (limit to 5 for cost efficiency)
    frames_to_analyze = frames[:5] if len(frames) > 5 else frames

    for i, frame_path in enumerate(frames_to_analyze):
        # Add frame label
        content.append(
            {
                "type": "text",
                "text": f"\n--- Frame {i + 1} of {len(frames_to_analyze)} ---",
            }
        )

        # Add the image
        logger.debug(f"Encoding frame: {frame_path}")
        image_data, media_type = encode_image_file(frame_path)
        if image_data:
            logger.debug(f"Frame encoded successfully: {len(image_data)} bytes")
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                }
            )
        else:
            logger.warning(f"Failed to encode frame: {frame_path}")

    # Check if we got at least one image
    has_images = any(item.get("type") == "image" for item in content)
    if not has_images:
        logger.error("No frames could be encoded!")
        return []

    logger.info(
        f"Successfully built content with {len([c for c in content if c.get('type') == 'image'])} images"
    )
    return content
