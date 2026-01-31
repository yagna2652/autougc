"""
Full Pipeline Graph - Complete LangGraph workflow for UGC generation.

This graph combines the analysis and prompt generation workflows with
video generation to create a complete end-to-end pipeline:

1. Video Analysis Phase:
   - Download video
   - Extract audio & transcribe
   - Extract frames & analyze visuals
   - Generate blueprint

2. Prompt Generation Phase:
   - Analyze product (if images provided)
   - Generate base prompt
   - Generate mechanics-enhanced prompt
   - Finalize prompt

3. Video Generation Phase:
   - Generate video using Fal.ai (Sora 2 or Kling)

The pipeline maintains complete state throughout, ensuring that:
- Blueprint data flows properly to mechanics generation
- Mechanics-enhanced prompts are used when available
- All intermediate results are preserved for debugging
"""

import logging
from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.pipeline.state import PipelineState, PipelineStatus

logger = logging.getLogger(__name__)


def should_continue_after_analysis(
    state: PipelineState,
) -> Literal["prompt_generation", "end"]:
    """
    Check if analysis succeeded before continuing to prompt generation.

    Args:
        state: Current pipeline state

    Returns:
        Next phase to execute or "end" if failed
    """
    # Check for fatal errors
    if state.get("status") == PipelineStatus.FAILED.value:
        logger.error(f"Pipeline failed during analysis: {state.get('error')}")
        return "end"

    # Check if we have minimum required data
    has_blueprint = bool(state.get("blueprint"))
    has_transcript = bool(state.get("transcript", {}).get("full_text"))

    if has_blueprint or has_transcript:
        logger.info("Analysis phase complete, proceeding to prompt generation")
        return "prompt_generation"

    # Check if we at least have visual analysis
    has_visuals = bool(state.get("visual_analysis"))
    if has_visuals:
        logger.warning("Only visual analysis available, proceeding with limited data")
        return "prompt_generation"

    logger.error("Analysis phase did not produce usable results")
    return "end"


def should_continue_after_prompts(
    state: PipelineState,
) -> Literal["video_generation", "end"]:
    """
    Check if prompt generation succeeded before continuing to video generation.

    Args:
        state: Current pipeline state

    Returns:
        Next phase to execute or "end" if failed
    """
    # Check for fatal errors
    if state.get("status") == PipelineStatus.FAILED.value:
        logger.error(f"Pipeline failed during prompt generation: {state.get('error')}")
        return "end"

    # Check if we have a usable prompt
    final_prompt = state.get("final_prompt", "")
    base_prompt = state.get("base_prompt", "")
    mechanics_prompt = state.get("mechanics_prompt", "")

    if final_prompt and final_prompt.strip():
        logger.info(
            f"Prompt generation complete ({len(final_prompt)} chars), "
            "proceeding to video generation"
        )
        return "video_generation"

    # Fallback: use base or mechanics prompt directly
    if base_prompt or mechanics_prompt:
        logger.warning("Using fallback prompt for video generation")
        return "video_generation"

    logger.error("No valid prompt available for video generation")
    return "end"


