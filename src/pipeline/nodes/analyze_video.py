"""
Analyze Video Node - Simple Claude Vision analysis of TikTok video frames.

This node takes extracted frames from a TikTok video and uses Claude Vision
to understand the video's style, content, and approach for recreation.

All LLM calls are traced via LangSmith for full observability.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

import anthropic

from src.tracing import TracedAnthropicClient, is_tracing_enabled

logger = logging.getLogger(__name__)


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

    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "video_analysis": {},
            "error": "ANTHROPIC_API_KEY not set",
        }

    # Initialize client (with tracing if enabled)
    if is_tracing_enabled():
        client = TracedAnthropicClient(api_key=api_key, trace_name="analyze_video")
    else:
        client = anthropic.Anthropic(api_key=api_key)

    model = state.get("config", {}).get("claude_model", "claude-sonnet-4-20250514")

    try:
        # Build the message content with frames
        content = _build_analysis_content(frames)

        # Call Claude Vision
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": content}],
        )

        # Parse response
        response_text = response.content[0].text
        analysis = _parse_analysis_response(response_text)

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
        logger.error(f"Claude API error: {e}")
        return {
            "video_analysis": {},
            "error": f"Claude API error: {str(e)}",
        }
    except Exception as e:
        logger.exception("Unexpected error during video analysis")
        return {
            "video_analysis": {},
            "error": str(e),
        }


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
        image_data, media_type = _encode_image(frame_path)
        if image_data:
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

    return content


def _encode_image(image_path: str) -> tuple[str, str]:
    """
    Encode an image file to base64.

    Args:
        image_path: Path to the image file

    Returns:
        Tuple of (base64_data, media_type) or (None, None) on error
    """
    import base64

    try:
        path = Path(image_path)

        # Determine media type
        suffix = path.suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_types.get(suffix, "image/jpeg")

        # Read and encode
        with open(path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")

        return data, media_type

    except Exception as e:
        logger.warning(f"Failed to encode image {image_path}: {e}")
        return None, None


def _parse_analysis_response(response_text: str) -> dict[str, Any] | None:
    """
    Parse the JSON response from Claude.

    Args:
        response_text: Raw response text

    Returns:
        Parsed dict or None
    """
    if not response_text:
        return None

    try:
        # Find JSON in response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start != -1 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)

        return None

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON: {e}")
        return None
