"""
Analyze Product Node - Analyzes product images using Claude Vision.

This node uses Claude Vision API to analyze product images and understand:
- Product type and category
- Key features and characteristics
- Best ways to showcase the product in a UGC video

All LLM calls are traced via LangSmith for full prompt observability.
"""

import logging
import os
from typing import Any

from src.pipeline.state import (
    PipelineState,
    PipelineStep,
    ProductAnalysis,
    mark_failed,
    update_progress,
)
from src.tracing import TracedAnthropicClient, is_tracing_enabled

logger = logging.getLogger(__name__)


def analyze_product_node(state: PipelineState) -> dict[str, Any]:
    """
    Analyze product images using Claude Vision API.

    This node:
    1. Takes product images (base64 encoded)
    2. Sends them to Claude Vision for analysis
    3. Returns product analysis (type, features, showcase suggestions)

    Args:
        state: Current pipeline state with product_images

    Returns:
        Partial state update with product_analysis and progress
    """
    import anthropic

    product_images = state.get("product_images", [])
    product_description = state.get("product_description", "")
    product_context = state.get("product_context", {})

    # If no product images, skip this node but don't fail
    if not product_images:
        logger.info("No product images provided, skipping product analysis")
        return {
            **update_progress(state, PipelineStep.ANALYZING_PRODUCT, 7),
            "product_analysis": {},
        }

    logger.info(f"Analyzing {len(product_images)} product images with Claude Vision")

    try:
        # Update progress
        progress_update = update_progress(state, PipelineStep.ANALYZING_PRODUCT, 7)

        # Get config
        config = state.get("config", {})
        claude_model = config.get("claude_model", "claude-sonnet-4-20250514")

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

        # Initialize Anthropic client (with tracing if enabled)
        if is_tracing_enabled():
            client = TracedAnthropicClient(
                api_key=api_key, trace_name="analyze_product"
            )
        else:
            client = anthropic.Anthropic(api_key=api_key)

        # Build image content for Claude
        image_content = _build_image_content(product_images)

        if not image_content:
            logger.warning("Could not process any product images")
            return {
                **progress_update,
                "product_analysis": {},
            }

        # Build product context info for the prompt
        context_info = _build_context_info(product_description, product_context)

        # Build the analysis prompt
        prompt = _build_analysis_prompt(context_info)

        # Call Claude Vision API
        response = client.messages.create(
            model=claude_model,
            max_tokens=1500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        *image_content,
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )

        # Extract text response
        response_text = response.content[0].text if response.content else ""

        # Parse the JSON response
        analysis_result = _parse_analysis_response(response_text)

        if not analysis_result:
            logger.warning("Could not parse product analysis response")
            return {
                **progress_update,
                "product_analysis": {},
            }

        # Convert to ProductAnalysis TypedDict
        product_analysis: ProductAnalysis = {
            "type": analysis_result.get("type", "unknown"),
            "description": analysis_result.get("description", ""),
            "key_features": analysis_result.get("keyFeatures", []),
            "suggested_showcase": analysis_result.get("suggestedShowcase", ""),
        }

        logger.info(
            f"Product analysis complete: type={product_analysis.get('type')}, "
            f"features={len(product_analysis.get('key_features', []))}"
        )

        return {
            **progress_update,
            "product_analysis": product_analysis,
        }

    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        return mark_failed(
            state,
            f"Claude API error: {str(e)}",
            {"status_code": getattr(e, "status_code", None)},
        )

    except Exception as e:
        logger.exception("Unexpected error during product analysis")
        return mark_failed(
            state,
            f"Failed to analyze product: {str(e)}",
            {"exception_type": type(e).__name__},
        )


def _build_image_content(
    product_images: list[str],
) -> list[dict[str, Any]]:
    """
    Build image content blocks for Claude API.

    Args:
        product_images: List of base64-encoded images or URLs

    Returns:
        List of image content blocks for Claude API
    """
    image_content = []

    for i, image in enumerate(product_images[:3]):  # Limit to 3 images
        try:
            if image.startswith("data:"):
                # Extract media type and data from data URL
                parts = image.split(";base64,")
                if len(parts) == 2:
                    media_type = parts[0].replace("data:", "")
                    image_data = parts[1]

                    # Validate media type
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
                # URL-based image
                image_content.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "url",
                            "url": image,
                        },
                    }
                )
            else:
                # Assume raw base64
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
            logger.warning(f"Failed to process product image {i}: {e}")
            continue

    return image_content


def _build_context_info(
    product_description: str,
    product_context: dict[str, Any],
) -> str:
    """
    Build context information string from product description and context.

    Args:
        product_description: User-provided product description
        product_context: Rich product context dict

    Returns:
        Formatted context string
    """
    parts = []

    if product_description:
        parts.append(f"Product description: {product_description}")

    if product_context:
        if product_context.get("type"):
            parts.append(f"Product type: {product_context['type']}")

        if product_context.get("interactions"):
            interactions = ", ".join(product_context["interactions"])
            parts.append(f"Key interactions: {interactions}")

        if product_context.get("tactile_features"):
            features = ", ".join(product_context["tactile_features"])
            parts.append(f"Tactile features: {features}")

        if product_context.get("sound_features"):
            sounds = ", ".join(product_context["sound_features"])
            parts.append(f"Sound features: {sounds}")

        if product_context.get("size_description"):
            parts.append(f"Size: {product_context['size_description']}")

        if product_context.get("highlight_feature"):
            parts.append(
                f"Key feature to highlight: {product_context['highlight_feature']}"
            )

        if product_context.get("custom_instructions"):
            parts.append(
                f"Additional context: {product_context['custom_instructions']}"
            )

    return "\n".join(parts) if parts else ""


def _build_analysis_prompt(context_info: str) -> str:
    """
    Build the product analysis prompt for Claude.

    Args:
        context_info: Product context information

    Returns:
        Complete prompt string
    """
    context_section = ""
    if context_info:
        context_section = f"""
User-provided information about this product:
{context_info}
"""

    return f"""Analyze the product image(s) provided and identify:

1. What type of product this is
2. A detailed description of the product
3. Key features visible in the image
4. The best way to showcase this product in a UGC-style TikTok video

{context_section}

Respond in this exact JSON format:
{{
  "type": "the product type/category",
  "description": "detailed description of the product based on the image",
  "keyFeatures": ["feature1", "feature2", "feature3"],
  "suggestedShowcase": "how to best show this product in a UGC video"
}}

Return ONLY valid JSON, no other text."""


def _parse_analysis_response(response_text: str) -> dict[str, Any] | None:
    """
    Parse the JSON response from Claude.

    Args:
        response_text: Raw response text from Claude

    Returns:
        Parsed dict or None if parsing fails
    """
    import json

    if not response_text:
        return None

    try:
        # Try to extract JSON from response
        # Sometimes Claude includes extra text before/after JSON
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start != -1 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)

        # Try direct parsing
        return json.loads(response_text)

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON response: {e}")
        return None
