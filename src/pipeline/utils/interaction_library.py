"""
Interaction Library Utilities - Library loading and clip matching.

Provides functions to:
- Load the interaction library index
- Find matching clips for interaction primitives
- Validate interaction plans
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 8 interaction primitives for mechanical keyboard keychain products
INTERACTION_PRIMITIVES = [
    "closeup_click_loop",
    "selfie_click_while_talking",
    "pocket_pull_and_click",
    "desk_idle_click",
    "anxiety_relief_click",
    "sound_showcase_asmr",
    "keychain_dangle_then_click",
    "compare_clicks_variation",
]

# Default library path
DEFAULT_LIBRARY_PATH = Path("assets/interaction_library/index.json")


def load_interaction_library(
    path: str | Path | None = None,
) -> dict[str, Any]:
    """
    Load the interaction library index.

    Args:
        path: Path to index.json. Defaults to assets/interaction_library/index.json

    Returns:
        Library dict with 'clips' and 'primitives_registry', or empty dict on error
    """
    library_path = Path(path) if path else DEFAULT_LIBRARY_PATH

    if not library_path.exists():
        logger.warning(f"Interaction library not found at {library_path}")
        return {}

    try:
        with open(library_path) as f:
            library = json.load(f)

        logger.info(
            f"Loaded interaction library: {len(library.get('clips', []))} clips"
        )
        return library

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse interaction library JSON: {e}")
        return {}
    except Exception as e:
        logger.error(f"Failed to load interaction library: {e}")
        return {}


def find_matching_clips(
    library: dict[str, Any],
    primitive: str,
    framing_preference: str | None = None,
    audio_emphasis: bool = False,
    product_category: str | None = None,
) -> list[dict[str, Any]]:
    """
    Find and score clips matching an interaction primitive.

    Scoring:
    - Exact primitive match: required (clips without match are excluded)
    - Framing preference match: +30 points
    - High audio quality when audio_emphasis: +25 points
    - Product category match: +10 points

    Args:
        library: Loaded interaction library dict
        primitive: Interaction primitive to match (e.g., 'closeup_click_loop')
        framing_preference: Preferred framing (e.g., 'macro_closeup')
        audio_emphasis: Whether audio quality should be prioritized
        product_category: Product category to match (e.g., 'mechanical_keyboard_keychain')

    Returns:
        List of clips sorted by score (highest first), each with added 'match_score' field
    """
    clips = library.get("clips", [])

    if not clips:
        logger.debug("No clips in library")
        return []

    # Filter to matching primitive (required)
    matching_clips = [c for c in clips if c.get("primitive") == primitive]

    if not matching_clips:
        logger.debug(f"No clips found for primitive: {primitive}")
        return []

    # Score each clip
    scored_clips = []
    for clip in matching_clips:
        score = 0

        # Framing preference bonus
        if framing_preference and clip.get("framing") == framing_preference:
            score += 30

        # Audio quality bonus when emphasized
        if audio_emphasis and clip.get("audio_quality") == "high":
            score += 25

        # Product category match bonus
        if product_category and clip.get("product_category") == product_category:
            score += 10

        scored_clip = {**clip, "match_score": score}
        scored_clips.append(scored_clip)

    # Sort by score (highest first)
    scored_clips.sort(key=lambda c: c["match_score"], reverse=True)

    return scored_clips


def validate_interaction_plan(plan: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate an interaction plan against constraints.

    Constraints:
    - 1-3 beats (sequence items)
    - Total duration <= 12 seconds
    - At least one beat must involve clicking

    Args:
        plan: Interaction plan dict with 'sequence' and 'total_duration_s'

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    if not plan:
        return False, ["Empty plan"]

    sequence = plan.get("sequence", [])

    # Check beat count (1-3)
    if not sequence:
        errors.append("Plan has no sequence/beats")
    elif len(sequence) < 1:
        errors.append("Plan must have at least 1 beat")
    elif len(sequence) > 3:
        errors.append(f"Plan has {len(sequence)} beats (max 3)")

    # Check total duration
    total_duration = plan.get("total_duration_s", 0)
    if total_duration > 12:
        errors.append(f"Total duration {total_duration}s exceeds 12s limit")
    elif total_duration <= 0:
        errors.append("Total duration must be positive")

    # Check for clicking beat
    clicking_primitives = {
        "closeup_click_loop",
        "selfie_click_while_talking",
        "pocket_pull_and_click",
        "desk_idle_click",
        "anxiety_relief_click",
        "sound_showcase_asmr",
        "compare_clicks_variation",
    }

    has_clicking = any(
        beat.get("primitive") in clicking_primitives for beat in sequence
    )
    if not has_clicking and sequence:
        errors.append("Plan must include at least one clicking beat")

    # Validate each beat has required fields
    for i, beat in enumerate(sequence):
        if not beat.get("primitive"):
            errors.append(f"Beat {i+1} missing 'primitive'")
        elif beat["primitive"] not in INTERACTION_PRIMITIVES:
            errors.append(f"Beat {i+1} has unknown primitive: {beat['primitive']}")

        if not beat.get("duration_s"):
            errors.append(f"Beat {i+1} missing 'duration_s'")

    is_valid = len(errors) == 0
    return is_valid, errors
