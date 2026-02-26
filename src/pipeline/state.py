"""
Simple Pipeline State for UGC Video Generation.

Minimal state that flows through the pipeline:
1. Download TikTok
2. Extract frames
3. Analyze with OpenRouter Vision
4. Generate prompt
5. Generate video
"""

import logging
from typing import Literal, TypedDict

from src.pipeline.types import (
    PipelineConfig,
    ProductReference,
    VideoAnalysisData,
)

logger = logging.getLogger(__name__)

# Status type for pipeline state
PipelineStatus = Literal["pending", "running", "paused", "completed", "failed"]


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
    product_images: list[str]  # file paths, URLs, or data URLs
    product_identity_pack: ProductReference  # multi-angle identity references
    product_category: str  # e.g., 'mechanical_keyboard_keychain'
    product_mechanics: str  # prose describing physical interaction rules

    # Config
    config: PipelineConfig

    # Pipeline data (populated as we go)
    video_path: str  # Downloaded video file path
    frames: list[str]  # List of extracted frame paths
    video_analysis: VideoAnalysisData  # Vision model analysis
    video_prompt: str  # Generated prompt for video API
    suggested_script: str  # Suggested script/voiceover
    scene_description: str  # Prompt for scene image generation (Nano Banana Pro)
    prompt_validation: dict  # Validation results from validate_prompt node

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
    product_identity_pack: ProductReference | None = None,
    product_category: str | None = None,
    product_mechanics: str = "",
    config: PipelineConfig | None = None,
    job_id: str | None = None,
) -> PipelineState:
    """
    Create initial pipeline state.

    If product fields are missing, this function attempts to auto-load the
    default product from assets/products before validating required images.

    Args:
        video_url: TikTok URL to analyze
        product_description: Description of product to feature
        product_images: Product images (auto-loaded from default product if missing)
        product_category: Product category for interaction planning
        product_mechanics: Prose describing physical interaction rules
        config: Optional configuration overrides
        job_id: Optional job ID (generated if not provided)

    Returns:
        Initial PipelineState

    Raises:
        ValueError: If product_images is empty and default product loading fails
    """
    import uuid

    resolved_description = product_description
    resolved_images = list(product_images or [])
    resolved_category = product_category or ""
    resolved_mechanics = product_mechanics

    # Auto-load default product details when fields are missing.
    if (
        not resolved_images
        or not resolved_description
        or not resolved_category
        or not resolved_mechanics
    ):
        try:
            from src.pipeline.product_loader import load_product

            default_product = load_product()
            if not resolved_description:
                resolved_description = default_product.get("description", "")
            if not resolved_images:
                resolved_images = default_product.get("images", [])
            if not resolved_category:
                resolved_category = default_product.get(
                    "category", "mechanical_keyboard_keychain"
                )
            if not resolved_mechanics:
                resolved_mechanics = default_product.get("mechanics", "")
        except FileNotFoundError as e:
            logger.warning(f"Default product load failed: {e}")

    # Validate required product images
    if not resolved_images:
        raise ValueError(
            "Product images are required for video generation (none provided and default product could not be loaded)"
        )

    return PipelineState(
        job_id=job_id or str(uuid.uuid4()),
        status="pending",
        current_step="initializing",
        error="",
        video_url=video_url,
        product_description=resolved_description,
        product_images=resolved_images,
        product_identity_pack=product_identity_pack or {},
        product_category=resolved_category or "mechanical_keyboard_keychain",
        product_mechanics=resolved_mechanics,
        config=config or {},
        video_path="",
        frames=[],
        video_analysis={},
        video_prompt="",
        suggested_script="",
        scene_description="",
        prompt_validation={},
        scene_image_url="",
        i2v_image_url="",
        generated_video_url="",
    )


# Default configuration
DEFAULT_CONFIG = {
    "vision_model": "openai/gpt-4o-mini",  # OpenRouter vision model
    "num_frames": 5,
    "video_model": "sora",  # sora or kling
    "video_duration": 5,
    "aspect_ratio": "9:16",
    "i2v_image_index": 0,  # Which product image to use for I2V (0-indexed)
}
