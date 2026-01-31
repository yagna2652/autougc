"""
Generate Mechanics Node - Enhances prompts with detailed human mechanics.

This node uses the existing MechanicsEngine to transform base prompts into
detailed mechanics-enhanced prompts that include specific instructions for:
- Hand movements and product interactions
- Facial expressions and micro-expressions
- Eye movements and gaze patterns
- Body posture and natural movements
- Product reveal and demonstration timing
"""

import logging
from typing import Any

from src.pipeline.state import (
    PipelineState,
    PipelineStep,
    update_progress,
)

logger = logging.getLogger(__name__)


def generate_mechanics_node(state: PipelineState) -> dict[str, Any]:
    """
    Generate mechanics-enhanced prompt from blueprint and base prompt.

    This node:
    1. Takes the blueprint and base prompt from previous nodes
    2. Uses MechanicsEngine to generate detailed human mechanics
    3. Returns an enhanced prompt with mechanics timeline

    Args:
        state: Current pipeline state with blueprint and base_prompt

    Returns:
        Partial state update with mechanics_prompt, mechanics_timeline, and progress
    """
    from src.mechanics import MechanicsEngine, ProductContext, VideoConfig
    from src.models.blueprint import VideoBlueprint

    blueprint_dict = state.get("blueprint", {})
    base_prompt = state.get("base_prompt", "")
    product_context = state.get("product_context", {})

    # Check if mechanics should be enabled
    config = state.get("config", {})
    enable_mechanics = config.get("enable_mechanics", True)

    if not enable_mechanics:
        logger.info("Mechanics generation disabled, skipping")
        return {
            **update_progress(state, PipelineStep.GENERATING_MECHANICS, 9),
            "mechanics_prompt": "",
            "mechanics_timeline": {},
        }

    if not blueprint_dict:
        logger.warning("No blueprint available for mechanics generation")
        return {
            **update_progress(state, PipelineStep.GENERATING_MECHANICS, 9),
            "mechanics_prompt": "",
            "mechanics_timeline": {},
        }

    logger.info("Generating mechanics-enhanced prompt")

    try:
        # Update progress
        progress_update = update_progress(state, PipelineStep.GENERATING_MECHANICS, 9)

        # Get config values
        product_category = config.get("product_category", "general")
        target_duration = config.get("target_duration", 8.0)
        energy_level = config.get("energy_level", "medium")

        # Convert product_context dict to ProductContext model if provided
        product_ctx = None
        if product_context:
            product_ctx = ProductContext(
                type=product_context.get("type", ""),
                interactions=product_context.get("interactions", []),
                tactile_features=product_context.get("tactile_features", []),
                sound_features=product_context.get("sound_features", []),
                size_description=product_context.get("size_description", ""),
                highlight_feature=product_context.get("highlight_feature", ""),
                custom_instructions=product_context.get("custom_instructions", ""),
            )

        # Create video config
        video_config = VideoConfig(
            duration=target_duration,
            has_product=True,
            product_category=product_category,
            product_context=product_ctx,
            energy_level=energy_level,
        )

        # Initialize mechanics engine
        engine = MechanicsEngine(video_config)

        # Try to parse blueprint into VideoBlueprint model
        try:
            blueprint = VideoBlueprint.model_validate(blueprint_dict)
        except Exception as e:
            logger.warning(f"Could not validate blueprint model: {e}")
            # Try to generate from style parameters instead
            return _generate_from_style(
                state, engine, base_prompt, config, progress_update
            )

        # Generate mechanics-enhanced prompt
        mechanics_prompt = engine.generate_mechanics_prompt(
            blueprint=blueprint,
            base_prompt=base_prompt,
            product_category=product_category,
            target_duration=target_duration,
        )

        # Get the mechanics timeline for debugging/visualization
        try:
            timeline = engine.generate_timeline(blueprint)
            mechanics_timeline = timeline.model_dump() if timeline else {}
        except Exception as e:
            logger.warning(f"Could not generate mechanics timeline: {e}")
            mechanics_timeline = {}

        if not mechanics_prompt:
            logger.warning("Mechanics engine returned empty prompt")
            return {
                **progress_update,
                "mechanics_prompt": "",
                "mechanics_timeline": {},
            }

        logger.info(f"Mechanics prompt generated: {len(mechanics_prompt)} characters")

        return {
            **progress_update,
            "mechanics_prompt": mechanics_prompt,
            "mechanics_timeline": mechanics_timeline,
        }

    except ImportError as e:
        logger.warning(f"MechanicsEngine not available: {e}")
        return {
            **update_progress(state, PipelineStep.GENERATING_MECHANICS, 9),
            "mechanics_prompt": "",
            "mechanics_timeline": {},
        }

    except Exception as e:
        logger.exception("Unexpected error generating mechanics")
        # Don't fail the pipeline, just skip mechanics
        return {
            **update_progress(state, PipelineStep.GENERATING_MECHANICS, 9),
            "mechanics_prompt": "",
            "mechanics_timeline": {},
            "error": f"Mechanics generation warning: {str(e)}",
        }