def build_full_pipeline(with_checkpointer: bool = True) -> StateGraph:
    """
    Build the complete UGC generation LangGraph pipeline.

    The pipeline structure:
    ```
    START
      │
      ▼
    ┌─────────────────────────────────────────┐
    │           VIDEO ANALYSIS PHASE          │
    │                                         │
    │  download_video                         │
    │       │                                 │
    │       ├──────────┬──────────┐          │
    │       │          │          │          │
    │       ▼          ▼          │          │
    │  extract_audio  extract_frames          │
    │       │          │          │          │
    │       ▼          ▼          │          │
    │  transcribe  analyze_visuals            │
    │       │          │          │          │
    │       └─────┬────┘          │          │
    │             │               │          │
    │             ▼               │          │
    │    generate_blueprint ◄─────┘          │
    │                                         │
    └─────────────────────────────────────────┘
                      │
                      ▼
           [should_continue_after_analysis?]
                      │
           ┌── yes ──┴── no ──┐
           │                   │
           ▼                   ▼
    ┌─────────────────────┐   END
    │  PROMPT GENERATION  │
    │                     │
    │  analyze_product    │
    │       │             │
    │       ▼             │
    │  generate_base_prompt│
    │       │             │
    │       ▼             │
    │  generate_mechanics │
    │       │             │
    │       ▼             │
    │  finalize_prompt    │
    │                     │
    └─────────────────────┘
                │
                ▼
     [should_continue_after_prompts?]
                │
     ┌── yes ──┴── no ──┐
     │                   │
     ▼                   ▼
    ┌─────────────────┐ END
    │ VIDEO GENERATION│
    │                 │
    │ generate_video  │
    │                 │
    └─────────────────┘
           │
           ▼
          END
    ```

    Args:
        with_checkpointer: Whether to include memory checkpointer for persistence

    Returns:
        Compiled LangGraph StateGraph
    """
    from src.pipeline.nodes import (
        analyze_product_node,
        analyze_visuals_node,
        download_video_node,
        extract_audio_node,
        extract_frames_node,
        finalize_prompt_node,
        generate_base_prompt_node,
        generate_blueprint_node,
        generate_mechanics_node,
        generate_video_node,
        transcribe_node,
    )

    # Create the graph with our state type
    graph = StateGraph(PipelineState)

    # =========================================================================
    # VIDEO ANALYSIS PHASE NODES
    # =========================================================================
    graph.add_node("download_video", download_video_node)
    graph.add_node("extract_audio", extract_audio_node)
    graph.add_node("transcribe", transcribe_node)
    graph.add_node("extract_frames", extract_frames_node)
    graph.add_node("analyze_visuals", analyze_visuals_node)
    graph.add_node("generate_blueprint", generate_blueprint_node)

    # =========================================================================
    # PROMPT GENERATION PHASE NODES
    # =========================================================================
    graph.add_node("analyze_product", analyze_product_node)
    graph.add_node("generate_base_prompt", generate_base_prompt_node)
    graph.add_node("generate_mechanics", generate_mechanics_node)
    graph.add_node("finalize_prompt", finalize_prompt_node)

    # =========================================================================
    # VIDEO GENERATION PHASE NODES
    # =========================================================================
    graph.add_node("generate_video", generate_video_node)

    # =========================================================================
    # DEFINE EDGES - VIDEO ANALYSIS PHASE
    # =========================================================================

    # Start with download
    graph.add_edge(START, "download_video")

    # After download, extract audio and frames (sequential for simplicity)
    # In production, these could be parallel
    graph.add_edge("download_video", "extract_audio")
    graph.add_edge("download_video", "extract_frames")

    # Audio path
    graph.add_edge("extract_audio", "transcribe")

    # Frames path
    graph.add_edge("extract_frames", "analyze_visuals")

    # Both paths converge at blueprint generation
    graph.add_edge("transcribe", "generate_blueprint")
    graph.add_edge("analyze_visuals", "generate_blueprint")

    # =========================================================================
    # TRANSITION: ANALYSIS -> PROMPT GENERATION
    # =========================================================================

    graph.add_conditional_edges(
        "generate_blueprint",
        should_continue_after_analysis,
        {
            "prompt_generation": "analyze_product",
            "end": END,
        },
    )

    # =========================================================================
    # DEFINE EDGES - PROMPT GENERATION PHASE
    # =========================================================================

    # Product analysis -> base prompt
    graph.add_edge("analyze_product", "generate_base_prompt")

    # Base prompt -> mechanics
    graph.add_edge("generate_base_prompt", "generate_mechanics")

    # Mechanics -> finalize
    graph.add_edge("generate_mechanics", "finalize_prompt")

    # =========================================================================
    # TRANSITION: PROMPT GENERATION -> VIDEO GENERATION
    # =========================================================================

    graph.add_conditional_edges(
        "finalize_prompt",
        should_continue_after_prompts,
        {
            "video_generation": "generate_video",
            "end": END,
        },
    )

    # =========================================================================
    # DEFINE EDGES - VIDEO GENERATION PHASE
    # =========================================================================

    # Video generation -> end
    graph.add_edge("generate_video", END)

    # =========================================================================
    # COMPILE WITH OPTIONAL CHECKPOINTER
    # =========================================================================

    if with_checkpointer:
        # Add memory checkpointer for persistence and debugging
        checkpointer = MemorySaver()
        compiled = graph.compile(checkpointer=checkpointer)
    else:
        compiled = graph.compile()

    return compiled


def build_analysis_only_pipeline() -> StateGraph:
    """
    Build a pipeline that only runs the analysis phase.

    Useful for testing or when you only need the blueprint.

    Returns:
        Compiled analysis-only pipeline
    """
    from src.pipeline.nodes import (
        analyze_visuals_node,
        download_video_node,
        extract_audio_node,
        extract_frames_node,
        generate_blueprint_node,
        transcribe_node,
    )

    graph = StateGraph(PipelineState)

    # Add analysis nodes
    graph.add_node("download_video", download_video_node)
    graph.add_node("extract_audio", extract_audio_node)
    graph.add_node("transcribe", transcribe_node)
    graph.add_node("extract_frames", extract_frames_node)
    graph.add_node("analyze_visuals", analyze_visuals_node)
    graph.add_node("generate_blueprint", generate_blueprint_node)

    # Define flow
    graph.add_edge(START, "download_video")
    graph.add_edge("download_video", "extract_audio")
    graph.add_edge("download_video", "extract_frames")
    graph.add_edge("extract_audio", "transcribe")
    graph.add_edge("extract_frames", "analyze_visuals")
    graph.add_edge("transcribe", "generate_blueprint")
    graph.add_edge("analyze_visuals", "generate_blueprint")
    graph.add_edge("generate_blueprint", END)

    return graph.compile()


