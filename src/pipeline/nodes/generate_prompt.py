"""
Generate Prompt Node - Creates video generation prompts based on TikTok analysis.

Takes the video analysis from Claude Vision and generates a prompt
for video generation APIs (Sora, Kling, etc.) to recreate a similar style.

All LLM calls are traced via LangSmith for full observability.
"""

import json
import logging
import os
from typing import Any

import anthropic

from src.tracing import TracedAnthropicClient, is_tracing_enabled

logger = logging.getLogger(__name__)


def generate_prompt_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a video prompt based on TikTok analysis and product info.

    Takes the video analysis and combines it with product information
    to create a prompt for video generation.

    Args:
        state: Pipeline state with 'video_analysis' and optionally 'product_description'

    Returns:
        State update with 'video_prompt' string
    """
    video_analysis = state.get("video_analysis", {})
    product_description = state.get("product_description", "")
    product_images = state.get("product_images", [])
    interaction_plan = state.get("interaction_plan", {})
    selected_interactions = state.get("selected_interactions", [])

    if not video_analysis:
        logger.warning("No video analysis provided")
        return {
            "video_prompt": "",
            "error": "No video analysis to base prompt on",
        }

    logger.info("Generating video prompt from analysis")

    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "video_prompt": "",
            "error": "ANTHROPIC_API_KEY not set",
        }

    # Initialize client (with tracing if enabled)
    if is_tracing_enabled():
        client = TracedAnthropicClient(api_key=api_key, trace_name="generate_prompt")
    else:
        client = anthropic.Anthropic(api_key=api_key)

    model = state.get("config", {}).get("claude_model", "claude-sonnet-4-20250514")

    try:
        # Build the prompt generation request
        content = _build_prompt_request(
            video_analysis, product_description, product_images,
            interaction_plan, selected_interactions
        )

        # Call Claude
        response = client.messages.create(
            model=model,
            max_tokens=1500,
            messages=[{"role": "user", "content": content}],
        )

        # Parse response
        response_text = response.content[0].text
        result = _parse_prompt_response(response_text)

        if not result:
            logger.warning("Could not parse prompt response")
            return {
                "video_prompt": response_text,  # Use raw response as fallback
                "current_step": "prompt_generated",
            }

        video_prompt = result.get("video_prompt", "")
        suggested_script = result.get("script", "")

        logger.info(f"Generated video prompt: {len(video_prompt)} chars")

        return {
            "video_prompt": video_prompt,
            "suggested_script": suggested_script,
            "current_step": "prompt_generated",
        }

    except anthropic.APIError as e:
        logger.error(f"Claude API error: {e}")
        return {
            "video_prompt": "",
            "error": f"Claude API error: {str(e)}",
        }
    except Exception as e:
        logger.exception("Unexpected error during prompt generation")
        return {
            "video_prompt": "",
            "error": str(e),
        }


def _build_prompt_request(
    video_analysis: dict[str, Any],
    product_description: str,
    product_images: list[str],
    interaction_plan: dict[str, Any],
    selected_interactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Build the content for prompt generation request.

    Args:
        video_analysis: Analysis from analyze_video node
        product_description: User's product description
        product_images: List of product image URLs or base64
        interaction_plan: Planned interaction sequence
        selected_interactions: Selected clips from library

    Returns:
        Content array for Claude API
    """
    content = []

    # Format the video analysis
    analysis_text = _format_analysis(video_analysis)

    # Format interaction plan if available
    interaction_text = _format_interaction_plan(interaction_plan, selected_interactions)

    # Build the main prompt
    prompt = f"""You are an expert at creating prompts for AI video generation models (Sora, Kling, etc.).

I analyzed a TikTok video and extracted this information about its style:

{analysis_text}

{"Product to feature: " + product_description if product_description else "No specific product - create a general UGC style video."}
{interaction_text}
Your task: Create a detailed prompt for an AI video generator that will recreate this EXACT style.

CRITICAL REQUIREMENTS FOR REALISM:
1. **Camera Quality**: iPhone front-facing camera look, NOT cinematic
2. **Skin**: Real skin with pores, texture, natural imperfections - NOT airbrushed
3. **Movement**: Slight handheld shake, natural micro-movements - NOT robotic
4. **Lighting**: Natural indoor lighting - NOT studio lighting
5. **Setting**: Real lived-in space - NOT a set
6. **Expression**: Genuine emotions - NOT acted/performative
7. **Eye Contact**: Looking at phone screen (like filming themselves) - NOT through the camera

MECHANICS INTEGRITY (for product interactions):
- Rigid/consistent object shape (no warping)
- Consistent clicking/interaction motion
- Plausible hand grip for product size
- Close-up framing to show interactions clearly
- Sound emphasis where appropriate

The video should be INDISTINGUISHABLE from a real TikTok filmed by a real person.

Respond in this JSON format:
{{
    "video_prompt": "A detailed 150-250 word prompt describing exactly what the AI video generator should create. Be extremely specific about every visual detail to achieve maximum realism. Include the planned interaction sequence.",
    "script": "A short casual script (1-3 sentences) the person might say - written exactly how a real person talks on TikTok"
}}

Return ONLY valid JSON."""

    content.append({"type": "text", "text": prompt})

    # Add product images if available (limit to 2)
    if product_images:
        content.append(
            {"type": "text", "text": "\n\nProduct images to feature in the video:"}
        )

        for i, image in enumerate(product_images[:2]):
            image_data, media_type = _process_image(image)
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


