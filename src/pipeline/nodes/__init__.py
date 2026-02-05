"""
Pipeline Nodes - Processing steps for the UGC generation pipeline.

9-step pipeline:
1. download_video - Download TikTok video from URL
2. extract_frames - Extract key frames for analysis
3. analyze_product - Analyze product images with Claude Vision
4. analyze_video - Analyze frames with Claude Vision
5. classify_ugc_intent - Classify UGC archetype and intent
6. plan_interactions - Plan interaction sequence for fidget products
7. select_interactions - Select reference clips from library
8. generate_prompt - Generate video prompt from analysis
9. generate_video - Call video generation API
"""

from src.pipeline.nodes.analyze_product import analyze_product_node
from src.pipeline.nodes.analyze_video import analyze_video_node
from src.pipeline.nodes.classify_ugc_intent import classify_ugc_intent_node
from src.pipeline.nodes.download_video import download_video_node
from src.pipeline.nodes.extract_frames import extract_frames_node
from src.pipeline.nodes.generate_prompt import generate_prompt_node
from src.pipeline.nodes.generate_video import generate_video_node
from src.pipeline.nodes.plan_interactions import plan_interactions_node
from src.pipeline.nodes.select_interactions import select_interaction_clips_node

__all__ = [
    "download_video_node",
    "extract_frames_node",
    "analyze_product_node",
    "analyze_video_node",
    "classify_ugc_intent_node",
    "plan_interactions_node",
    "select_interaction_clips_node",
    "generate_prompt_node",
    "generate_video_node",
]
