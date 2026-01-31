"""
Analyze Visuals Node - Analyzes video frames using Claude Vision.

This node uses the existing VisualAnalyzer to analyze extracted frames
with Claude Vision API to understand visual style, setting, and composition.
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

logger = logging.getLogger(__name__)


def analyze_visuals_node(state: PipelineState) -> dict[str, Any]:
    """
    Analyze video frames using Claude Vision API.

    This node:
    1. Takes extracted frames (base64 encoded)
    2. Sends them to Claude Vision for analysis
    3. Returns visual style analysis (setting, lighting, composition, etc.)

    Args:
        state: Current pipeline state with frames_base64

    Returns:
        Partial state update with visual_analysis and progress
    """
    from src.analyzer.visual_analyzer import VisualAnalyzer

    frames_base64 = state.get("frames_base64", [])
    frames = state.get("frames", [])

    if not frames_base64 and not frames:
        return mark_failed(state, "No frames available for visual analysis")

    logger.info(f"Analyzing {len(frames_base64 or frames)} frames with Claude Vision")

    try:
        # Update progress
        progress_update = update_progress(state, PipelineStep.ANALYZING_VISUALS, 5)

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

        # Initialize analyzer
        analyzer = VisualAnalyzer(
            api_key=api_key,
            model=claude_model,
        )

        # Use frame paths if base64 not available
        if frames_base64:
            # Analyze using base64 frames
            # Note: VisualAnalyzer.analyze() takes frame paths, so we need to use
            # the frames list. The base64 versions are for other API calls.
            visual_result = analyzer.analyze(frames)
        else:
            visual_result = analyzer.analyze(frames)

        if not visual_result:
            return {
                **progress_update,
                **mark_failed(state, "Visual analysis returned no result"),
            }

        # Convert to dict if it's a Pydantic model
        if hasattr(visual_result, "model_dump"):
            visual_analysis = visual_result.model_dump()
        elif hasattr(visual_result, "dict"):
            visual_analysis = visual_result.dict()
        else:
            visual_analysis = dict(visual_result) if visual_result else {}

        logger.info(
            f"Visual analysis complete: "
            f"setting={visual_analysis.get('setting', 'unknown')}, "
            f"lighting={visual_analysis.get('lighting', 'unknown')}"
        )

        return {
            **progress_update,
            "visual_analysis": visual_analysis,
        }

    except Exception as e:
        logger.exception("Unexpected error during visual analysis")
        return mark_failed(
            state,
            f"Failed to analyze visuals: {str(e)}",
            {"exception_type": type(e).__name__},
        )
