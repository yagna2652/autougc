"""
Simple UGC Video Generation Pipeline.

A minimal pipeline that:
1. Downloads a TikTok video
2. Extracts key frames
3. Analyzes with Claude Vision
4. Generates a video prompt
5. Generates the video

Usage:
    from src.pipeline import create_initial_state, run_pipeline

    state = create_initial_state(
        video_url="https://tiktok.com/...",
        product_description="My awesome product",
    )

    result = run_pipeline(state)
    print(result["generated_video_url"])

LangSmith tracing is automatically enabled when configured.
"""

from src.pipeline.graphs.simple_pipeline import (
    build_pipeline,
    get_pipeline,
    run_pipeline,
    run_pipeline_async,
    stream_pipeline,
)
from src.pipeline.state import (
    DEFAULT_CONFIG,
    PipelineState,
    create_initial_state,
)

__all__ = [
    # State
    "PipelineState",
    "create_initial_state",
    "DEFAULT_CONFIG",
    # Pipeline
    "build_pipeline",
    "get_pipeline",
    "run_pipeline",
    "run_pipeline_async",
    "stream_pipeline",
]
