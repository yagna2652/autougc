"""
Distill Prompt Node - Rewrites creative prompts for optimal video model output.

Takes the creative video prompt from generate_prompt and rewrites it into a
model-optimized format. Video models are physics simulators, not story
interpreters — this node enforces mechanical language, sequential actions,
simplified camera, and tight word budgets.

The original prompt is preserved as 'original_video_prompt' for A/B comparison.
"""

import logging
import time
from typing import Any

from src.pipeline.utils import get_openrouter_client, handle_unexpected_error

logger = logging.getLogger(__name__)

_ERROR_DEFAULTS = {"video_prompt": ""}

DISTILLATION_SYSTEM_PROMPT = """You are a video generation prompt optimizer. You rewrite creative video prompts into a format that produces the best results from AI video generation models (Kling-v3, Sora).

VIDEO MODELS ARE PHYSICS SIMULATORS, NOT STORY INTERPRETERS.

Rules — apply ALL of these:

1. SERIALIZE ACTIONS: Convert any simultaneous/parallel actions into strict sequential order. Use "first... then... next... finally" structure. One finger/hand action at a time.

2. MECHANICAL LANGUAGE ONLY: Replace all emotional, mood, or vibe language with physics descriptions. "Delightful rhythm" → delete. "Presses down, sinks into housing, springs back" → keep. The model renders forces and displacements, not feelings.

3. EXPAND NAMED PATTERNS: If the prompt contains named interaction moves (e.g. "Fidget Wave", "Anxious Crunch", "Absentminded Hold"), replace the name with the literal mechanical description of what the fingers/hands do.

4. SIMPLIFY CAMERA: Camera instructions = [verb] + [direction] + [magnitude]. "Pushes in slightly." "Pans left." No intent, no justification, no narrative framing. One camera move per beat max.

5. MAX 5 NEGATIVE CONSTRAINTS: If DO NOT SHOW has more than 5 items, keep only the 5 most important (prioritize hand/finger positioning and device orientation constraints).

6. MAX 2-3 BEATS per 5 seconds: If the prompt describes more than 3 distinct actions, keep the first 2-3 and drop the rest.

7. WORD BUDGET: Keep action description under ~120 words. Trim from the end if needed.

8. PRESERVE SPATIAL SETUP: Keep the opening spatial/orientation description (how the device is held, which hand, chain position) exactly as written.

9. PRESERVE ELEMENT TOKENS: If the prompt contains @Element1, @Element2, @Image1 etc., keep them exactly as-is. These are API references that the video model needs.

Output ONLY the rewritten prompt. No commentary, no explanation."""


def distill_prompt_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Distill the creative video prompt into a model-optimized format.

    Preserves the original prompt as 'original_video_prompt' and overwrites
    'video_prompt' with the distilled version.

    Args:
        state: Pipeline state with 'video_prompt' from generate_prompt

    Returns:
        State update with 'original_video_prompt' and distilled 'video_prompt'
    """
    video_prompt = state.get("video_prompt", "")

    if not video_prompt or not video_prompt.strip():
        logger.warning("distill_prompt: skipping — empty video_prompt")
        return {
            "original_video_prompt": "",
            "current_step": "prompt_distilled",
        }

    logger.info(f"    ↳ Distilling prompt ({len(video_prompt)} chars)")

    # Get OpenRouter client — text model is sufficient for rewriting
    client, model, error = get_openrouter_client(
        state, trace_name="distill_prompt", model_type="text"
    )
    if error:
        # Non-fatal: keep original prompt and continue
        logger.warning(f"distill_prompt: LLM unavailable ({error}), keeping original prompt")
        return {
            "original_video_prompt": video_prompt,
            "current_step": "prompt_distilled",
        }

    try:
        t0 = time.time()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": DISTILLATION_SYSTEM_PROMPT},
                {"role": "user", "content": video_prompt},
            ],
        )
        elapsed = time.time() - t0

        # Check for API errors
        if hasattr(response, "error") and response.error:
            error_msg = response.error.get("message", "Unknown error")
            logger.warning(f"distill_prompt: API error ({error_msg}), keeping original prompt")
            return {
                "original_video_prompt": video_prompt,
                "current_step": "prompt_distilled",
            }

        if not response.choices or not response.choices[0].message:
            logger.warning("distill_prompt: empty response, keeping original prompt")
            return {
                "original_video_prompt": video_prompt,
                "current_step": "prompt_distilled",
            }

        distilled = (response.choices[0].message.content or "").strip()

        # Validate distilled prompt isn't empty or too short
        if not distilled or len(distilled) < 50:
            logger.warning(f"distill_prompt: result too short ({len(distilled)} chars), keeping original")
            return {
                "original_video_prompt": video_prompt,
                "current_step": "prompt_distilled",
            }

        logger.info(f"    ↳ Distilled: {len(video_prompt)} → {len(distilled)} chars ({elapsed:.1f}s)")
        logger.info(f"    ↳ Preview: {distilled[:100]}...")

        return {
            "original_video_prompt": video_prompt,
            "video_prompt": distilled,
            "current_step": "prompt_distilled",
        }

    except Exception as e:
        logger.warning(f"distill_prompt: exception ({e}), keeping original prompt")
        # Non-fatal: preserve original and continue
        return {
            "original_video_prompt": video_prompt,
            "current_step": "prompt_distilled",
        }
