"""
Pipeline Nodes - Processing steps for the UGC generation pipeline.

7-step pipeline:
1. download_video - Download TikTok video from URL
2. extract_frames - Extract key frames for analysis
3. analyze_video - Analyze frames with vision model (OpenRouter)
4. generate_prompt - Generate video prompt from analysis + mechanics + library
5. validate_prompt - Pre-generation quality gate for video prompts
6. generate_scene_image - Composite product into TikTok-style scene (Nano Banana Pro)
7. generate_video - Call video generation API
"""

from src.pipeline.nodes.analyze_video import analyze_video_node
from src.pipeline.nodes.download_video import download_video_node
from src.pipeline.nodes.extract_frames import extract_frames_node
from src.pipeline.nodes.generate_prompt import generate_prompt_node
from src.pipeline.nodes.generate_scene_image import generate_scene_image_node
from src.pipeline.nodes.generate_video import generate_video_node
from src.pipeline.nodes.validate_prompt import validate_prompt_node

__all__ = [
    "download_video_node",
    "extract_frames_node",
    "analyze_video_node",
    "generate_prompt_node",
    "validate_prompt_node",
    "generate_scene_image_node",
    "generate_video_node",
]
