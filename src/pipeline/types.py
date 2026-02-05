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
    Output from analyze_video node - Claude Vision analysis of video frames.

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


class PipelineConfig(TypedDict, total=False):
    """Configuration options for the pipeline."""

    claude_model: str  # e.g., "claude-sonnet-4-20250514"
    num_frames: int  # Number of frames to extract
    video_model: Literal["sora", "kling"] | str
    video_duration: int  # Duration in seconds
    aspect_ratio: str  # e.g., "9:16"
    i2v_image_index: int  # Which product image to use for I2V
