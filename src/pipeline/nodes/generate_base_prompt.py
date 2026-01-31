"""
Generate Base Prompt Node - Creates video generation prompts using Claude.

This node uses Claude to generate detailed video prompts that will create
realistic UGC-style TikTok videos when sent to video generation models like
Sora 2 or Kling.

All LLM calls are traced via LangSmith for full prompt observability.
"""

import logging
import os
from typing import Any

from src.pipeline.state import (
    PipelineState,
    PipelineStep,
    mark_failed,
    update_progress,
)
from src.tracing import TracedAnthropicClient, is_tracing_enabled

logger = logging.getLogger(__name__)


def generate_base_prompt_node(state: PipelineState) -> dict[str, Any]:
    """
    Generate base video prompt using Claude.

    This node:
    1. Takes blueprint data, product analysis, and product description
    2. Uses Claude to generate a detailed video prompt
    3. Returns the base prompt (before mechanics enhancement)

    Args:
        state: Current pipeline state with blueprint and product data

    Returns:
        Partial state update with base_prompt, suggested_script, and progress
    """

    state.get("blueprint", {})
    blueprint_summary = state.get("blueprint_summary", {})
    product_analysis = state.get("product_analysis", {})
    product_description = state.get("product_description", "")
    product_context = state.get("product_context", {})
    product_images = state.get("product_images", [])

    logger.info("Generating base video prompt with Claude")

    try:
        # Update progress
        progress_update = update_progress(state, PipelineStep.GENERATING_BASE_PROMPT, 8)

        # Get config
        config = state.get("config", {})
        claude_model = config.get("claude_model", "claude-sonnet-4-20250514")
        target_duration = config.get("target_duration", 8.0)

        # Get API key from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            return {
                **progress_update,
                **mark_failed(
                    state,
                    "ANTHROPIC_API_KEY not set",
                    {"hint": "Set ANTHROPIC_API_KEY environment variable"},
                ),
            }

        # If we have product images, use Claude Vision to generate the prompt
        if product_images:
            result = _generate_prompt_with_vision(
                api_key=api_key,
                model=claude_model,
                product_images=product_images,
                product_description=product_description,
                product_context=product_context,
                product_analysis=product_analysis,
                blueprint_summary=blueprint_summary,
                target_duration=target_duration,
            )
        else:
            # Generate prompt without images (text-only)
            result = _generate_prompt_text_only(
                api_key=api_key,
                model=claude_model,
                product_description=product_description,
                product_context=product_context,
                product_analysis=product_analysis,
                blueprint_summary=blueprint_summary,
                target_duration=target_duration,
            )

        if not result:
            # Fallback to template-based prompt
            result = _generate_template_prompt(
                product_description=product_description,
                blueprint_summary=blueprint_summary,
            )

        base_prompt = result.get("prompt", "")
        suggested_script = result.get("script", "")

        if not base_prompt:
            return {
                **progress_update,
                **mark_failed(state, "Failed to generate video prompt"),
            }

        logger.info(f"Base prompt generated: {len(base_prompt)} characters")

        return {
            **progress_update,
            "base_prompt": base_prompt,
            "suggested_script": suggested_script,
        }

    except Exception as e:
        logger.exception("Unexpected error generating base prompt")
        return mark_failed(
            state,
            f"Failed to generate base prompt: {str(e)}",
            {"exception_type": type(e).__name__},
        )


def _generate_prompt_with_vision(
    api_key: str,
    model: str,
    product_images: list[str],
    product_description: str,
    product_context: dict[str, Any],
    product_analysis: dict[str, Any],
    blueprint_summary: dict[str, Any],
    target_duration: float,
) -> dict[str, Any]:
    """
    Generate video prompt using Claude Vision with product images.

    Args:
        api_key: Anthropic API key
        model: Claude model to use
        product_images: List of base64-encoded product images
        product_description: User-provided product description
        product_context: Rich product context
        product_analysis: Product analysis from previous node
        blueprint_summary: Blueprint summary from analysis
        target_duration: Target video duration

    Returns:
        Dict with 'prompt' and 'script' keys
    """
    import anthropic

    if is_tracing_enabled():
        client = TracedAnthropicClient(
            api_key=api_key, trace_name="generate_base_prompt_vision"
        )
    else:
        client = anthropic.Anthropic(api_key=api_key)

    # Build image content
    image_content = _build_image_content(product_images[:3])

    if not image_content:
        return {}

    # Build the prompt
    prompt_text = _build_vision_prompt(
        product_description=product_description,
        product_context=product_context,
        product_analysis=product_analysis,
        blueprint_summary=blueprint_summary,
        target_duration=target_duration,
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        *image_content,
                        {"type": "text", "text": prompt_text},
                    ],
                }
            ],
        )

        response_text = response.content[0].text if response.content else ""
        return _parse_prompt_response(response_text)

    except Exception as e:
        logger.error(f"Claude Vision API error: {e}")
        return {}


