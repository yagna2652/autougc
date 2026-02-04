"""
Analyze Product Node - Claude Vision product analysis for enhanced descriptions.

Uses Claude Vision to analyze product images and generate a rich, detailed
product description automatically. This enhanced description is used downstream
by prompt generation and interaction planning nodes.

Solves the problem of static/generic config.json descriptions not matching
actual product appearance.
"""

import logging
from typing import Any

import anthropic

from src.pipeline.utils import (
    build_error_result,
    get_anthropic_client,
    get_anthropic_client_with_timeout,
    parse_json_response,
    process_image,
)

logger = logging.getLogger(__name__)

# Prompt for product analysis
PRODUCT_ANALYSIS_PROMPT = """Analyze these product images in detail. This description will be used to generate AI videos featuring this product.

Describe:
1. **Physical Appearance**: Exact colors, materials, finish (matte/glossy/translucent)
2. **Dimensions**: Approximate size (compare to common objects like coins, fingers)
3. **Key Components**: What parts are visible? Switches, keycaps, chain, body?
4. **Unique Features**: What makes this product visually distinctive?
5. **Tactile Qualities**: What would it feel/sound like based on appearance?
6. **Best Angles**: Which views showcase the product best?

Format your response as JSON:
{
    "enhanced_description": "A detailed paragraph suitable for video generation prompts, describing the product's exact appearance, colors, materials, size, and distinctive features",
    "visual_features": {
        "colors": ["list of specific colors visible"],
        "materials": ["list of materials (plastic, metal, etc.)"],
        "finish": "matte/glossy/translucent/mixed",
        "size_reference": "size compared to common objects",
        "key_components": ["list of visible parts"],
        "unique_features": ["list of distinctive visual elements"],
        "best_angles": ["list of recommended viewing angles"]
    }
}

Return ONLY valid JSON."""


def analyze_product_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Use Claude Vision to analyze product images and generate
    a detailed product description.

    Sends up to 4 product images to Claude Vision and extracts
    detailed visual features including color, material, size,
    and unique selling points.

    Args:
        state: Pipeline state with 'product_images' list

    Returns:
        State update with 'enhanced_product_description' and 'product_visual_features'
    """
    product_images = state.get("product_images", [])
    existing_description = state.get("product_description", "")

    if not product_images:
        logger.info("No product images provided, skipping product analysis")
        return {
            "enhanced_product_description": existing_description,
            "product_visual_features": {},
            "current_step": "product_analyzed",
        }

    logger.info(f"Analyzing {len(product_images)} product images with Claude Vision")

    # Get Anthropic client
    client, model, error = get_anthropic_client(state, trace_name="analyze_product")
    if error:
        logger.warning(f"{error}, using existing description")
        return {
            "enhanced_product_description": existing_description,
            "product_visual_features": {},
            "current_step": "product_analyzed",
        }

    try:
        # Build the message content with product images
        content = _build_product_analysis_content(product_images, existing_description)

        if not content:
            logger.warning("Failed to build content - no valid product images")
            return {
                "enhanced_product_description": existing_description,
                "product_visual_features": {},
                "current_step": "product_analyzed",
            }

        logger.info(f"Content built with {len(content)} items, calling Claude Vision...")

        # Call Claude Vision with timeout
        api_client = get_anthropic_client_with_timeout(
            timeout_seconds=120.0, connect_timeout=30.0
        )
        if not api_client:
            return {
                "enhanced_product_description": existing_description,
                "product_visual_features": {},
                "current_step": "product_analyzed",
                "error": "ANTHROPIC_API_KEY not set",
            }

        response = api_client.messages.create(
            model=model,
            max_tokens=1500,
            messages=[{"role": "user", "content": content}],
        )

        logger.info("Claude Vision response received for product analysis")

        # Parse response
        response_text = response.content[0].text
        result = parse_json_response(response_text, context="product analysis")

        if not result:
            logger.warning("Could not parse product analysis response")
            return {
                "enhanced_product_description": existing_description,
                "product_visual_features": {},
                "current_step": "product_analyzed",
            }

        enhanced_description = result.get("enhanced_description", existing_description)
        visual_features = result.get("visual_features", {})

        logger.info(f"Product analysis complete: {len(enhanced_description)} char description")

        return {
            "enhanced_product_description": enhanced_description,
            "product_visual_features": visual_features,
            "current_step": "product_analyzed",
        }

    except anthropic.APIError as e:
        logger.error(f"Claude API error during product analysis: {e}")
        # Dynamic fallback to existing_description - can't use standard error handler
        return build_error_result(
            error=e,
            output_fields={
                "enhanced_product_description": existing_description,
                "product_visual_features": {},
            },
            current_step="product_analyzed",
            include_error_field=False,  # Original didn't include error field
        )
    except Exception as e:
        logger.exception("Unexpected error during product analysis")
        # Dynamic fallback to existing_description - can't use standard error handler
        return build_error_result(
            error=e,
            output_fields={
                "enhanced_product_description": existing_description,
                "product_visual_features": {},
            },
            current_step="product_analyzed",
            include_error_field=False,
        )


def _build_product_analysis_content(
    product_images: list[str],
    existing_description: str,
) -> list[dict[str, Any]]:
    """
    Build the content array for Claude Vision API.

    Args:
        product_images: List of product image URLs or base64 data
        existing_description: Existing product description for context

    Returns:
        Content array for Claude API
    """
    content = []

    # Add context about existing description if available
    if existing_description:
        context = f"For context, here's the basic product description: {existing_description}\n\nNow analyze these images to create a much more detailed visual description.\n\n"
    else:
        context = ""

    content.append({"type": "text", "text": context + PRODUCT_ANALYSIS_PROMPT})

    # Add product images (limit to 4 for cost efficiency)
    images_to_analyze = product_images[:4] if len(product_images) > 4 else product_images
    images_added = 0

    for i, image in enumerate(images_to_analyze):
        # Use shared image processing utility with auto-resize
        image_data, media_type = process_image(image, auto_resize=True)
        if image_data:
            content.append(
                {"type": "text", "text": f"\n--- Product Image {i + 1} ---"}
            )
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
            images_added += 1
        else:
            logger.warning(f"Failed to process product image {i + 1}")

    # Check if we got at least one image
    if images_added == 0:
        logger.error("No product images could be processed")
        return []

    logger.info(f"Successfully built content with {images_added} product images")
    return content
