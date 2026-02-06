"""
Generate Prompt Node - Creates video generation prompts based on TikTok analysis.

Absorbs the reasoning of the former analyze_product, classify_ugc_intent,
plan_interactions, and select_interactions nodes into a single LLM call.
The model receives video analysis, product info, mechanics rules, and the
full interaction library, then outputs a motion prompt and script.

All LLM calls are traced via LangSmith for full observability.
"""

import logging
from typing import Any

import anthropic

from src.pipeline.utils import (
    get_anthropic_client,
    handle_api_error,
    handle_unexpected_error,
    load_interaction_library,
    parse_json_response,
    process_image,
)

logger = logging.getLogger(__name__)

# Default output fields for error handling
_ERROR_DEFAULTS = {"video_prompt": ""}


def generate_prompt_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Generate a video prompt based on TikTok analysis, product info, and mechanics.

    Reads video analysis, product description, mechanics prose, and the
    interaction library to produce a motion prompt and script in one shot.

    Args:
        state: Pipeline state with 'video_analysis', 'product_description',
               'product_mechanics', 'product_images'

    Returns:
        State update with 'video_prompt' and 'suggested_script'
    """
    video_analysis = state.get("video_analysis", {})
    product_description = state.get("product_description", "")
    product_mechanics = state.get("product_mechanics", "")
    product_images = state.get("product_images", [])

    if not video_analysis:
        logger.warning("No video analysis provided")
        return {
            "video_prompt": "",
            "error": "No video analysis to base prompt on",
        }

    logger.info("    ↳ Generating video prompt from analysis")
    logger.info(f"    ↳ Has product description: {bool(product_description)}")
    logger.info(f"    ↳ Has mechanics rules: {bool(product_mechanics)}")

    # Load interaction library
    library = load_interaction_library()
    logger.info(f"    ↳ Interaction library: {len(library.get('clips', []))} clips")

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
            video_analysis, product_description, product_mechanics,
            product_images, library
        )

        # Call Claude
        logger.info(f"    ↳ Calling Claude ({model}) to generate prompt...")
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": content}],
        )
        logger.info("    ↳ Claude response received, parsing...")

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
        scene_description = result.get("scene_description", "")

        logger.info(f"    ↳ Generated video prompt: {len(video_prompt)} chars")
        logger.info(f"    ↳ Prompt preview: {video_prompt[:100]}...")
        if scene_description:
            logger.info(f"    ↳ Scene description: {len(scene_description)} chars")
            logger.info(f"    ↳ Scene preview: {scene_description[:100]}...")

        return {
            "video_prompt": video_prompt,
            "suggested_script": suggested_script,
            "scene_description": scene_description,
            "current_step": "prompt_generated",
        }

    except anthropic.APIError as e:
        return handle_api_error(e, _ERROR_DEFAULTS, context="prompt generation")
    except Exception as e:
        return handle_unexpected_error(e, _ERROR_DEFAULTS, context="prompt generation")


def _build_prompt_request(
    video_analysis: dict[str, Any],
    product_description: str,
    product_mechanics: str,
    product_images: list[str],
    library: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Build the content for prompt generation request.

    Provides the model with video analysis prose, product info, mechanics
    constraints, and the full interaction library inventory so it can pick
    clips, plan beats, and write a motion prompt in one pass.

    Args:
        video_analysis: Analysis from analyze_video node
        product_description: User's product description
        product_mechanics: Prose describing physical interaction rules
        product_images: List of product image URLs or base64
        library: Loaded interaction library dict

    Returns:
        Content array for Claude API
    """
    content = []

    # Format the video analysis
    analysis_text = _format_analysis(video_analysis)

    # Format interaction library inventory
    library_text = _format_library(library)

    # Build the main prompt
    prompt = f"""You are an expert at creating MOTION prompts for AI image-to-video models.

IMPORTANT: The video model will start with the actual product image as the first frame.
Your prompt should describe HOW THINGS MOVE, not what the product looks like.

## TIKTOK STYLE ANALYSIS
I analyzed a TikTok video. Replicate this style:

{analysis_text}

## PRODUCT INFO
**Product**: {product_description if product_description else "A product shown in the starting image."}

## MECHANICS RULES
{product_mechanics if product_mechanics else "No specific mechanics rules provided."}

These rules describe the physical reality of the product — how it's held, what moves,
what stays still, how big it is relative to hands. Your motion prompt MUST obey these
rules. If the rules say "only one finger presses at a time", do not show two fingers
pressing simultaneously. If the rules say "4 keys in a row", do not show 6 keys.

{library_text}

## YOUR TASK
Using the TikTok style, mechanics rules, and interaction library above:

1. **Pick 1-3 clips** from the library that fit the TikTok's energy and style
2. **Plan the beats** — a short choreographed sequence (total ≤ 12 seconds)
3. **Write a motion prompt** describing how the scene animates from the product image
4. **Write a casual script** (1-3 sentences) adapted for this product

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
1. Starting frame shows the product — describe how it MOVES from there
2. Follow the MECHANICS RULES exactly — do not invent impossible movements
3. Reference specific clip IDs you chose from the library
4. Focus on hand movements, camera motion, energy
5. The product is already visible — don't describe its appearance
6. Motion verbs: pull, click, flip, rotate, press, slide, reveal
7. iPhone front-facing camera look, NOT cinematic
8. Real skin with texture, natural imperfections — NOT airbrushed
9. Slight handheld shake, natural micro-movements — NOT robotic
10. Natural indoor lighting — NOT studio lighting
11. Looking at phone screen (like filming themselves)

Respond in JSON format:
{{
    "video_prompt": "A motion-focused prompt. Start with the scene setup (person, setting, lighting from TikTok style), then describe the MOVEMENT and ACTION beat by beat. Reference the clip IDs you chose. Do not describe the product's appearance.",
    "script": "A short casual script (1-3 sentences) adapted for the new product — written how a real person talks on TikTok",
    "scene_description": "A photorealistic image generation prompt for the FIRST FRAME of the video. Describe: the person (age, appearance, clothing from TikTok analysis), the setting/background, the lighting, the product being held or interacted with (name it explicitly), camera angle and framing, UGC/iPhone selfie aesthetic. This will be fed to an image generation model to create the starting frame, so be vivid and specific. Example: 'A young woman in her early 20s with long brown hair wearing a casual oversized hoodie, sitting at a desk in a cozy bedroom with warm natural window lighting, holding a small mechanical keyboard keychain in her right hand, close-up shot from slightly above, iPhone selfie camera style, authentic and unpolished feel'"
}}

Return ONLY valid JSON."""

    content.append({"type": "text", "text": prompt})

    # Send product image so Claude can see what it's writing motion prompts for
    if product_images:
        image_data, media_type = process_image(product_images[0], auto_resize=True)
        if image_data:
            content.append({"type": "text", "text": "\n## PRODUCT IMAGE (for reference)"})
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data,
                },
            })
            logger.info("Added product image to prompt generation request")
        else:
            logger.warning("Failed to process product image for prompt generation")

    return content


