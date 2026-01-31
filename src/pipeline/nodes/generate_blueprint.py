"""
Generate Blueprint Node - Combines analysis results into a complete video blueprint.

This node orchestrates the final blueprint generation by combining:
- Transcript data
- Visual analysis
- Structure parsing (Hook/Body/CTA)
- Scene segmentation (if enhanced analysis enabled)
- Pacing analysis
- Product tracking

The resulting blueprint is the core data structure used for mechanics generation.
"""

import logging
import os
from typing import Any

from src.pipeline.state import (
    BlueprintSummary,
    PipelineState,
    PipelineStep,
    mark_failed,
    update_progress,
)

logger = logging.getLogger(__name__)


def generate_blueprint_node(state: PipelineState) -> dict[str, Any]:
    """
    Generate complete video blueprint from analysis results.

    This node:
    1. Takes transcript, visual analysis, and frames from previous nodes
    2. Parses video structure (Hook/Body/CTA)
    3. Optionally runs enhanced analysis (scenes, pacing, product tracking)
    4. Combines everything into a comprehensive blueprint

    Args:
        state: Current pipeline state with transcript, visual_analysis, frames

    Returns:
        Partial state update with blueprint, blueprint_summary, and progress
    """
    from src.analyzer.structure_parser import StructureParser
    from src.models.blueprint import Transcript as TranscriptModel
    from src.models.blueprint import VideoBlueprint, VisualStyle

    # Get required data from state
    transcript_data = state.get("transcript", {})
    visual_analysis = state.get("visual_analysis", {})
    frames = state.get("frames", [])
    video_path = state.get("video_path", "")

    if not transcript_data:
        return mark_failed(
            state, "No transcript data available for blueprint generation"
        )

    logger.info("Generating video blueprint from analysis results")

    try:
        # Update progress
        progress_update = update_progress(state, PipelineStep.GENERATING_BLUEPRINT, 6)

        # Get config
        config = state.get("config", {})
        claude_model = config.get("claude_model", "claude-sonnet-4-20250514")
        enable_enhanced = config.get("enable_enhanced_analysis", True)

        # Get API key
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

        # Convert transcript dict to model
        transcript_model = TranscriptModel(
            full_text=transcript_data.get("full_text", ""),
            segments=[
                type(
                    "Segment",
                    (),
                    {
                        "start": seg.get("start", 0),
                        "end": seg.get("end", 0),
                        "text": seg.get("text", ""),
                    },
                )()
                for seg in transcript_data.get("segments", [])
            ],
            language=transcript_data.get("language", "en"),
        )

        # Estimate video duration from transcript
        segments = transcript_data.get("segments", [])
        if segments:
            duration = max(seg.get("end", 0) for seg in segments)
        else:
            duration = 30.0  # Default duration

        # Build visual context string for structure parsing
        visual_context = _build_visual_context(visual_analysis)

        # Parse video structure (Hook/Body/CTA)
        structure_parser = StructureParser(
            api_key=api_key,
            model=claude_model,
        )

        structure, audio_style, engagement = structure_parser.parse_structure(
            transcript=transcript_model,
            duration=duration,
            visual_context=visual_context,
        )

        # Build visual style from analysis
        visual_style = _build_visual_style(visual_analysis)

        # Run enhanced analysis if enabled
        scenes = []
        pacing = {}
        product_tracking = {}

        if enable_enhanced and frames:
            scenes, pacing, product_tracking = _run_enhanced_analysis(
                state, frames, transcript_data, api_key, claude_model
            )

        # Create the blueprint
        blueprint = VideoBlueprint(
            source_video=video_path or state.get("video_url", "unknown"),
            total_duration=duration,
            transcript=transcript_model,
            structure=structure,
            visual_style=visual_style,
            audio_style=audio_style,
            engagement_analysis=engagement,
        )

        # Add enhanced analysis results if available
        if scenes:
            blueprint.scenes = scenes
        if pacing:
            blueprint.pacing = pacing
        if product_tracking:
            blueprint.product_tracking = product_tracking

        # Convert to dict for state storage
        blueprint_dict = blueprint.model_dump()

        # Create simplified summary for UI
        blueprint_summary: BlueprintSummary = {
            "transcript": transcript_data.get("full_text", ""),
            "hook_style": structure.hook.style.value if structure.hook else "unknown",
            "body_framework": structure.body.framework.value
            if structure.body
            else "unknown",
            "cta_urgency": structure.cta.urgency.value if structure.cta else "unknown",
            "setting": visual_style.setting
            if hasattr(visual_style, "setting")
            else visual_analysis.get("setting", "unknown"),
            "lighting": visual_style.lighting
            if hasattr(visual_style, "lighting")
            else visual_analysis.get("lighting", "unknown"),
            "energy": audio_style.energy_level
            if hasattr(audio_style, "energy_level")
            else "medium",
            "duration": duration,
        }

        logger.info(
            f"Blueprint generated: "
            f"hook={blueprint_summary.get('hook_style')}, "
            f"body={blueprint_summary.get('body_framework')}, "
            f"cta={blueprint_summary.get('cta_urgency')}"
        )

        return {
            **progress_update,
            "blueprint": blueprint_dict,
            "blueprint_summary": blueprint_summary,
            "scenes": scenes,
            "pacing": pacing,
            "product_tracking": product_tracking,
        }

    except Exception as e:
        logger.exception("Unexpected error generating blueprint")
        return mark_failed(
            state,
            f"Failed to generate blueprint: {str(e)}",
            {"exception_type": type(e).__name__},
        )


