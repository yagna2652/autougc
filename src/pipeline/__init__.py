"""
Simple UGC Video Generation Pipeline.

A minimal pipeline that:
1. Downloads a TikTok video
2. Extracts key frames
3. Analyzes with vision model (OpenRouter)
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

from importlib import import_module
from typing import Any


def _resolve(module_path: str, attr_name: str) -> Any:
    module = import_module(module_path)
    return getattr(module, attr_name)


def __getattr__(name: str) -> Any:
    export_map = {
        # State
        "PipelineState": ("src.pipeline.state", "PipelineState"),
        "create_initial_state": ("src.pipeline.state", "create_initial_state"),
        "DEFAULT_CONFIG": ("src.pipeline.state", "DEFAULT_CONFIG"),
        # Types
        "VideoAnalysisData": ("src.pipeline.types", "VideoAnalysisData"),
        "CameraInfo": ("src.pipeline.types", "CameraInfo"),
        "PersonInfo": ("src.pipeline.types", "PersonInfo"),
        "PipelineConfig": ("src.pipeline.types", "PipelineConfig"),
        # Product loader
        "load_product": ("src.pipeline.product_loader", "load_product"),
        "load_default_product": ("src.pipeline.product_loader", "load_default_product"),
        "get_available_products": ("src.pipeline.product_loader", "get_available_products"),
    }

    if name not in export_map:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_path, attr_name = export_map[name]
    value = _resolve(module_path, attr_name)
    globals()[name] = value
    return value


def build_pipeline():
    return _resolve("src.pipeline.graphs.simple_pipeline", "build_pipeline")()


def get_pipeline():
    return _resolve("src.pipeline.graphs.simple_pipeline", "get_pipeline")()


def run_pipeline(initial_state: Any):
    return _resolve("src.pipeline.graphs.simple_pipeline", "run_pipeline")(initial_state)


async def run_pipeline_async(initial_state: Any):
    return await _resolve("src.pipeline.graphs.simple_pipeline", "run_pipeline_async")(initial_state)


def stream_pipeline(initial_state: Any):
    return _resolve("src.pipeline.graphs.simple_pipeline", "stream_pipeline")(initial_state)

__all__ = [
    # State
    "PipelineState",
    "create_initial_state",
    "DEFAULT_CONFIG",
    # Types
    "VideoAnalysisData",
    "CameraInfo",
    "PersonInfo",
    "PipelineConfig",
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
