"""
Plan Interactions Node - Claude-powered interaction sequence planning.

Plans mechanically plausible interaction sequences for fidget/click products
(mechanical keyboard keychains) based on UGC intent and product context.

Core Concept - Mechanics Integrity:
- Rigid/consistent object shape (no warping)
- Consistent clicking motion (finger down/up travel)
- Plausible hand grip for small keychain
- Close-up framing to show the click
- Sound emphasis (ASMR-like click)
"""

import json
import logging
import os
from typing import Any

import anthropic

from src.pipeline.utils.interaction_library import (
    INTERACTION_PRIMITIVES,
    validate_interaction_plan,
)
from src.tracing import TracedAnthropicClient, is_tracing_enabled

logger = logging.getLogger(__name__)

# System prompt for interaction planning
PLANNING_SYSTEM_PROMPT = """You are a UGC director specializing in fidget products like mechanical keyboard keychains. Your task is to plan a short, mechanically plausible interaction sequence that showcases the product's tactile/auditory appeal.

CORE PRINCIPLES (Mechanics Integrity):
- Rigid/consistent object shape (no warping)
- Consistent clicking motion (finger down/up travel)
- Plausible hand grip for small keychain
- Close-up framing to show the click clearly
- Sound emphasis (ASMR-like click satisfaction)

AVAILABLE INTERACTION PRIMITIVES:
1. closeup_click_loop - Macro shot of fingers clicking in loop (ideal: macro_closeup)
2. selfie_click_while_talking - Talking head while casually clicking (ideal: selfie_medium)
3. pocket_pull_and_click - Pull from pocket, start clicking (ideal: close)
4. desk_idle_click - Top-down desk view, clicking while working (ideal: desk_topdown)
5. anxiety_relief_click - Stress relief through clicking (ideal: close)
6. sound_showcase_asmr - ASMR-style sound focus (ideal: macro_closeup)
7. keychain_dangle_then_click - Show dangling, then click (ideal: close)
8. compare_clicks_variation - Different click styles/speeds (ideal: macro_closeup)

PLANNING RULES:
- Always include at least one beat that clearly shows clicking
- If script_dependency is "low", prefer macro_closeup framing
- If ugc_archetype is "testimonial" or "storytime", include selfie_click_while_talking
- If audio_emphasis is requested, prefer sound_showcase_asmr or closeup_click_loop
- Keep total sequence to 1-3 beats
- Keep total duration under 12 seconds

Respond ONLY with valid JSON matching the specified schema."""

# JSON schema for plan output
PLAN_OUTPUT_SCHEMA = """{
  "sequence": [
    {
      "primitive": "one of the 8 primitives above",
      "duration_s": 3.0,
      "framing": "macro_closeup|selfie_medium|close|desk_topdown",
      "audio_emphasis": true|false,
      "notes": "Brief direction note"
    }
  ],
  "total_duration_s": 9.0,
  "key_mechanics_notes": "Overall mechanical/physical considerations for the sequence"
}"""


def plan_interactions_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Plan interaction sequence based on UGC intent and product context.

    Args:
        state: Pipeline state with 'ugc_intent', 'product_description',
               'product_category', and optionally 'interaction_constraints'

    Returns:
        State update with 'interaction_plan' dict
    """
    ugc_intent = state.get("ugc_intent", {})
    product_description = state.get("product_description", "")
    product_category = state.get("product_category", "mechanical_keyboard_keychain")
    interaction_constraints = state.get("interaction_constraints", {})

    logger.info("Planning interaction sequence")

    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set, returning empty plan")
        return {
            "interaction_plan": {},
            "current_step": "interactions_planned",
        }

    # Initialize client (with tracing if enabled)
    if is_tracing_enabled():
        client = TracedAnthropicClient(api_key=api_key, trace_name="plan_interactions")
    else:
        client = anthropic.Anthropic(api_key=api_key)

    model = state.get("config", {}).get("claude_model", "claude-sonnet-4-20250514")

    try:
        # Build user message
        user_message = _build_planning_request(
            ugc_intent=ugc_intent,
            product_description=product_description,
            product_category=product_category,
            interaction_constraints=interaction_constraints,
        )

        # Call Claude with low temperature for consistency
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            temperature=0.2,  # Low temperature for consistent planning
            system=PLANNING_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        # Parse response
        response_text = response.content[0].text
        interaction_plan = _parse_plan_response(response_text)

        if not interaction_plan:
            logger.warning("Could not parse interaction plan, using empty dict")
            return {
                "interaction_plan": {},
                "current_step": "interactions_planned",
            }

        # Validate the plan
        is_valid, errors = validate_interaction_plan(interaction_plan)
        if not is_valid:
            logger.warning(f"Invalid interaction plan: {errors}")
            # Still return the plan, but log the issues
            interaction_plan["validation_warnings"] = errors

        logger.info(
            f"Planned {len(interaction_plan.get('sequence', []))} interaction beats"
        )

        return {
            "interaction_plan": interaction_plan,
            "current_step": "interactions_planned",
        }

    except anthropic.APIError as e:
        logger.error(f"Claude API error during interaction planning: {e}")
        return {
            "interaction_plan": {},
            "current_step": "interactions_planned",
        }
    except Exception as e:
        logger.exception("Unexpected error during interaction planning")
        return {
            "interaction_plan": {},
            "current_step": "interactions_planned",
        }


def _build_planning_request(
    ugc_intent: dict[str, Any],
    product_description: str,
    product_category: str,
    interaction_constraints: dict[str, Any],
) -> str:
    """
    Build the user message for planning request.

    Args:
        ugc_intent: Classification from classify_ugc_intent node
        product_description: Product description text
        product_category: Product category string
        interaction_constraints: Optional constraints dict

    Returns:
        User message string
    """
    # Format UGC intent
    intent_str = json.dumps(ugc_intent, indent=2) if ugc_intent else "Not available"

    # Format constraints
    constraints_str = (
        json.dumps(interaction_constraints, indent=2)
        if interaction_constraints
        else "None specified"
    )

    request = f"""Plan an interaction sequence for this fidget product video.

## Product Information
Category: {product_category}
Description: {product_description or "Mechanical keyboard keychain fidget clicker"}

## UGC Intent Classification
{intent_str}

## Interaction Constraints
{constraints_str}

## Output Schema
{PLAN_OUTPUT_SCHEMA}

Plan a 1-3 beat sequence (total <=12s) that:
1. Showcases the clicking/tactile appeal
2. Matches the UGC archetype and intent
3. Maintains mechanical plausibility
4. Emphasizes sound if appropriate

Respond with ONLY valid JSON matching the schema above."""

    return request


def _parse_plan_response(response_text: str) -> dict[str, Any] | None:
    """
    Parse the JSON response from Claude.

    Args:
        response_text: Raw response text

    Returns:
        Parsed dict or None if parsing fails
    """
    if not response_text:
        return None

    try:
        # Try direct JSON parse first
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass

    # Fallback: find first JSON object in response
    try:
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start != -1 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)

        return None

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse interaction plan JSON: {e}")
        return None
