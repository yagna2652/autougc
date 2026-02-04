"""
Generate Prompt Node - Creates video generation prompts based on TikTok analysis.

Takes the video analysis from Claude Vision and generates a prompt
for video generation APIs (Sora, Kling, etc.) to recreate a similar style.

All LLM calls are traced via LangSmith for full observability.
"""

import logging
from typing import Any

import anthropic

from src.pipeline.utils import (
    get_anthropic_client,
    handle_api_error,
    handle_unexpected_error,
    parse_json_response,
)

logger = logging.getLogger(__name__)

# Default output fields for error handling
_ERROR_DEFAULTS = {"video_prompt": ""}


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
    # Prefer enhanced description from Vision analysis, fall back to basic description
    product_description = state.get("enhanced_product_description") or state.get("product_description", "")
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

    # Get Anthropic client
    client, model, error = get_anthropic_client(state, trace_name="generate_prompt")
    if error:
        return {
            "video_prompt": "",
            "error": error,
        }

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
        result = parse_json_response(response_text, context="prompt generation")

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
        return handle_api_error(e, _ERROR_DEFAULTS, context="prompt generation")
    except Exception as e:
        return handle_unexpected_error(e, _ERROR_DEFAULTS, context="prompt generation")


def _build_prompt_request(
    video_analysis: dict[str, Any],
    product_description: str,
    product_images: list[str],
    interaction_plan: dict[str, Any],
    selected_interactions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Build the content for prompt generation request.

    For I2V pipeline: The video model starts with the product image as the first frame,
    so prompts should focus on MOTION and ACTION, not product appearance.

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

    # Build the main prompt - I2V: focus on MOTION since the image is already provided
    prompt = f"""You are an expert at creating MOTION prompts for AI image-to-video models.

IMPORTANT: The video model will start with the actual product image as the first frame.
Your prompt should describe HOW THINGS MOVE, not what the product looks like.

I analyzed a TikTok video for its STYLE. Here's the style to replicate:

{analysis_text}

## PRODUCT INFO (for context only - the model already sees the image)
**Product**: {product_description if product_description else "A product shown in the starting image."}
{interaction_text}

Your task: Create a MOTION PROMPT that describes how the scene animates from the starting image.

KEEP from TikTok:
- Person appearance/vibe (age, clothing, energy)
- Setting/background
- Lighting style
- Camera movement (handheld, angle)
- Pacing and energy level
- Authenticity/UGC feel

FOCUS ON MOTION (the product image is already visible):
- Hand movements: pull, click, flip, rotate, squeeze, tap
- Timing and rhythm of actions
- Camera motion per beat (push in, pull back, slight pan)
- Energy and dynamics (quick/snappy vs smooth/slow)
- DO NOT describe the product's appearance (colors, materials, shape)

CRITICAL REQUIREMENTS:
1. Starting frame shows the product - describe how it MOVES from there
2. Follow the INTERACTION SEQUENCE exactly (beat by beat)
3. Focus on hand movements, camera motion, energy
4. The product is already visible - don't describe its appearance
5. Motion verbs: pull, click, flip, rotate, press, slide, reveal
6. iPhone front-facing camera look, NOT cinematic
7. Real skin with texture, natural imperfections - NOT airbrushed
8. Slight handheld shake, natural micro-movements - NOT robotic
9. Natural indoor lighting - NOT studio lighting
10. Looking at phone screen (like filming themselves)

Respond in JSON format:
{{
    "video_prompt": "A motion-focused prompt. Start with the scene setup (person, setting, lighting from TikTok style), then describe the MOVEMENT and ACTION beat by beat. Do not describe the product's appearance - it's already in the starting frame.",
    "script": "A short casual script (1-3 sentences) adapted for the new product - written how a real person talks on TikTok"
}}

Return ONLY valid JSON."""

    content.append({"type": "text", "text": prompt})

    # NOTE: Product images are NOT sent to Claude for prompt generation in I2V mode.
    # The video model will see the actual product image as the starting frame.
    # Claude only needs the product description for context.

    return content


def _format_interaction_plan(
    interaction_plan: dict[str, Any],
    selected_interactions: list[dict[str, Any]],
) -> str:
    """
    Format the interaction plan into prompt text.

    For I2V: Emphasizes MOTION verbs, timing, and camera movement.
    The product appearance is already visible in the starting frame.

    Args:
        interaction_plan: Planned interaction sequence
        selected_interactions: Selected clips from library

    Returns:
        Formatted string for prompt
    """
    if not interaction_plan or not interaction_plan.get("sequence"):
        return ""

    parts = [
        "",
        "## MOTION SEQUENCE (starting from product image)",
        "**Describe HOW these movements happen, not what the product looks like**",
        "",
    ]

    # Add mechanics notes prominently at the top
    if interaction_plan.get("key_mechanics_notes"):
        parts.append(f"Key motion: {interaction_plan['key_mechanics_notes']}")
        parts.append("")

    for i, beat in enumerate(interaction_plan.get("sequence", [])):
        primitive = beat.get("primitive", "unknown")
        duration = beat.get("duration_s", 0)
        framing = beat.get("framing", "close")
        notes = beat.get("notes", "")
        audio_emphasis = beat.get("audio_emphasis", False)

        # Use motion-focused language
        motion_name = primitive.replace("_", " ").title()
        parts.append(f"Beat {i+1} ({duration}s): {motion_name}")
        parts.append(f"  Camera: {framing} shot")
        if audio_emphasis:
            parts.append("  Rhythm: Emphasize the motion (satisfying click/snap)")
        if notes:
            parts.append(f"  Motion direction: {notes}")

        # Add clip reference if available
        if selected_interactions and i < len(selected_interactions):
            selection = selected_interactions[i]
            if selection.get("match_status") == "matched" and selection.get("clip"):
                clip = selection["clip"]
                parts.append(f"  Reference motion: {clip.get('id')}")

        parts.append("")

    parts.append(f"Total duration: {interaction_plan.get('total_duration_s', 0)}s")

    return "\n".join(parts)


def _format_analysis(analysis: dict[str, Any]) -> str:
    """
    Format the video analysis into a readable string.

    Extracts STYLE elements only (person, setting, lighting, energy, camera).
    Excludes product-specific elements (actions, what_makes_it_work) since
    those will be replaced by the interaction plan.

    Args:
        analysis: Video analysis dict

    Returns:
        Formatted string
    """
    parts = []

    # KEEP: Style/vibe elements
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

    # SKIP: actions - replaced by interaction plan
    # SKIP: what_makes_it_work - product-specific

    if analysis.get("style"):
        parts.append(f"Style: {analysis['style']}")

    if analysis.get("energy"):
        parts.append(f"Energy: {analysis['energy']}")

    if analysis.get("mood"):
        parts.append(f"Mood: {analysis['mood']}")

    return "\n".join(parts) if parts else "No specific style analysis available."
