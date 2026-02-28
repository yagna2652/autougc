"""
Generate Prompt Node - Creates video generation prompts based on TikTok analysis.

Absorbs the reasoning of the former analyze_product, classify_ugc_intent,
plan_interactions, and select_interactions nodes into a single LLM call.
The model receives video analysis, product info, mechanics rules, and the
full interaction library, then outputs a motion prompt and script.

All LLM calls are traced via LangSmith for full observability.
"""

import json
import logging
import re
import time
from typing import Any

from src.pipeline.utils import (
    get_openrouter_client,
    handle_unexpected_error,
    load_interaction_library,
    parse_json_response,
    process_image,
    resolve_clip_ids_to_plain_language,
)
from src.prompt_store import get_prompt_store

logger = logging.getLogger(__name__)

# Default output fields for error handling
_ERROR_DEFAULTS = {"video_prompt": ""}

# ---------------------------------------------------------------------------
# Template skeleton — same as the f-string in _build_prompt_request_openrouter
# but with fixed placeholders instead of runtime values. Only changes when the
# instructions are edited, so the hash is stable across runs.
# ---------------------------------------------------------------------------
_TEMPLATE_SKELETON = """You are an expert at creating MOTION prompts for AI image-to-video models.

IMPORTANT: The video model will start with the actual product image as the first frame.
Your prompt should describe HOW THINGS MOVE, not what the product looks like.

## TIKTOK STYLE ANALYSIS
I analyzed a TikTok video. Replicate this style:

{{ANALYSIS}}

## PRODUCT INFO
**Product**: {{PRODUCT_DESCRIPTION}}

## MECHANICS RULES
{{PRODUCT_MECHANICS}}

These rules describe the physical reality of the product — how it's held, what moves,
what stays still, how big it is relative to hands. Your motion prompt MUST obey these
rules. If the rules say "only one finger presses at a time", do not show two fingers
pressing simultaneously. If the rules say "4 keys in a row", do not show 6 keys.

## PHYSICS CONSTRAINTS (MANDATORY IN video_prompt)
- Describe the hand wrapped around the device (which fingers move, which parts stay still).
- Describe the keys physically moving: plunging downward, sinking into the housing, springing back up.
- Use the exact verbs and energy from the MECHANICS RULES — do not substitute with generic words.
- Include at least 3 "DO NOT" constraints taken directly from the mechanics.
- Never describe the motion as typing, entering data, or using a utility device.

{{LIBRARY}}

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
- Energy and dynamics: this is a fidget toy — force the motion to be playful, bouncy, repetitive, or absentminded (e.g., "idly drumming," "satisfying bouncy squeeze")
- Point of contact: explicitly state where fingers press (the FLAT TOP SURFACE of the keycaps)
- Key physics: you MUST describe the keys physically moving — use "plunges downward," "sinks into the housing," "springs back up"
- Camera motion per beat (push in, pull back, slight pan)
- DO NOT describe the product's appearance (colors, materials, shape)

CRITICAL REQUIREMENTS:
1. Starting frame shows the product — describe how it MOVES from there
2. Follow the MECHANICS RULES exactly — do not invent impossible movements
3. Reference specific clip IDs you chose from the library
4. Focus on hand movements, camera motion, energy
5. The product is already visible — don't describe its appearance
6. Motion verbs: squeeze, plunge, crunch, bounce, drum, spring, sink, press
7. iPhone front-facing camera look, NOT cinematic
8. Real skin with texture, natural imperfections — NOT airbrushed
9. Slight handheld shake, natural micro-movements — NOT robotic
10. Natural indoor lighting — NOT studio lighting
11. Looking at phone screen (like filming themselves)
12. Open the prompt by stating the device is held VERTICALLY with the chain dangling at the bottom
13. Explicitly state what remains stationary in each beat
14. Add a clear "DO NOT SHOW" section inside the video prompt

Respond in JSON format:
{{
    "video_prompt": "...",
    "negative_prompt": "...",
    "script": "...",
    "scene_description": "..."
}}

Return ONLY valid JSON."""


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
    config = state.get("config", {})

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

    # Get OpenRouter client for text model
    client, model, error = get_openrouter_client(
        state, trace_name="generate_prompt", model_type="text"
    )
    if error:
        return {
            "video_prompt": "",
            "error": error,
        }

    try:
        # Build the prompt generation request
        content = _build_prompt_request_openrouter(
            video_analysis, product_description, product_mechanics,
            product_images, library,
            video_model=config.get("video_model", "sora"),
        )

        # Call OpenRouter
        logger.info(f"    ↳ Calling OpenRouter ({model}) to generate prompt...")
        t0 = time.time()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
        )
        elapsed = time.time() - t0
        logger.info("    ↳ OpenRouter response received, parsing...")

        # Check for errors
        if hasattr(response, 'error') and response.error:
            error_msg = response.error.get('message', 'Unknown error')
            logger.error(f"OpenRouter error: {error_msg}")
            return {
                "video_prompt": "",
                "error": f"OpenRouter error: {error_msg}",
            }

        # Parse response
        if not response.choices or not response.choices[0].message:
            logger.error("No response from OpenRouter")
            return {
                "video_prompt": "",
                "error": "No response from OpenRouter",
            }

        response_text = response.choices[0].message.content
        if not response_text:
            logger.error("Empty response from OpenRouter")
            return {
                "video_prompt": "",
                "error": "Empty response from OpenRouter",
            }

        result = parse_json_response(response_text, context="prompt generation")

        if not result:
            logger.warning("Could not parse prompt response")
            resolved_raw = resolve_clip_ids_to_plain_language(response_text, library)
            return {
                "video_prompt": resolved_raw,  # Use raw response as fallback
                "current_step": "prompt_generated",
            }

        video_prompt = resolve_clip_ids_to_plain_language(
            result.get("video_prompt", ""), library
        )
        negative_prompt = str(result.get("negative_prompt", "") or "").strip()
        if not negative_prompt:
            impossible = _extract_impossible_interactions(product_mechanics)
            if impossible:
                negative_prompt = "; ".join(
                    f"Do NOT show {constraint}" for constraint in impossible
                )
        video_prompt = _append_negative_constraints(video_prompt, negative_prompt)
        suggested_script = result.get("script", "")
        scene_description = result.get("scene_description", "")

        logger.info(f"    ↳ Generated video prompt: {len(video_prompt)} chars")
        logger.info(f"    ↳ Prompt preview: {video_prompt[:100]}...")
        if scene_description:
            logger.info(f"    ↳ Scene description: {len(scene_description)} chars")
            logger.info(f"    ↳ Scene preview: {scene_description[:100]}...")

        # --- Trace storage ---
        trace_id = None
        template_version = None
        try:
            # Build assembled_prompt from text parts of content array
            assembled_prompt = "\n".join(
                part["text"] for part in content if part.get("type") == "text"
            )
            # Extract token usage from response
            token_usage = None
            if hasattr(response, "usage") and response.usage:
                token_usage = {
                    "input_tokens": getattr(response.usage, "prompt_tokens", 0) or 0,
                    "output_tokens": getattr(response.usage, "completion_tokens", 0) or 0,
                }
            store = get_prompt_store()
            trace_id = store.save_trace(
                template_text=_TEMPLATE_SKELETON,
                assembled_prompt=assembled_prompt,
                model=model,
                inputs_snapshot={
                    "video_analysis": video_analysis,
                    "product_description": product_description,
                    "product_mechanics": product_mechanics,
                },
                job_id=state.get("job_id"),
                raw_response=response_text,
                processed_output={
                    "video_prompt": video_prompt,
                    "suggested_script": suggested_script,
                    "scene_description": scene_description,
                },
                token_usage=token_usage,
                latency_ms=int(elapsed * 1000),
            )
            # Fetch template version for SSE passthrough
            trace_data = store.get_trace(trace_id)
            if trace_data:
                template_version = trace_data.get("template_version")
            logger.info(f"    ↳ Trace saved: {trace_id[:8]}... (template v{template_version})")
        except Exception as trace_err:
            logger.warning(f"    ↳ Trace storage failed (non-fatal): {trace_err}")

        return {
            "video_prompt": video_prompt,
            "suggested_script": suggested_script,
            "scene_description": scene_description,
            "trace_id": trace_id,
            "template_version": template_version,
            "current_step": "prompt_generated",
        }

    except Exception as e:
        logger.error(f"Error during prompt generation: {str(e)}")
        return handle_unexpected_error(e, _ERROR_DEFAULTS, context="prompt generation")