def build_prompt_only_pipeline() -> StateGraph:
    """
    Build a pipeline that only runs the prompt generation phase.

    Useful when you already have a blueprint and just need to generate prompts.

    Returns:
        Compiled prompt-only pipeline
    """
    from src.pipeline.nodes import (
        analyze_product_node,
        finalize_prompt_node,
        generate_base_prompt_node,
        generate_mechanics_node,
    )

    graph = StateGraph(PipelineState)

    # Add prompt generation nodes
    graph.add_node("analyze_product", analyze_product_node)
    graph.add_node("generate_base_prompt", generate_base_prompt_node)
    graph.add_node("generate_mechanics", generate_mechanics_node)
    graph.add_node("finalize_prompt", finalize_prompt_node)

    # Define flow
    graph.add_edge(START, "analyze_product")
    graph.add_edge("analyze_product", "generate_base_prompt")
    graph.add_edge("generate_base_prompt", "generate_mechanics")
    graph.add_edge("generate_mechanics", "finalize_prompt")
    graph.add_edge("finalize_prompt", END)

    return graph.compile()


# =========================================================================
# SINGLETON PIPELINE INSTANCE
# =========================================================================

# Global pipeline instance (lazy initialization)
_pipeline = None


def get_pipeline():
    """
    Get the global pipeline instance (lazy initialization).

    Returns:
        Compiled full pipeline
    """
    global _pipeline
    if _pipeline is None:
        _pipeline = build_full_pipeline(with_checkpointer=True)
    return _pipeline


# Convenience export
pipeline = None


def ensure_pipeline():
    """Ensure pipeline is initialized and return it."""
    global pipeline
    if pipeline is None:
        pipeline = get_pipeline()
    return pipeline


# =========================================================================
# PIPELINE RUNNER UTILITIES
# =========================================================================


async def run_pipeline_async(
    initial_state: PipelineState,
    config: dict[str, Any] | None = None,
) -> PipelineState:
    """
    Run the pipeline asynchronously.

    Args:
        initial_state: Initial pipeline state
        config: Optional LangGraph config (for thread_id, etc.)

    Returns:
        Final pipeline state
    """
    pipeline = ensure_pipeline()
    config = config or {}

    # Ensure thread_id for checkpointing
    if "configurable" not in config:
        config["configurable"] = {}
    if "thread_id" not in config["configurable"]:
        config["configurable"]["thread_id"] = initial_state.get("job_id", "default")

    # Run the pipeline
    final_state = await pipeline.ainvoke(initial_state, config)
    return final_state


def run_pipeline_sync(
    initial_state: PipelineState,
    config: dict[str, Any] | None = None,
) -> PipelineState:
    """
    Run the pipeline synchronously.

    Args:
        initial_state: Initial pipeline state
        config: Optional LangGraph config (for thread_id, etc.)

    Returns:
        Final pipeline state
    """
    pipeline = ensure_pipeline()
    config = config or {}

    # Ensure thread_id for checkpointing
    if "configurable" not in config:
        config["configurable"] = {}
    if "thread_id" not in config["configurable"]:
        config["configurable"]["thread_id"] = initial_state.get("job_id", "default")

    # Run the pipeline
    final_state = pipeline.invoke(initial_state, config)
    return final_state


def stream_pipeline(
    initial_state: PipelineState,
    config: dict[str, Any] | None = None,
):
    """
    Stream pipeline execution, yielding state updates.

    This is useful for real-time progress updates in the UI.

    Args:
        initial_state: Initial pipeline state
        config: Optional LangGraph config

    Yields:
        Tuple of (node_name, state_update) for each step
    """
    pipeline = ensure_pipeline()
    config = config or {}

    # Ensure thread_id for checkpointing
    if "configurable" not in config:
        config["configurable"] = {}
    if "thread_id" not in config["configurable"]:
        config["configurable"]["thread_id"] = initial_state.get("job_id", "default")

    # Stream the pipeline
    for event in pipeline.stream(initial_state, config):
        for node_name, state_update in event.items():
            yield node_name, state_update