def _generate_prompt_text_only(
    api_key: str,
    model: str,
    product_description: str,
    product_context: dict[str, Any],
    product_analysis: dict[str, Any],
    blueprint_summary: dict[str, Any],
    target_duration: float,
) -> dict[str, Any]:
    """
    Generate video prompt using Claude without images.

    Args:
        api_key: Anthropic API key
        model: Claude model to use
        product_description: User-provided product description
        product_context: Rich product context
        product_analysis: Product analysis (may be empty)
        blueprint_summary: Blueprint summary from analysis
        target_duration: Target video duration

    Returns:
        Dict with 'prompt' and 'script' keys
    """
    import anthropic

    if is_tracing_enabled():
        client = TracedAnthropicClient(
            api_key=api_key, trace_name="generate_base_prompt_text"
        )
    else:
        client = anthropic.Anthropic(api_key=api_key)

    # Build the prompt
    prompt_text = _build_text_only_prompt(
        product_description=product_description,
        product_context=product_context,
        product_analysis=product_analysis,
        blueprint_summary=blueprint_summary,
        target_duration=target_duration,
    )

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt_text}],
        )

        response_text = response.content[0].text if response.content else ""
        return _parse_prompt_response(response_text)

    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return {}


def _build_image_content(product_images: list[str]) -> list[dict[str, Any]]:
    """
    Build image content blocks for Claude API.

    Args:
        product_images: List of base64-encoded images

    Returns:
        List of image content blocks
    """
    image_content = []

    for image in product_images:
        try:
            if image.startswith("data:"):
                parts = image.split(";base64,")
                if len(parts) == 2:
                    media_type = parts[0].replace("data:", "")
                    image_data = parts[1]

                    valid_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
                    if media_type not in valid_types:
                        media_type = "image/jpeg"

                    image_content.append(
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        }
                    )
            elif image.startswith("http"):
                image_content.append(
                    {
                        "type": "image",
                        "source": {"type": "url", "url": image},
                    }
                )
            else:
                image_content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image,
                        },
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to process product image: {e}")

    return image_content


def _build_vision_prompt(
    product_description: str,
    product_context: dict[str, Any],
    product_analysis: dict[str, Any],
    blueprint_summary: dict[str, Any],
    target_duration: float,
) -> str:
    """
    Build the prompt for Claude Vision to generate a video prompt.
    """
    # Build context sections
    product_info = ""
    if product_description:
        product_info += f"Product description: {product_description}\n"
    if product_analysis:
        if product_analysis.get("type"):
            product_info += f"Product type: {product_analysis['type']}\n"
        if product_analysis.get("key_features"):
            features = ", ".join(product_analysis["key_features"])
            product_info += f"Key features: {features}\n"

    # Build product context info
    context_info = _build_product_context_info(product_context)

    # Build blueprint context
    blueprint_context = ""
    if blueprint_summary:
        blueprint_context = f"""
Reference video style:
- Hook Style: {blueprint_summary.get("hook_style", "casual_share")}
- Body Framework: {blueprint_summary.get("body_framework", "demonstration")}
- CTA Style: {blueprint_summary.get("cta_urgency", "soft")}
- Setting: {blueprint_summary.get("setting", "bedroom")}
- Lighting: {blueprint_summary.get("lighting", "natural")}
- Energy Level: {blueprint_summary.get("energy", "medium")}

Original script reference:
"{blueprint_summary.get("transcript", "")[:500]}"
"""

    return f"""You are an expert at creating prompts for AI video generation models (like Sora 2 and Kling) that produce authentic UGC (User-Generated Content) style videos.

Analyze the product image(s) provided and generate a detailed video prompt that will create a realistic TikTok-style product review video.

{product_info}
{context_info}
{blueprint_context}

Target video duration: {target_duration} seconds

Your task:
1. Consider the product and how it should be showcased
2. Generate a detailed prompt for the AI video model
3. Suggest a casual script the person might say

The prompt MUST create a video that looks like a REAL TikTok, NOT an AI-generated video. Include these elements:

CRITICAL REALISM REQUIREMENTS:
- iPhone front camera quality (not cinematic)
- Real skin with pores, texture, natural imperfections
- Handheld camera shake and amateur framing
- Natural indoor lighting (not studio lighting)
- Authentic bedroom/bathroom/kitchen setting
- Person looking at phone screen, not through camera
- Genuine excitement, not acted performance

Respond in this exact JSON format:
{{
  "videoPrompt": "The complete, detailed prompt for the AI video generator. This should be 150-300 words and extremely specific about achieving realism.",
  "suggestedScript": "A short, casual script the person might say (2-3 sentences, very casual TikTok style)"
}}

Return ONLY valid JSON, no other text."""


