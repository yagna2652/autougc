"""
Select Interactions Node - Clip selection from interaction library.

Matches planned interaction beats to reference clips from the library,
scoring by primitive match, framing preference, and audio quality.
"""

import logging
from typing import Any

from src.pipeline.utils.interaction_library import (
    find_matching_clips,
    load_interaction_library,
)

logger = logging.getLogger(__name__)


def select_interaction_clips_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Select reference clips for each planned interaction beat.

    Scoring per clip:
    - Exact primitive match: required
    - Framing preference match: +30 points
    - High audio quality when audio_emphasis: +25 points
    - Product category match: +10 points

    Args:
        state: Pipeline state with 'interaction_plan' and optionally 'product_category'

    Returns:
        State update with 'selected_interactions' list
    """
    interaction_plan = state.get("interaction_plan", {})
    product_category = state.get("product_category", "mechanical_keyboard_keychain")

    logger.info("Selecting interaction clips from library")

    # Handle empty plan gracefully
    if not interaction_plan or not interaction_plan.get("sequence"):
        logger.info("No interaction plan to select clips for")
        return {
            "selected_interactions": [],
            "current_step": "interactions_selected",
        }

    # Load the library
    library = load_interaction_library()

    if not library:
        logger.warning("Interaction library not available, returning plan-only entries")
        # Return plan entries without clips
        selected = [
            {
                "beat_index": i,
                "planned": beat,
                "clip": None,
                "match_status": "library_unavailable",
            }
            for i, beat in enumerate(interaction_plan.get("sequence", []))
        ]
        return {
            "selected_interactions": selected,
            "current_step": "interactions_selected",
        }

    # Select clips for each beat
    selected_interactions = []

    for i, beat in enumerate(interaction_plan.get("sequence", [])):
        primitive = beat.get("primitive", "")
        framing = beat.get("framing")
        audio_emphasis = beat.get("audio_emphasis", False)

        # Find matching clips
        matches = find_matching_clips(
            library=library,
            primitive=primitive,
            framing_preference=framing,
            audio_emphasis=audio_emphasis,
            product_category=product_category,
        )

        if matches:
            # Take the best match
            best_clip = matches[0]
            selected_interactions.append(
                {
                    "beat_index": i,
                    "planned": beat,
                    "clip": {
                        "id": best_clip.get("id"),
                        "file_path": best_clip.get("file_path"),
                        "duration_s": best_clip.get("duration_s"),
                        "framing": best_clip.get("framing"),
                        "audio_quality": best_clip.get("audio_quality"),
                        "tags": best_clip.get("tags", []),
                        "match_score": best_clip.get("match_score", 0),
                    },
                    "match_status": "matched",
                    "alternatives_count": len(matches) - 1,
                }
            )
            logger.debug(
                f"Beat {i}: matched {best_clip.get('id')} (score: {best_clip.get('match_score')})"
            )
        else:
            # No clip found - include plan-only entry
            selected_interactions.append(
                {
                    "beat_index": i,
                    "planned": beat,
                    "clip": None,
                    "match_status": "no_match",
                    "alternatives_count": 0,
                }
            )
            logger.debug(f"Beat {i}: no matching clip for primitive '{primitive}'")

    # Summary logging
    matched_count = sum(
        1 for s in selected_interactions if s["match_status"] == "matched"
    )
    logger.info(
        f"Selected {matched_count}/{len(selected_interactions)} clips for interaction beats"
    )

    return {
        "selected_interactions": selected_interactions,
        "current_step": "interactions_selected",
    }
