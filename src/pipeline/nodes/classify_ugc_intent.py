"""
Classify UGC Intent Node - Extracts semantic intent/archetype from video analysis.

Takes video analysis and transcription to classify the video into
structured categories (archetype, intent, hook type, narrative structure, etc.)
for more consistent prompt generation.
"""

import json
import logging
import os
from typing import Any

import anthropic

from src.tracing import TracedAnthropicClient, is_tracing_enabled

logger = logging.getLogger(__name__)

# System prompt for classification (scoped to this node only)
CLASSIFICATION_SYSTEM_PROMPT = """You are an expert at analyzing short-form UGC/TikTok selfie videos. Your task is NOT to rewrite or improve. Your task is to classify the example into a small set of semantic intent categories so it can be reliably recreated later. Do not invent facts. If unclear, pick the closest category. Respond ONLY with valid JSON using the specified schema."""

# JSON schema for classification output
CLASSIFICATION_SCHEMA = """{
  "ugc_archetype": "testimonial|problem_solution|casual_review|founder_rant|storytime|unboxing|comparison|educational_tip|other",
  "primary_intent": "build_trust|explain_value|spark_curiosity|normalize_product_use|social_proof|other",
  "hook_type": "relatable_problem|bold_claim|curiosity_gap|emotional_statement|none|other",
  "narrative_structure": "hook_then_story|story_then_reveal|linear_explanation|moment_in_time|list_format|other",
  "trust_mechanism": "personal_experience|specificity|authority|vulnerability|demonstration|social_context|other",
  "cta_style": "soft_mention|implicit|direct_ask|none|other",
  "energy_level": "low|medium|high",
  "authenticity_style": "casual_imperfect|emotional_honesty|matter_of_fact|spontaneous|polished_realism|other",
  "pacing": "slow|medium|fast",
  "script_dependency": "high|medium|low"
}"""


def classify_ugc_intent_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Classify UGC video into semantic intent categories.

    Args:
        state: Pipeline state with 'video_analysis' and optionally 'transcribed_script'

    Returns:
        State update with 'ugc_intent' dict
    """
    video_analysis = state.get("video_analysis", {})
    transcribed_script = state.get("transcribed_script", "")

    if not video_analysis:
        logger.warning("No video analysis provided for classification")
        return {
            "ugc_intent": {},
            "error": "No video analysis to classify",
        }

    logger.info("Classifying UGC intent from video analysis")

    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "ugc_intent": {},
            "error": "ANTHROPIC_API_KEY not set",
        }

    # Initialize client (with tracing if enabled)
    if is_tracing_enabled():
        client = TracedAnthropicClient(api_key=api_key, trace_name="classify_ugc_intent")
    else:
        client = anthropic.Anthropic(api_key=api_key)

    model = state.get("config", {}).get("claude_model", "claude-sonnet-4-20250514")

    try:
        # Build user message
        user_message = _build_classification_request(video_analysis, transcribed_script)

        # Call Claude with low temperature for consistency
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            temperature=0.1,  # Low temperature for deterministic classification
            system=CLASSIFICATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        # Parse response
        response_text = response.content[0].text
        ugc_intent = _parse_classification_response(response_text)

        if not ugc_intent:
            logger.warning("Could not parse classification response, using empty dict")
            return {
                "ugc_intent": {},
                "current_step": "ugc_intent_classified",
                "error": "Classification parsing failed",
            }

        logger.info(f"Classified UGC intent: {ugc_intent.get('ugc_archetype', 'unknown')}")

        return {
            "ugc_intent": ugc_intent,
            "current_step": "ugc_intent_classified",
        }

    except anthropic.APIError as e:
        logger.error(f"Claude API error during classification: {e}")
        return {
            "ugc_intent": {},
            "error": f"Classification API error: {str(e)}",
        }
    except Exception as e:
        logger.exception("Unexpected error during UGC classification")
        return {
            "ugc_intent": {},
            "error": f"Classification failed: {str(e)}",
        }


def _build_classification_request(
    video_analysis: dict[str, Any],
    transcribed_script: str,
) -> str:
    """
    Build the user message for classification request.

    Args:
        video_analysis: Analysis from analyze_video node
        transcribed_script: Transcribed audio (may be empty)

    Returns:
        User message string
    """
    # Format video analysis
    analysis_str = json.dumps(video_analysis, indent=2)

    # Build request
    request = f"""Analyze this UGC/TikTok video and classify it according to the schema below.

## Video Analysis
{analysis_str}

## Transcribed Script
{transcribed_script if transcribed_script else "(No speech detected or transcript unavailable)"}

## Classification Schema
{CLASSIFICATION_SCHEMA}

Respond with ONLY valid JSON matching the schema above. Use snake_case strings. Pick the closest category if unclear."""

    return request


def _parse_classification_response(response_text: str) -> dict[str, Any] | None:
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
        logger.warning(f"Failed to parse classification JSON: {e}")
        return None