def _format_analysis(analysis: dict[str, Any]) -> str:
    """
    Format the video analysis into a readable string.

    Extracts style elements (person, setting, lighting, energy, camera).

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

    if analysis.get("style"):
        parts.append(f"Style: {analysis['style']}")

    if analysis.get("energy"):
        parts.append(f"Energy: {analysis['energy']}")

    if analysis.get("mood"):
        parts.append(f"Mood: {analysis['mood']}")

    return "\n".join(parts) if parts else "No specific style analysis available."


def _format_library(library: dict[str, Any]) -> str:
    """
    Format the interaction library inventory for the prompt.

    Args:
        library: Loaded interaction library dict

    Returns:
        Formatted string listing all clips with their metadata
    """
    clips = library.get("clips", [])
    if not clips:
        return ""

    parts = [
        "## INTERACTION LIBRARY",
        "Available reference clips (pick 1-3 that match the TikTok's energy):",
        "",
    ]

    for clip in clips:
        clip_id = clip.get("id", "unknown")
        primitive = clip.get("primitive", "unknown")
        framing = clip.get("framing", "unknown")
        duration = clip.get("duration_s", 0)
        description = clip.get("description", "")
        tags = clip.get("tags", [])

        line = f"- **{clip_id}**: {primitive} | {framing} | {duration}s"
        if description:
            line += f" | {description}"
        if tags:
            line += f" | tags: {', '.join(tags)}"
        parts.append(line)

    parts.append("")
    return "\n".join(parts)