def _generate_from_style(
    state: PipelineState,
    engine: Any,
    base_prompt: str,
    config: dict[str, Any],
    progress_update: dict[str, Any],
) -> dict[str, Any]:
    """
    Fallback: Generate mechanics from style parameters when blueprint parsing fails.

    Args:
        state: Current pipeline state
        engine: MechanicsEngine instance
        base_prompt: Base prompt to enhance
        config: Pipeline configuration
        progress_update: Progress update dict

    Returns:
        Partial state update with mechanics_prompt
    """
    blueprint_summary = state.get("blueprint_summary", {})

    # Map blueprint summary to style parameters
    hook_style = _map_hook_style(blueprint_summary.get("hook_style", "casual_share"))
    body_framework = _map_body_framework(
        blueprint_summary.get("body_framework", "demonstration")
    )
    cta_style = _map_cta_style(blueprint_summary.get("cta_urgency", "soft"))

    try:
        mechanics_prompt = engine.generate_from_config(
            hook_style=hook_style,
            body_framework=body_framework,
            cta_style=cta_style,
            product_category=config.get("product_category", "general"),
            duration=config.get("target_duration", 8.0),
            base_prompt=base_prompt,
        )

        logger.info(
            f"Mechanics prompt generated from style: {len(mechanics_prompt)} characters"
        )

        return {
            **progress_update,
            "mechanics_prompt": mechanics_prompt,
            "mechanics_timeline": {},
        }

    except Exception as e:
        logger.warning(f"Failed to generate mechanics from style: {e}")
        return {
            **progress_update,
            "mechanics_prompt": "",
            "mechanics_timeline": {},
        }


def _map_hook_style(blueprint_style: str) -> str:
    """Map blueprint hook style to mechanics template name."""
    style_mapping = {
        "pov_trend": "pov_storytelling",
        "revelation": "curiosity_hook",
        "question": "curiosity_hook",
        "controversial": "curiosity_hook",
        "story_start": "pov_storytelling",
        "curiosity_gap": "curiosity_hook",
        "pattern_interrupt": "product_reveal",
        "relatable": "casual_share",
        "shock": "product_reveal",
        "other": "casual_share",
    }
    return style_mapping.get(blueprint_style.lower(), "casual_share")


def _map_body_framework(blueprint_framework: str) -> str:
    """Map blueprint body framework to mechanics template name."""
    framework_mapping = {
        "testimonial": "testimonial",
        "education": "education",
        "problem_agitation": "demonstration",
        "demonstration": "demonstration",
        "social_proof": "testimonial",
        "storytelling": "testimonial",
        "comparison": "comparison",
        "tutorial": "education",
        "behind_the_scenes": "demonstration",
        "other": "demonstration",
    }
    return framework_mapping.get(blueprint_framework.lower(), "demonstration")


def _map_cta_style(blueprint_urgency: str) -> str:
    """Map blueprint CTA urgency to mechanics template name."""
    urgency_mapping = {
        "soft": "soft_recommendation",
        "medium": "soft_recommendation",
        "urgent": "urgent_action",
        "fomo": "urgent_action",
        "discount": "urgent_action",
        "curiosity": "curious_tease",
        "direct": "urgent_action",
    }
    return urgency_mapping.get(blueprint_urgency.lower(), "soft_recommendation")
