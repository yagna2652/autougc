"""
Simple Pipeline State for UGC Video Generation.

Minimal state that flows through the pipeline:
1. Download TikTok
2. Extract frames
3. Analyze with Claude Vision
4. Generate prompt
5. Generate video
"""

import logging
from typing import Literal, TypedDict

from src.pipeline.types import (
    PipelineConfig,
    VideoAnalysisData,
)

logger = logging.getLogger(__name__)

# Status type for pipeline state
PipelineStatus = Literal["pending", "running", "completed", "failed"]


class PipelineState(TypedDict, total=False):
    """
    Minimal state for the UGC pipeline.

    All fields are optional (total=False) to allow partial updates.
    """

    # Job tracking
    job_id: str
    status: PipelineStatus
    current_step: str
    error: str

    # Input
    video_url: str
    product_description: str
    product_images: list[str]  # base64 or URLs
    product_category: str  # e.g., 'mechanical_keyboard_keychain'
    product_mechanics: str  # prose describing physical interaction rules

    # Config
    config: PipelineConfig

    # Pipeline data (populated as we go)
    video_path: str  # Downloaded video file path
    frames: list[str]  # List of extracted frame paths
    video_analysis: VideoAnalysisData  # Claude Vision analysis
    video_prompt: str  # Generated prompt for video API
    suggested_script: str  # Suggested script/voiceover
    scene_description: str  # Prompt for scene image generation (Nano Banana Pro)

    # Scene image (composited first frame for I2V)
    scene_image_url: str  # Fal CDN URL of generated scene image

    # I2V (Image-to-Video)
    i2v_image_url: str  # Fal CDN URL of uploaded product image

    # Output
    generated_video_url: str  # Final video URL


def create_initial_state(
    video_url: str,
    product_description: str = "",
    product_images: list[str] | None = None,
    product_category: str | None = None,
    product_mechanics: str = "",
    config: PipelineConfig | None = None,
    job_id: str | None = None,
) -> PipelineState:
    """
    Create initial pipeline state.

    Args:
        video_url: TikTok URL to analyze
        product_description: Description of product to feature
        product_images: Product images (required) - base64 or URLs
        product_category: Product category for interaction planning
        product_mechanics: Prose describing physical interaction rules
        config: Optional configuration overrides
        job_id: Optional job ID (generated if not provided)

    Returns:
        Initial PipelineState

    Raises:
        ValueError: If product_images is empty or not provided
    """
    import uuid

    # Validate required product images
    if not product_images:
        raise ValueError("Product images are required for video generation")

    return PipelineState(
        job_id=job_id or str(uuid.uuid4()),
        status="pending",
        current_step="initializing",
        error="",
        video_url=video_url,
        product_description=product_description,
        product_images=product_images,
        product_category=product_category or "mechanical_keyboard_keychain",
        product_mechanics=product_mechanics,
        config=config or {},
        video_path="",
        frames=[],
        video_analysis={},
        video_prompt="",
        suggested_script="",
        scene_description="",
        scene_image_url="",
        i2v_image_url="",
        generated_video_url="",
    )


# Default configuration
DEFAULT_CONFIG = {
    "claude_model": "claude-sonnet-4-20250514",
    "num_frames": 5,
    "video_model": "sora",  # sora or kling
    "video_duration": 5,
    "aspect_ratio": "9:16",
    "i2v_image_index": 0,  # Which product image to use for I2V (0-indexed)
}
