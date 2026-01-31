"""
Finalize Prompt Node - Selects the best prompt for video generation.

This node is the critical junction that ensures the enhanced mechanics prompt
is used when available, falling back to the base prompt otherwise. This fixes
the plumbing issue where mechanics prompts were being generated but ignored.
"""

import logging
from typing import Any

from src.pipeline.state import (
    PipelineState,
    PipelineStep,
    update_progress,
)

logger = logging.getLogger(__name__)


def finalize_prompt_node(state: PipelineState) -> dict[str, Any]:
    """
    Select the best prompt for video generation.

    This node:
    1. Checks if mechanics_prompt is available and non-empty
    2. Falls back to base_prompt if mechanics not available
    3. Sets final_prompt which is used by video generation

    IMPORTANT: This node fixes the plumbing issue where mechanics prompts
    were being generated but not used. The final_prompt is what gets sent
    to the video generation API.

    Priority order:
    1. mechanics_prompt (if enabled and available)
    2. base_prompt (fallback)
    3. Template-based prompt (last resort)

    Args:
        state: Current pipeline state with base_prompt and mechanics_prompt

    Returns:
        Partial state update with final_prompt and progress
    """
    base_prompt = state.get("base_prompt", "")
    mechanics_prompt = state.get("mechanics_prompt", "")
    config = state.get("config", {})
    enable_mechanics = config.get("enable_mechanics", True)

    logger.info("Finalizing prompt for video generation")

    try:
        # Update progress
        progress_update = update_progress(state, PipelineStep.FINALIZING_PROMPT, 10)

        # Determine which prompt to use
        final_prompt = ""
        prompt_source = ""

        if enable_mechanics and mechanics_prompt and mechanics_prompt.strip():
            # Use mechanics-enhanced prompt (preferred)
            final_prompt = mechanics_prompt
            prompt_source = "mechanics"
            logger.info(f"Using mechanics-enhanced prompt ({len(final_prompt)} chars)")
        elif base_prompt and base_prompt.strip():
            # Fall back to base prompt
            final_prompt = base_prompt
            prompt_source = "base"
            logger.info(f"Using base prompt ({len(final_prompt)} chars)")
        else:
            # Last resort: generate a minimal template prompt
            final_prompt = _generate_fallback_prompt(state)
            prompt_source = "fallback"
            logger.warning(
                f"Using fallback template prompt ({len(final_prompt)} chars)"
            )

        # Validate prompt is not empty
        if not final_prompt or not final_prompt.strip():
            logger.error("No valid prompt available for video generation")
            return {
                **progress_update,
                "final_prompt": "",
                "error": "No valid prompt available for video generation",
            }

        # Log prompt stats for debugging
        _log_prompt_stats(base_prompt, mechanics_prompt, final_prompt, prompt_source)

        return {
            **progress_update,
            "final_prompt": final_prompt,
            # Store metadata about which prompt was used
            "prompt_metadata": {
                "source": prompt_source,
                "base_prompt_length": len(base_prompt) if base_prompt else 0,
                "mechanics_prompt_length": len(mechanics_prompt)
                if mechanics_prompt
                else 0,
                "final_prompt_length": len(final_prompt),
                "mechanics_enabled": enable_mechanics,
            },
        }

    except Exception as e:
        logger.exception("Unexpected error finalizing prompt")
        # Try to return something usable
        fallback = base_prompt or mechanics_prompt or _generate_fallback_prompt(state)
        return {
            **update_progress(state, PipelineStep.FINALIZING_PROMPT, 10),
            "final_prompt": fallback,
            "error": f"Warning: Error finalizing prompt: {str(e)}",
        }


def _generate_fallback_prompt(state: PipelineState) -> str:
    """
    Generate a minimal fallback prompt when all else fails.

    Args:
        state: Current pipeline state

    Returns:
        Basic video generation prompt
    """
    product_description = state.get("product_description", "")
    blueprint_summary = state.get("blueprint_summary", {})

    setting = blueprint_summary.get("setting", "bedroom")
    lighting = blueprint_summary.get("lighting", "natural window light")
    energy = blueprint_summary.get("energy", "medium")

    product_text = f"holding {product_description}" if product_description else ""

    return f"""iPhone front camera selfie video, filmed vertically for TikTok,
a real young woman in her mid-20s {product_text},
natural {setting} setting with {lighting},
{energy} energy, talking casually to camera,
real skin texture, handheld camera shake,
looking at phone screen not camera lens,
genuine authentic UGC style, not polished or professional."""


def _log_prompt_stats(
    base_prompt: str,
    mechanics_prompt: str,
    final_prompt: str,
    prompt_source: str,
) -> None:
    """
    Log detailed prompt statistics for debugging.

    Args:
        base_prompt: The base prompt
        mechanics_prompt: The mechanics-enhanced prompt
        final_prompt: The selected final prompt
        prompt_source: Which prompt was selected
    """
    stats = {
        "source": prompt_source,
        "base_chars": len(base_prompt) if base_prompt else 0,
        "mechanics_chars": len(mechanics_prompt) if mechanics_prompt else 0,
        "final_chars": len(final_prompt) if final_prompt else 0,
    }

    # Check if mechanics added significant content
    if base_prompt and mechanics_prompt:
        added_chars = len(mechanics_prompt) - len(base_prompt)
        stats["mechanics_added_chars"] = added_chars
        stats["mechanics_expansion_ratio"] = (
            round(len(mechanics_prompt) / len(base_prompt), 2)
            if len(base_prompt) > 0
            else 0
        )

    logger.debug(f"Prompt selection stats: {stats}")

    # Warn if mechanics was supposed to be used but wasn't
    if prompt_source == "base" and mechanics_prompt:
        logger.warning(
            f"Mechanics prompt was available ({len(mechanics_prompt)} chars) "
            "but base prompt was selected. Check enable_mechanics config."
        )
