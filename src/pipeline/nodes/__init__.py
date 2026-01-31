"""
Pipeline Nodes - Individual processing steps for the LangGraph pipeline.

Each node is a function that:
1. Takes the current PipelineState
2. Performs a specific task
3. Returns a partial state update (dict)

Nodes are designed to be:
- Idempotent where possible
- Observable via LangSmith tracing
- Fault-tolerant with clear error handling
"""

from src.pipeline.nodes.analyze_product import analyze_product_node
from src.pipeline.nodes.analyze_visuals import analyze_visuals_node
from src.pipeline.nodes.download_video import download_video_node
from src.pipeline.nodes.extract_audio import extract_audio_node
from src.pipeline.nodes.extract_frames import extract_frames_node
from src.pipeline.nodes.finalize_prompt import finalize_prompt_node
from src.pipeline.nodes.generate_base_prompt import generate_base_prompt_node
from src.pipeline.nodes.generate_blueprint import generate_blueprint_node
from src.pipeline.nodes.generate_mechanics import generate_mechanics_node
from src.pipeline.nodes.generate_video import generate_video_node
from src.pipeline.nodes.transcribe import transcribe_node

__all__ = [
    # Analysis nodes
    "download_video_node",
    "extract_audio_node",
    "transcribe_node",
    "extract_frames_node",
    "analyze_visuals_node",
    "generate_blueprint_node",
    # Prompt generation nodes
    "analyze_product_node",
    "generate_base_prompt_node",
    "generate_mechanics_node",
    "finalize_prompt_node",
    # Video generation nodes
    "generate_video_node",
]
