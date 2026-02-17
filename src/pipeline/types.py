"""
Pipeline Type Definitions - Strongly typed data structures for pipeline nodes.

These TypedDict classes provide type safety and IDE autocompletion for
the data structures flowing through the pipeline.
"""

from typing import Literal, TypedDict


# =============================================================================
# Video Analysis Types
# =============================================================================


class CameraInfo(TypedDict, total=False):
    """Camera framing and movement information."""

    framing: Literal["close-up", "medium", "full body"] | str
    angle: Literal["eye-level", "above", "below"] | str
    movement: Literal["handheld", "stable", "slight movement"] | str


class PersonInfo(TypedDict, total=False):
    """Information about the person in the video."""

    age_range: str  # e.g., "20-25"
    gender: str
    appearance: str  # clothing, hair, makeup description
    vibe: Literal["casual", "polished", "energetic"] | str


class VideoAnalysisData(TypedDict, total=False):
    """
    Output from analyze_video node - Vision model analysis of video frames.

    Contains detailed breakdown of the video's visual style, setting,
    and characteristics for recreation.
    """

    setting: str  # Where the video is filmed
    lighting: str  # Lighting description
    camera: CameraInfo  # Camera framing and movement
    person: PersonInfo  # Person details (if present)
    actions: str  # What the person is doing
    style: str  # Overall video style/aesthetic
    energy: Literal["high", "medium", "low"] | str
    mood: str  # Emotional tone
    text_overlays: str  # Description of on-screen text
    what_makes_it_work: str  # Why this style is effective for UGC

    # May contain raw response if parsing partially failed
    raw_response: str


# =============================================================================
# Configuration Types
# =============================================================================


class ProductReference(TypedDict, total=False):
    """Product identity pack - multi-angle reference images for SKU."""

    front: str  # Front view image (base64 or URL)
    side_45: str  # 45-degree angle view
    back: str  # Back view
    top: str  # Top view
    close_up_logo: str  # Close-up of logo/markings
    close_up_material: str  # Close-up of material texture


class PipelineConfig(TypedDict, total=False):
    """Configuration options for the pipeline."""

    vision_model: str  # e.g., "openai/gpt-4o-mini"
    num_frames: int  # Number of frames to extract
    video_model: Literal["sora", "kling", "kling-v3"] | str
    video_duration: int  # Duration in seconds
    aspect_ratio: str  # e.g., "9:16"
    i2v_image_index: int  # Which product image to use for I2V

    # Identity fidelity controls (fastest gains)
    use_identity_pack: bool  # Enable multi-reference identity pack
    use_tail_image: bool  # Use same image as end frame (forces consistency)
    segment_duration: int  # Duration per segment for anchor strategy (2-3s)
    use_anchor_frames: bool  # Generate keyframes first, then motion