def _build_prompt_request_openrouter(
    video_analysis: dict[str, Any],
    product_description: str,
    product_mechanics: str,
    product_images: list[str],
    library: dict[str, Any],
    video_model: str = "sora",
) -> list[dict[str, Any]]:
    """
    Build the content for prompt generation request (OpenRouter format).

    Args:
        video_analysis: Analysis from analyze_video node
        product_description: User's product description
        product_mechanics: Prose describing physical interaction rules
        product_images: List of product image URLs or base64
        library: Loaded interaction library dict
        video_model: Target video model (affects prompt instructions)

    Returns:
        Content array for OpenRouter API (OpenAI-compatible format)
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

## PHYSICS CONSTRAINTS (MANDATORY IN video_prompt)
- Describe the hand wrapped around the device (which fingers move, which parts stay still).
- Describe the keys physically moving: plunging downward, sinking into the housing, springing back up.
- Use the exact verbs and energy from the MECHANICS RULES — do not substitute with generic words.
- Include at least 3 "DO NOT" constraints taken directly from the mechanics.
- Never describe the motion as typing, entering data, or using a utility device.

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
- Energy and dynamics: this is a fidget toy — force the motion to be playful, bouncy, repetitive, or absentminded (e.g., "idly drumming," "satisfying bouncy squeeze")
- Point of contact: explicitly state where fingers press (the FLAT TOP SURFACE of the keycaps)
- Key physics: you MUST describe the keys physically moving — use "plunges downward," "sinks into the housing," "springs back up"
- Camera motion per beat (push in, pull back, slight pan)
- DO NOT describe the product's appearance (colors, materials, shape)

CRITICAL REQUIREMENTS:
1. Starting frame shows the product — describe how it MOVES from there
2. Follow the MECHANICS RULES exactly — do not invent impossible movements
3. Reference specific clip IDs you chose from the library
4. Focus on hand movements, camera motion, energy
5. The product is already visible — don't describe its appearance
6. Motion verbs: squeeze, plunge, crunch, bounce, drum, spring, sink, press
7. iPhone front-facing camera look, NOT cinematic
8. Real skin with texture, natural imperfections — NOT airbrushed
9. Slight handheld shake, natural micro-movements — NOT robotic
10. Natural indoor lighting — NOT studio lighting
11. Looking at phone screen (like filming themselves)
12. Open the prompt by stating the device is held VERTICALLY with the chain dangling at the bottom
13. Explicitly state what remains stationary in each beat
14. Add a clear "DO NOT SHOW" section inside the video prompt

Respond in JSON format:
{{
    "video_prompt": "A visual, cinematic scene description — NOT a technical manual. Open with orientation (VERTICALLY held, chain dangling). Then describe each beat as a vivid motion scene: what the fingers do, how the keys plunge and spring, the energy and rhythm. End with a DO NOT SHOW section. Use the same verbs as the mechanics rules.",
    "negative_prompt": "A semicolon-separated list of explicit forbidden motions from mechanics and physics constraints.",
    "script": "A short casual script (1-3 sentences) adapted for the new product — written how a real person talks on TikTok",
    "scene_description": "A photorealistic image generation prompt for the FIRST FRAME of the video. Describe: the person (age, appearance, clothing from TikTok analysis), the setting/background, the lighting, the product being held or interacted with (name it explicitly), camera angle and framing, UGC/iPhone selfie aesthetic. This will be fed to an image generation model to create the starting frame, so be vivid and specific. Example: 'A young woman in her early 20s with long brown hair wearing a casual oversized hoodie, sitting at a desk in a cozy bedroom with warm natural window lighting, holding a small mechanical keyboard keychain in her right hand, close-up shot from slightly above, iPhone selfie camera style, authentic and unpolished feel'"
}}

Return ONLY valid JSON."""

    content.append({"type": "text", "text": prompt})

    # O3 reference-to-video: instruct LLM to use @Element1 notation
    if video_model == "kling-o3-ref":
        content.append({"type": "text", "text": """
## @Element1 REFERENCE NOTATION (CRITICAL — O3 model)
The target video model uses reference-conditioned generation. When referring to the product in the video_prompt, use `@Element1` as an inline token so the model binds the product's identity element.

Rules:
- Use `@Element1` where you would normally name the product (e.g., "A hand picks up @Element1 and presses…")
- You may use `@Element1` multiple times in the prompt
- Do NOT wrap it in quotes or brackets — just `@Element1` bare
- The model will replace `@Element1` with the actual product reference at render time
"""})

    # Send product image in OpenRouter format
    if product_images:
        image_data, media_type = process_image(product_images[0], auto_resize=True)
        if image_data:
            content.append({"type": "text", "text": "\n## PRODUCT IMAGE (for reference)"})
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{image_data}"
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


def _extract_impossible_interactions(product_mechanics: str) -> list[str]:
    """
    Extract bullet-point impossible interactions from mechanics prose.
    """
    if not product_mechanics:
        return []

    constraints: list[str] = []
    in_section = False

    for raw_line in product_mechanics.splitlines():
        line = raw_line.strip()
        if not line:
            if in_section and constraints:
                break
            continue

        if re.match(r"^impossible interactions\s*:?\s*$", line, flags=re.IGNORECASE):
            in_section = True
            continue

        if in_section:
            if line.startswith("-"):
                item = line.lstrip("- ").strip()
                if item:
                    constraints.append(item)
            elif constraints:
                break

    return constraints


def _append_negative_constraints(video_prompt: str, negative_prompt: str) -> str:
    """
    Append forbidden-motion constraints to the generated video prompt.
    """
    if not negative_prompt.strip():
        return video_prompt

    negative_lines = []
    for part in negative_prompt.split(";"):
        cleaned = part.strip().strip(".")
        if cleaned:
            negative_lines.append(f"- {cleaned}")

    if not negative_lines:
        return video_prompt

    return (
        f"{video_prompt.strip()}\n\n"
        "DO NOT SHOW:\n"
        + "\n".join(negative_lines)
    ).strip()
