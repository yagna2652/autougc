"""
Simple Pipeline State for UGC Video Generation.

Minimal state that flows through the pipeline:
1. Download TikTok
2. Extract frames
3. Analyze with Claude Vision
4. Generate prompt
5. Generate video
"""

from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    """
    Minimal state for the UGC pipeline.

    All fields are optional (total=False) to allow partial updates.
    """

    # Job tracking
    job_id: str
    status: str  # pending, running, completed, failed
    current_step: str
    error: str

    # Input
    video_url: str
    product_description: str
    product_images: list[str]  # base64 or URLs

    # Config
    config: dict[str, Any]

    # Pipeline data (populated as we go)
    video_path: str  # Downloaded video file path
    frames: list[str]  # List of extracted frame paths
    video_analysis: dict[str, Any]  # Claude Vision analysis
    video_prompt: str  # Generated prompt for video API
    suggested_script: str  # Suggested script/voiceover

    # Output
    generated_video_url: str  # Final video URL


def create_initial_state(
    video_url: str,
    product_description: str = "",
    product_images: list[str] | None = None,
    config: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> PipelineState:
    """
    Create initial pipeline state.

    Args:
        video_url: TikTok URL to analyze
        product_description: Description of product to feature
        product_images: Optional product images (base64 or URLs)
        config: Optional configuration overrides
        job_id: Optional job ID (generated if not provided)

    Returns:
        Initial PipelineState
    """
    import uuid

    return PipelineState(
        job_id=job_id or str(uuid.uuid4()),
        status="pending",
        current_step="initializing",
        error="",
        video_url=video_url,
        product_description=product_description,
        product_images=product_images or [],
        config=config or {},
        video_path="",
        frames=[],
        video_analysis={},
        video_prompt="",
        suggested_script="",
        generated_video_url="",
    )


# Default configuration
DEFAULT_CONFIG = {
    "claude_model": "claude-sonnet-4-20250514",
    "num_frames": 5,
    "video_model": "sora",  # sora or kling
    "video_duration": 5,
    "aspect_ratio": "9:16",
}
