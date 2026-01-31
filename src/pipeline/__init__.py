"""
LangGraph-based pipeline for UGC video generation.

This module provides a stateful, observable pipeline that orchestrates:
1. Video analysis (download, transcribe, extract frames, analyze visuals)
2. Blueprint generation (structure parsing, mechanics mapping)
3. Prompt generation (product analysis, mechanics enhancement)
4. Video generation (Sora 2, Kling via Fal.ai)

Usage:
    from src.pipeline import create_initial_state, run_pipeline_sync, stream_pipeline

    # Create initial state
    state = create_initial_state(
        video_url="https://tiktok.com/...",
        product_images=[...],
        product_description="...",
    )

    # Run synchronously
    result = run_pipeline_sync(state)

    # Or stream for real-time updates
    for node_name, update in stream_pipeline(state):
        print(f"{node_name}: {update.get('current_step')}")

LangSmith Integration:
    Set these environment variables to enable tracing:
    - LANGCHAIN_TRACING_V2=true
    - LANGCHAIN_API_KEY=your_api_key
    - LANGCHAIN_PROJECT=autougc-pipeline
"""

from src.pipeline.state import (
    PipelineConfig,
    PipelineState,
    PipelineStatus,
    PipelineStep,
    create_initial_state,
    mark_completed,
    mark_failed,
    update_progress,
)


# Lazy imports to avoid circular dependencies
def get_pipeline():
    """Get the compiled full pipeline."""
    from src.pipeline.graphs.full_pipeline import get_pipeline as _get_pipeline

    return _get_pipeline()


def run_pipeline_sync(initial_state: PipelineState, config: dict = None):
    """Run the pipeline synchronously."""
    from src.pipeline.graphs.full_pipeline import run_pipeline_sync as _run

    return _run(initial_state, config)


async def run_pipeline_async(initial_state: PipelineState, config: dict = None):
    """Run the pipeline asynchronously."""
    from src.pipeline.graphs.full_pipeline import run_pipeline_async as _run

    return await _run(initial_state, config)


def stream_pipeline(initial_state: PipelineState, config: dict = None):
    """Stream pipeline execution with real-time updates."""
    from src.pipeline.graphs.full_pipeline import stream_pipeline as _stream

    yield from _stream(initial_state, config)


__all__ = [
    # State types
    "PipelineState",
    "PipelineConfig",
    "PipelineStatus",
    "PipelineStep",
    # State utilities
    "create_initial_state",
    "update_progress",
    "mark_completed",
    "mark_failed",
    # Pipeline runners
    "get_pipeline",
    "run_pipeline_sync",
    "run_pipeline_async",
    "stream_pipeline",
]
