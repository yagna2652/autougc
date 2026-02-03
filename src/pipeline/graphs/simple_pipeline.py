"""
Simple UGC Pipeline - LangGraph workflow for video generation.

A clean, minimal pipeline:
1. Download TikTok video
2. Extract frames
3. Analyze with Claude Vision
4. Classify UGC intent/archetype
5. Generate video prompt
6. Generate video

All steps are traced via LangSmith for observability.
"""

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.pipeline.state import PipelineState

logger = logging.getLogger(__name__)


# Import nodes
from src.pipeline.nodes.analyze_video import analyze_video_node
from src.pipeline.nodes.classify_ugc_intent import classify_ugc_intent_node
from src.pipeline.nodes.download_video import download_video_node
from src.pipeline.nodes.extract_frames import extract_frames_node
from src.pipeline.nodes.generate_prompt import generate_prompt_node
from src.pipeline.nodes.generate_video import generate_video_node
from src.pipeline.nodes.plan_interactions import plan_interactions_node
from src.pipeline.nodes.select_interactions import select_interaction_clips_node


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
        START → download → extract_frames → analyze → classify_ugc_intent
              → plan_interactions → select_interactions → generate_prompt → generate_video → END

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph
    workflow = StateGraph(PipelineState)

    # Add nodes
    workflow.add_node("download_video", download_video_node)
    workflow.add_node("extract_frames", extract_frames_node)
    workflow.add_node("analyze_video", analyze_video_node)
    workflow.add_node("classify_ugc_intent", classify_ugc_intent_node)
    workflow.add_node("plan_interactions", plan_interactions_node)
    workflow.add_node("select_interactions", select_interaction_clips_node)
    workflow.add_node("generate_prompt", generate_prompt_node)
    workflow.add_node("generate_video", generate_video_node)

    # Define the flow
    workflow.add_edge(START, "download_video")

    # After download, check for errors then continue
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
            "continue": "classify_ugc_intent",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "classify_ugc_intent",
        should_continue,
        {
            "continue": "plan_interactions",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "plan_interactions",
        should_continue,
        {
            "continue": "select_interactions",
            "end": END,
        },
    )

    workflow.add_conditional_edges(
        "select_interactions",
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


def stream_pipeline(initial_state: PipelineState):
    """
    Stream pipeline execution with real-time updates.

    Args:
        initial_state: Initial pipeline state

    Yields:
        Tuples of (node_name, state_update) for each step
    """
    pipeline = get_pipeline()

    initial_state["status"] = "running"

    for output in pipeline.stream(initial_state):
        for node_name, state_update in output.items():
            logger.info(f"Completed: {node_name}")
            yield node_name, state_update
