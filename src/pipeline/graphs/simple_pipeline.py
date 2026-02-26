"""
Simple UGC Pipeline - LangGraph workflow for video generation.

A clean, minimal pipeline:
1. Download TikTok video
2. Extract frames
3. Analyze with vision model (OpenRouter)
4. Generate video prompt
5. Validate video prompt quality
6. Generate scene image (composite product into TikTok-style scene)
7. Generate video

All steps are traced via LangSmith for observability.
"""

import logging
from functools import wraps
from typing import Any, Callable, Literal

from langgraph.graph import END, START, StateGraph

from src.pipeline.state import PipelineState

logger = logging.getLogger(__name__)


# Import nodes
from src.pipeline.nodes.analyze_video import analyze_video_node
from src.pipeline.nodes.download_video import download_video_node
from src.pipeline.nodes.extract_frames import extract_frames_node
from src.pipeline.nodes.generate_prompt import generate_prompt_node
from src.pipeline.nodes.generate_scene_image import generate_scene_image_node
from src.pipeline.nodes.generate_video import generate_video_node
from src.pipeline.nodes.validate_prompt import validate_prompt_node


# Human-readable descriptions for logging
NODE_DESCRIPTIONS = {
    "download_video": "Downloading TikTok video",
    "extract_frames": "Extracting key frames from video",
    "analyze_video": "Analyzing video style with vision model",
    "generate_prompt": "Generating video prompt",
    "validate_prompt": "Validating video prompt quality",
    "generate_scene_image": "Generating scene image (Nano Banana Pro)",
    "generate_video": "Generating video (this takes 2-5 minutes)",
}


def with_logging(node_name: str, node_func: Callable) -> Callable:
    """Wrap a node function with start/end logging."""

    @wraps(node_func)
    def wrapper(state: dict[str, Any]) -> dict[str, Any]:
        desc = NODE_DESCRIPTIONS.get(node_name, node_name)
        logger.info(f"▶ STARTING: {desc}...")
        result = node_func(state)
        if result.get("error"):
            logger.error(f"✗ FAILED: {desc} - {result.get('error')}")
        else:
            logger.info(f"✓ DONE: {desc}")
        return result

    return wrapper


def should_continue(state: PipelineState) -> Literal["continue", "end"]:
    """Check if pipeline should continue or stop due to error."""
    if state.get("error"):
        logger.warning(f"Pipeline stopping due to error: {state['error']}")
        return "end"
    return "continue"


def build_pipeline() -> StateGraph:
    """
    Build the simple UGC generation pipeline.

    Flow:
        START → download → extract_frames → analyze_video → generate_prompt → validate_prompt → generate_scene_image → generate_video → END

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph
    workflow = StateGraph(PipelineState)

    # Add nodes with logging wrappers
    workflow.add_node(
        "download_video", with_logging("download_video", download_video_node)
    )
    workflow.add_node(
        "extract_frames", with_logging("extract_frames", extract_frames_node)
    )
    workflow.add_node(
        "analyze_video", with_logging("analyze_video", analyze_video_node)
    )
    workflow.add_node(
        "generate_prompt", with_logging("generate_prompt", generate_prompt_node)
    )
    workflow.add_node(
        "validate_prompt", with_logging("validate_prompt", validate_prompt_node)
    )
    workflow.add_node(
        "generate_scene_image",
        with_logging("generate_scene_image", generate_scene_image_node),
    )
    workflow.add_node(
        "generate_video", with_logging("generate_video", generate_video_node)
    )

    # Define the flow
    workflow.add_edge(START, "download_video")

    workflow.add_conditional_edges(
        "download_video",
        should_continue,
        {
            "continue": "extract_frames",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "extract_frames",
        should_continue,
        {
            "continue": "analyze_video",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "analyze_video",
        should_continue,
        {
            "continue": "generate_prompt",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "generate_prompt",
        should_continue,
        {
            "continue": "validate_prompt",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "validate_prompt",
        should_continue,
        {
            "continue": "generate_scene_image",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "generate_scene_image",
        should_continue,
        {
            "continue": "generate_video",
            "end": END,
        },
    )

    workflow.add_edge("generate_video", END)

    return workflow.compile()


# Singleton pipeline instance
_pipeline = None


def get_pipeline() -> StateGraph:
    """Get or create the pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline


def run_pipeline(initial_state: PipelineState) -> PipelineState:
    """
    Run the pipeline synchronously.

    Args:
        initial_state: Initial pipeline state with video_url and product info

    Returns:
        Final pipeline state with results
    """
    pipeline = get_pipeline()

    # Update status
    initial_state["status"] = "running"
    initial_state["current_step"] = "starting"

    # Run the pipeline
    final_state = pipeline.invoke(initial_state)

    # Update final status
    if final_state.get("error"):
        final_state["status"] = "failed"
    else:
        final_state["status"] = "completed"
        final_state["current_step"] = "done"

    return final_state


async def run_pipeline_async(initial_state: PipelineState) -> PipelineState:
    """
    Run the pipeline asynchronously.

    Args:
        initial_state: Initial pipeline state with video_url and product info

    Returns:
        Final pipeline state with results
    """
    pipeline = get_pipeline()

    # Update status
    initial_state["status"] = "running"
    initial_state["current_step"] = "starting"

    # Run the pipeline
    final_state = await pipeline.ainvoke(initial_state)

    # Update final status
    if final_state.get("error"):
        final_state["status"] = "failed"
    else:
        final_state["status"] = "completed"
        final_state["current_step"] = "done"

    return final_state


def stream_pipeline(initial_state: PipelineState, stop_after: str | None = None):
    """
    Stream pipeline execution with real-time updates.

    Args:
        initial_state: Initial pipeline state
        stop_after: If set, stop yielding after this node completes

    Yields:
        Tuples of (node_name, state_update) for each step
    """
    pipeline = get_pipeline()

    initial_state["status"] = "running"

    for output in pipeline.stream(initial_state):
        for node_name, state_update in output.items():
            logger.info(f"Completed: {node_name}")
            yield node_name, state_update
            if stop_after and node_name == stop_after:
                return


# Ordered mapping of node name → function for direct invocation (resume path)
ORDERED_NODES = [
    ("download_video", download_video_node),
    ("extract_frames", extract_frames_node),
    ("analyze_video", analyze_video_node),
    ("generate_prompt", generate_prompt_node),
    ("validate_prompt", validate_prompt_node),
    ("generate_scene_image", generate_scene_image_node),
    ("generate_video", generate_video_node),
]


def stream_from_node(state: dict[str, Any], start_node: str):
    """
    Resume pipeline from a specific node, calling node functions directly.

    Bypasses LangGraph and calls the wrapped node functions in sequence
    starting from ``start_node``.

    Args:
        state: Accumulated pipeline state (must contain all fields up to start_node)
        start_node: Node name to start from (inclusive)

    Yields:
        Tuples of (node_name, state_update) for each step
    """
    found = False
    for node_name, node_func in ORDERED_NODES:
        if node_name == start_node:
            found = True
        if not found:
            continue

        desc = NODE_DESCRIPTIONS.get(node_name, node_name)
        logger.info(f"▶ STARTING (resume): {desc}...")
        result = node_func(state)
        if result.get("error"):
            logger.error(f"✗ FAILED (resume): {desc} - {result.get('error')}")
        else:
            logger.info(f"✓ DONE (resume): {desc}")

        # Merge result into state for subsequent nodes
        state.update(result)
        yield node_name, result

        if result.get("error"):
            return
