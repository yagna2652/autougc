"""
Analyze Video Node - Vision analysis of TikTok video frames using OpenRouter.

This node takes extracted frames from a TikTok video and uses a vision model
(via OpenRouter) to understand the video's style, content, and approach for recreation.

All LLM calls are traced via LangSmith for full observability.
"""

import logging
from typing import Any

from openai import OpenAI

from src.pipeline.utils import (
    encode_image_file,
    get_openrouter_client,
    handle_unexpected_error,
    parse_json_response,
)

logger = logging.getLogger(__name__)

# Default output fields for error handling
_ERROR_DEFAULTS = {"video_analysis": {}}


def analyze_video_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Analyze video frames using OpenRouter Vision.

    Takes extracted frames and sends them to a vision model via OpenRouter for analysis.
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

    logger.info(f"    ↳ Analyzing {len(frames)} video frames with OpenRouter Vision")

    # Get OpenRouter client
    client, model, error = get_openrouter_client(state, trace_name="analyze_video")
    if error:
        return {
            "video_analysis": {},
            "error": error,
        }

    try:
        # Build the message content with frames
        logger.info("    ↳ Building analysis content from frames...")
        content = _build_analysis_content_openrouter(frames)

        if not content:
            logger.error("    ↳ Failed to build content - no valid frames")
            return {
                "video_analysis": {},
                "error": "Failed to encode any frames for analysis",
                "current_step": "analysis_failed",
            }

        logger.info(f"    ↳ Sending {len(content)} items to OpenRouter Vision API...")
        logger.info(f"    ↳ Using model: {model}")

        # Call OpenRouter Vision API (OpenAI-compatible)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
                max_tokens=2000,
            )
        except Exception as api_error:
            logger.error(f"OpenRouter API error: {str(api_error)}")
            error_msg = str(api_error)
            if "insufficient credits" in error_msg.lower():
                error_msg = "Insufficient credits on OpenRouter. Please add credits at https://openrouter.ai/credits"
            return {
                "video_analysis": {},
                "error": f"OpenRouter API error: {error_msg}",
                "current_step": "analysis_failed",
            }

        logger.info("OpenRouter Vision response received")

        # Check for error field in response (OpenRouter-specific)
        if hasattr(response, "error") and response.error:
            error_msg = response.error.get("message", "Unknown error")
            error_code = response.error.get("code", "N/A")
            provider = response.error.get("metadata", {}).get(
                "provider_name", "Unknown"
            )
            logger.error(
                f"OpenRouter error: {error_msg} (Code: {error_code}, Provider: {provider})"
            )
            logger.error(f"Full error object: {response.error}")

            # Try to get more details from metadata
            if "metadata" in response.error:
                logger.error(f"Error metadata: {response.error['metadata']}")

            return {
                "video_analysis": {},
                "error": f"OpenRouter API error: {error_msg} (Provider: {provider})",
                "current_step": "analysis_failed",
            }

        # Parse response with error handling
        if not response.choices:
            logger.error("No choices in response")
            logger.error(f"Response object: {response}")
            return {
                "video_analysis": {},
                "error": "No response choices from OpenRouter API",
                "current_step": "analysis_failed",
            }

        message = response.choices[0].message
        if not message:
            logger.error("No message in response choice")
            return {
                "video_analysis": {},
                "error": "No message in OpenRouter response",
                "current_step": "analysis_failed",
            }

        response_text = message.content
        if not response_text:
            logger.error("No content in message")
            logger.error(f"Message object: {message}")
            # Check if there's a refusal or other field
            if hasattr(message, "refusal") and message.refusal:
                logger.error(f"Model refused: {message.refusal}")
                return {
                    "video_analysis": {},
                    "error": f"Model refused: {message.refusal}",
                    "current_step": "analysis_failed",
                }
            return {
                "video_analysis": {},
                "error": "Empty content from OpenRouter API",
                "current_step": "analysis_failed",
            }

        logger.info(f"Response text length: {len(response_text)}")
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

    except Exception as e:
        logger.error(f"Error during video analysis: {str(e)}")
        return handle_unexpected_error(e, _ERROR_DEFAULTS, context="video analysis")


def _build_analysis_content_openrouter(frames: list[str]) -> list[dict[str, Any]]:
    """
    Build the content array for OpenRouter Vision API (OpenAI-compatible format).

    Args:
        frames: List of frame file paths

    Returns:
        Content array for OpenRouter API
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

        # Add the image in OpenAI/OpenRouter format
        logger.debug(f"Encoding frame: {frame_path}")
        image_data, media_type = encode_image_file(frame_path)
        if image_data:
            logger.debug(f"Frame encoded successfully: {len(image_data)} bytes")
            # OpenRouter uses OpenAI-compatible format
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{media_type};base64,{image_data}"},
                }
            )
        else:
            logger.warning(f"Failed to encode frame: {frame_path}")

    # Check if we got at least one image
    has_images = any(item.get("type") == "image_url" for item in content)
    if not has_images:
        logger.error("No frames could be encoded!")
        return []

    logger.info(
        f"Successfully built content with {len([c for c in content if c.get('type') == 'image_url'])} images"
    )
    return content