def _format_interaction_plan(
    interaction_plan: dict[str, Any],
    selected_interactions: list[dict[str, Any]],
) -> str:
    """
    Format the interaction plan into prompt text.

    Args:
        interaction_plan: Planned interaction sequence
        selected_interactions: Selected clips from library

    Returns:
        Formatted string for prompt
    """
    if not interaction_plan or not interaction_plan.get("sequence"):
        return ""

    parts = ["\n## INTERACTION SEQUENCE (must follow this sequence):"]

    for i, beat in enumerate(interaction_plan.get("sequence", [])):
        primitive = beat.get("primitive", "unknown")
        duration = beat.get("duration_s", 0)
        framing = beat.get("framing", "close")
        notes = beat.get("notes", "")
        audio_emphasis = beat.get("audio_emphasis", False)

        parts.append(f"\nBeat {i+1} ({duration}s): {primitive.replace('_', ' ').title()}")
        parts.append(f"  - Framing: {framing}")
        if audio_emphasis:
            parts.append("  - Audio: Emphasize sound (ASMR-like)")
        if notes:
            parts.append(f"  - Direction: {notes}")

        # Add matched clip info if available
        if selected_interactions and i < len(selected_interactions):
            selection = selected_interactions[i]
            if selection.get("match_status") == "matched" and selection.get("clip"):
                clip = selection["clip"]
                parts.append(f"  - Reference clip: {clip.get('id')} ({clip.get('duration_s')}s)")

    if interaction_plan.get("key_mechanics_notes"):
        parts.append(f"\nMechanics notes: {interaction_plan['key_mechanics_notes']}")

    parts.append(f"\nTotal duration: {interaction_plan.get('total_duration_s', 0)}s")

    return "\n".join(parts)


def _format_analysis(analysis: dict[str, Any]) -> str:
    """
    Format the video analysis into a readable string.

    Args:
        analysis: Video analysis dict

    Returns:
        Formatted string
    """
    parts = []

    if analysis.get("setting"):
        parts.append(f"Setting: {analysis['setting']}")

    if analysis.get("lighting"):
        parts.append(f"Lighting: {analysis['lighting']}")

    if analysis.get("camera"):
        camera = analysis["camera"]
        if isinstance(camera, dict):
            camera_desc = f"Camera: {camera.get('framing', 'medium shot')}, {camera.get('angle', 'eye-level')}, {camera.get('movement', 'handheld')}"
        else:
            camera_desc = f"Camera: {camera}"
        parts.append(camera_desc)

    if analysis.get("person"):
        person = analysis["person"]
        if isinstance(person, dict):
            person_desc = f"Person: {person.get('age_range', 'young adult')}, {person.get('appearance', '')}, {person.get('vibe', 'casual')}"
        else:
            person_desc = f"Person: {person}"
        parts.append(person_desc)

    if analysis.get("actions"):
        parts.append(f"Actions: {analysis['actions']}")

    if analysis.get("style"):
        parts.append(f"Style: {analysis['style']}")

    if analysis.get("energy"):
        parts.append(f"Energy: {analysis['energy']}")

    if analysis.get("mood"):
        parts.append(f"Mood: {analysis['mood']}")

    if analysis.get("what_makes_it_work"):
        parts.append(f"What makes it work: {analysis['what_makes_it_work']}")

    return "\n".join(parts) if parts else "No specific style analysis available."


def _process_image(image: str) -> tuple[str, str]:
    """
    Process an image string (URL or base64) into base64 data.

    Args:
        image: Image URL or base64 data

    Returns:
        Tuple of (base64_data, media_type) or (None, None)
    """
    import base64

    try:
        if image.startswith("data:"):
            # Data URL format: data:image/jpeg;base64,/9j/4AAQ...
            parts = image.split(";base64,")
            if len(parts) == 2:
                media_type = parts[0].replace("data:", "")
                image_data = parts[1]
                return image_data, media_type

        elif image.startswith("http"):
            # URL - we can't easily download here, skip for now
            logger.warning("URL images not supported in prompt generation, skipping")
            return None, None

        else:
            # Assume raw base64
            return image, "image/jpeg"

    except Exception as e:
        logger.warning(f"Failed to process image: {e}")
        return None, None


def _parse_prompt_response(response_text: str) -> dict[str, Any] | None:
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