def _build_text_only_prompt(
    product_description: str,
    product_context: dict[str, Any],
    product_analysis: dict[str, Any],
    blueprint_summary: dict[str, Any],
    target_duration: float,
) -> str:
    """
    Build a text-only prompt for Claude (no images).
    """
    product_info = f"Product: {product_description}" if product_description else ""
    context_info = _build_product_context_info(product_context)

    blueprint_context = ""
    if blueprint_summary:
        blueprint_context = f"""
Reference video style:
- Hook Style: {blueprint_summary.get("hook_style", "casual_share")}
- Body Framework: {blueprint_summary.get("body_framework", "demonstration")}
- CTA Style: {blueprint_summary.get("cta_urgency", "soft")}
- Setting: {blueprint_summary.get("setting", "bedroom")}
- Lighting: {blueprint_summary.get("lighting", "natural")}
- Energy Level: {blueprint_summary.get("energy", "medium")}

Original script reference:
"{blueprint_summary.get("transcript", "")[:500]}"
"""

    return f"""You are an expert at creating prompts for AI video generation models (like Sora 2 and Kling) that produce authentic UGC (User-Generated Content) style videos.

Generate a detailed video prompt that will create a realistic TikTok-style product review video.

{product_info}
{context_info}
{blueprint_context}

Target video duration: {target_duration} seconds

The prompt MUST create a video that looks like a REAL TikTok, NOT an AI-generated video. Include:

CRITICAL REALISM REQUIREMENTS:
- iPhone front camera quality
- Real skin with pores and natural imperfections
- Handheld camera shake
- Natural indoor lighting
- Authentic home setting
- Person looking at phone screen
- Genuine emotions

Respond in this exact JSON format:
{{
  "videoPrompt": "The complete, detailed prompt for the AI video generator (150-300 words).",
  "suggestedScript": "A short, casual script (2-3 sentences)"
}}

Return ONLY valid JSON."""


def _build_product_context_info(product_context: dict[str, Any]) -> str:
    """Build product context info string."""
    if not product_context:
        return ""

    parts = []
    if product_context.get("type"):
        parts.append(f"Product type: {product_context['type']}")
    if product_context.get("interactions"):
        parts.append(f"Key interactions: {', '.join(product_context['interactions'])}")
    if product_context.get("tactile_features"):
        parts.append(
            f"Tactile features: {', '.join(product_context['tactile_features'])}"
        )
    if product_context.get("sound_features"):
        parts.append(f"Sound features: {', '.join(product_context['sound_features'])}")
    if product_context.get("size_description"):
        parts.append(f"Size: {product_context['size_description']}")
    if product_context.get("highlight_feature"):
        parts.append(f"Highlight: {product_context['highlight_feature']}")

    if parts:
        return "Product details:\n" + "\n".join(parts)
    return ""


def _parse_prompt_response(response_text: str) -> dict[str, Any]:
    """Parse the JSON response from Claude."""
    import json

    if not response_text:
        return {}

    try:
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start != -1 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            result = json.loads(json_str)
            return {
                "prompt": result.get("videoPrompt", ""),
                "script": result.get("suggestedScript", ""),
            }

        return {}

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON response: {e}")
        return {}


def _generate_template_prompt(
    product_description: str,
    blueprint_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Generate a fallback template-based prompt when Claude fails.
    """
    setting = blueprint_summary.get("setting", "bedroom")
    lighting = blueprint_summary.get("lighting", "natural window light")
    energy = blueprint_summary.get("energy", "medium")
    hook_style = blueprint_summary.get("hook_style", "casual_share")
    body_framework = blueprint_summary.get("body_framework", "demonstration")
    cta_urgency = blueprint_summary.get("cta_urgency", "soft")
    transcript = blueprint_summary.get("transcript", "")

    prompt = f"""iPhone 13 front facing camera video, filmed vertically for TikTok,
a real young woman not a model, mid-20s, average everyday appearance,
holding {product_description or "the product"} up to show the camera while talking excitedly,

CRITICAL - MUST LOOK REAL NOT AI:
- skin has visible pores especially on nose, natural sebum shine on t-zone
- slight dark circles under eyes, normal human imperfections
- eyes looking at the phone screen not the lens, that typical selfie video eye line
- natural asymmetrical face, one eye slightly different than other
- real hair with flyaways, not perfectly styled

CAMERA FEEL:
- handheld shake from her arm getting tired holding phone up
- slight focus hunting occasionally
- that iPhone front camera slight distortion
- NO stabilization, raw footage feel

ENVIRONMENT:
- {setting}
- {lighting}
- not aesthetically arranged, real life mess

ENERGY:
- {energy} energy level
- genuinely likes the product, not acting
- talking like she's FaceTiming her best friend
- natural umms and pauses, not scripted delivery
- real smile that reaches her eyes

HOOK STYLE: {hook_style}
BODY FRAMEWORK: {body_framework}
CTA: {cta_urgency}

SCRIPT REFERENCE:
"{transcript[:300] if transcript else "Casual product review"}"
"""

    return {
        "prompt": prompt,
        "script": transcript[:200]
        if transcript
        else "Check this out, I've been using this and honestly it's so good!",
    }
