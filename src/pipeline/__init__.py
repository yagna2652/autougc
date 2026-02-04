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

    # Just provide a TikTok URL - product auto-loads from assets/products/keychain/
    state = create_initial_state(
        video_url="https://tiktok.com/...",
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
from src.pipeline.product_loader import (
    get_available_products,
    load_default_product,
    load_product,
)
from src.pipeline.state import (
    DEFAULT_CONFIG,
    PipelineState,
    create_initial_state,
)
from src.pipeline.types import (
    CameraInfo,
    InteractionBeat,
    InteractionClip,
    InteractionConstraints,
    InteractionPlanData,
    PersonInfo,
    PipelineConfig,
    ProductVisualFeatures,
    SelectedInteraction,
    UGCIntentData,
    VideoAnalysisData,
)

__all__ = [
    # State
    "PipelineState",
    "create_initial_state",
    "DEFAULT_CONFIG",
    # Types
    "VideoAnalysisData",
    "CameraInfo",
    "PersonInfo",
    "UGCIntentData",
    "InteractionPlanData",
    "InteractionBeat",
    "InteractionClip",
    "SelectedInteraction",
    "ProductVisualFeatures",
    "PipelineConfig",
    "InteractionConstraints",
    # Product loader
    "load_product",
    "load_default_product",
    "get_available_products",
    # Pipeline
    "build_pipeline",
    "get_pipeline",
    "run_pipeline",
    "run_pipeline_async",
    "stream_pipeline",
]
