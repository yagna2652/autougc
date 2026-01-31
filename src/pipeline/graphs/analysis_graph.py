"""
Analysis Graph - LangGraph workflow for video analysis.

This graph orchestrates the video analysis pipeline:
1. Download video
2. Extract audio (parallel with frame extraction)
3. Transcribe audio
4. Extract frames (parallel with audio extraction)
5. Analyze visuals
6. Generate blueprint (waits for both transcription and visual analysis)

The graph uses LangGraph's StateGraph to manage state flow between nodes.
"""

import logging
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from src.pipeline.state import PipelineState, PipelineStatus

logger = logging.getLogger(__name__)


def should_continue_after_download(
    state: PipelineState,
) -> Literal["extract_audio", "end"]:
    """
    Check if download succeeded before continuing.

    Args:
        state: Current pipeline state

    Returns:
        Next node to execute or "end" if failed
    """
    if state.get("error"):
        logger.error(f"Download failed: {state.get('error')}")
        return "end"

    if state.get("video_path"):
        return "extract_audio"

    logger.error("No video path after download")
    return "end"


def should_continue_after_audio(
    state: PipelineState,
) -> Literal["transcribe", "end"]:
    """
    Check if audio extraction succeeded before continuing.

    Args:
        state: Current pipeline state

    Returns:
        Next node to execute or "end" if failed
    """
    if state.get("error") and "audio" in state.get("error", "").lower():
        logger.error(f"Audio extraction failed: {state.get('error')}")
        return "end"

    if state.get("audio_path"):
        return "transcribe"

    # Audio extraction may have failed but we can still continue
    # with visual analysis only
    logger.warning("No audio path, continuing without transcription")
    return "end"


def should_continue_after_frames(
    state: PipelineState,
) -> Literal["analyze_visuals", "end"]:
    """
    Check if frame extraction succeeded before continuing.

    Args:
        state: Current pipeline state

    Returns:
        Next node to execute or "end" if failed
    """
    if state.get("frames") or state.get("frames_base64"):
        return "analyze_visuals"

    logger.warning("No frames extracted, skipping visual analysis")
    return "end"


def can_generate_blueprint(
    state: PipelineState,
) -> Literal["generate_blueprint", "end"]:
    """
    Check if we have enough data to generate a blueprint.

    Requires at least a transcript to generate the blueprint.

    Args:
        state: Current pipeline state

    Returns:
        "generate_blueprint" if ready, "end" otherwise
    """
    has_transcript = bool(state.get("transcript", {}).get("full_text"))
    has_visuals = bool(state.get("visual_analysis"))

    if has_transcript:
        return "generate_blueprint"

    if has_visuals:
        # Can generate minimal blueprint from visuals only
        logger.warning("No transcript, generating blueprint from visuals only")
        return "generate_blueprint"

    logger.error("Cannot generate blueprint: no transcript or visual analysis")
    return "end"


def build_analysis_graph() -> StateGraph:
    """
    Build the video analysis LangGraph workflow.

    The graph structure:
    ```
    START
      │
      ▼
    download_video
      │
      ├───────────────────┐
      │                   │
      ▼                   ▼
    extract_audio     extract_frames
      │                   │
      ▼                   ▼
    transcribe       analyze_visuals
      │                   │
      └─────────┬─────────┘
                │
                ▼
        generate_blueprint
                │
                ▼
              END
    ```

    Returns:
        Compiled LangGraph StateGraph
    """
    from src.pipeline.nodes import (
        analyze_visuals_node,
        download_video_node,
        extract_audio_node,
        extract_frames_node,
        generate_blueprint_node,
        transcribe_node,
    )

    # Create the graph with our state type
    graph = StateGraph(PipelineState)

    # Add all nodes
    graph.add_node("download_video", download_video_node)
    graph.add_node("extract_audio", extract_audio_node)
    graph.add_node("transcribe", transcribe_node)
    graph.add_node("extract_frames", extract_frames_node)
    graph.add_node("analyze_visuals", analyze_visuals_node)
    graph.add_node("generate_blueprint", generate_blueprint_node)

    # Define the flow
    # Start with download
    graph.add_edge(START, "download_video")

    # After download, branch to both audio and frame extraction
    graph.add_conditional_edges(
        "download_video",
        should_continue_after_download,
        {
            "extract_audio": "extract_audio",
            "end": END,
        },
    )

    # Also extract frames after download (parallel path)
    # We need to use a custom router for this since we want parallel execution
    graph.add_edge("download_video", "extract_frames")

    # Audio path: extract -> transcribe
    graph.add_conditional_edges(
        "extract_audio",
        should_continue_after_audio,
        {
            "transcribe": "transcribe",
            "end": END,
        },
    )

    # Frames path: extract -> analyze
    graph.add_conditional_edges(
        "extract_frames",
        should_continue_after_frames,
        {
            "analyze_visuals": "analyze_visuals",
            "end": END,
        },
    )

    # Both paths converge at blueprint generation
    graph.add_edge("transcribe", "generate_blueprint")
    graph.add_edge("analyze_visuals", "generate_blueprint")

    # Blueprint generation to end
    graph.add_edge("generate_blueprint", END)

    return graph


def compile_analysis_graph():
    """
    Build and compile the analysis graph.

    Returns:
        Compiled graph ready for execution
    """
    graph = build_analysis_graph()
    return graph.compile()


# Pre-compiled graph for direct import
analysis_graph = None


def get_analysis_graph():
    """
    Get the compiled analysis graph (lazy initialization).

    Returns:
        Compiled analysis graph
    """
    global analysis_graph
    if analysis_graph is None:
        analysis_graph = compile_analysis_graph()
    return analysis_graph