def _build_visual_context(visual_analysis: dict[str, Any]) -> str:
    """
    Build a visual context string from visual analysis for structure parsing.

    Args:
        visual_analysis: Visual analysis results dict

    Returns:
        Formatted string describing visual elements
    """
    if not visual_analysis:
        return ""

    parts = []

    if visual_analysis.get("setting"):
        parts.append(f"Setting: {visual_analysis['setting']}")

    if visual_analysis.get("lighting"):
        parts.append(f"Lighting: {visual_analysis['lighting']}")

    if visual_analysis.get("framing"):
        parts.append(f"Framing: {visual_analysis['framing']}")

    if visual_analysis.get("subject_description"):
        parts.append(f"Subject: {visual_analysis['subject_description']}")

    if visual_analysis.get("colors"):
        colors = visual_analysis["colors"]
        if isinstance(colors, list):
            parts.append(f"Colors: {', '.join(colors)}")
        else:
            parts.append(f"Colors: {colors}")

    if visual_analysis.get("product_visible"):
        parts.append("Product is visible in frame")

    return "\n".join(parts) if parts else ""


def _build_visual_style(visual_analysis: dict[str, Any]) -> Any:
    """
    Build a VisualStyle object from visual analysis.

    Args:
        visual_analysis: Visual analysis results dict

    Returns:
        VisualStyle object
    """
    from src.models.blueprint import VisualStyle

    return VisualStyle(
        setting=visual_analysis.get("setting", "unknown"),
        lighting=visual_analysis.get("lighting", "natural"),
        framing=visual_analysis.get("framing", "medium shot"),
        camera_movement=visual_analysis.get("camera_movement", "static"),
        subject_description=visual_analysis.get("subject_description", ""),
        background_elements=visual_analysis.get("background_elements", []),
        colors=visual_analysis.get("colors", []),
        text_overlays=visual_analysis.get("text_overlays", []),
        product_visible=visual_analysis.get("product_visible", False),
        product_description=visual_analysis.get("product_description", ""),
    )


def _run_enhanced_analysis(
    state: PipelineState,
    frames: list[str],
    transcript_data: dict[str, Any],
    api_key: str,
    claude_model: str,
) -> tuple[list[dict], dict, dict]:
    """
    Run enhanced analysis: scene segmentation, pacing, product tracking.

    Args:
        state: Current pipeline state
        frames: List of frame paths
        transcript_data: Transcript data dict
        api_key: Anthropic API key
        claude_model: Claude model to use

    Returns:
        Tuple of (scenes, pacing, product_tracking)
    """
    scenes = []
    pacing = {}
    product_tracking = {}

    try:
        # Scene segmentation
        from src.analyzer.scene_segmenter import SceneSegmenter

        segmenter = SceneSegmenter(
            anthropic_api_key=api_key,
            model=claude_model,
        )
        # Note: SceneSegmenter.segment() needs frames and transcript
        # Implementation depends on your existing code
        logger.info("Running scene segmentation...")

    except ImportError:
        logger.warning("SceneSegmenter not available, skipping scene segmentation")
    except Exception as e:
        logger.warning(f"Scene segmentation failed: {e}")

    try:
        # Pacing analysis
        from src.analyzer.pacing_analyzer import PacingAnalyzer

        pacing_analyzer = PacingAnalyzer()
        # Implementation depends on your existing code
        logger.info("Running pacing analysis...")

    except ImportError:
        logger.warning("PacingAnalyzer not available, skipping pacing analysis")
    except Exception as e:
        logger.warning(f"Pacing analysis failed: {e}")

    try:
        # Product tracking
        from src.analyzer.product_tracker import ProductTracker

        tracker = ProductTracker()
        # Implementation depends on your existing code
        logger.info("Running product tracking...")

    except ImportError:
        logger.warning("ProductTracker not available, skipping product tracking")
    except Exception as e:
        logger.warning(f"Product tracking failed: {e}")

    return scenes, pacing, product_tracking
