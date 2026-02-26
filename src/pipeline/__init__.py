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

# Direct imports — resolved at import time (no deadlock)
from src.pipeline.state import PipelineState, create_initial_state, DEFAULT_CONFIG
from src.pipeline.types import VideoAnalysisData, CameraInfo, PersonInfo, PipelineConfig
from src.pipeline.product_loader import load_product, load_default_product, get_available_products


def _resolve(module_path: str, attr_name: str) -> Any:
    module = import_module(module_path)
    return getattr(module, attr_name)


# Runtime wrappers — _resolve() only called when these functions are invoked, not imported

def build_pipeline():
    return _resolve("src.pipeline.graphs.simple_pipeline", "build_pipeline")()


def get_pipeline():
    return _resolve("src.pipeline.graphs.simple_pipeline", "get_pipeline")()


def run_pipeline(initial_state: Any):
    return _resolve("src.pipeline.graphs.simple_pipeline", "run_pipeline")(initial_state)


async def run_pipeline_async(initial_state: Any):
    return await _resolve("src.pipeline.graphs.simple_pipeline", "run_pipeline_async")(initial_state)


def stream_pipeline(initial_state: Any, stop_after: Any = None):
    return _resolve("src.pipeline.graphs.simple_pipeline", "stream_pipeline")(initial_state, stop_after=stop_after)


def stream_from_node(state: Any, start_node: str):
    return _resolve("src.pipeline.graphs.simple_pipeline", "stream_from_node")(state, start_node)

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
    "stream_from_node",
]
