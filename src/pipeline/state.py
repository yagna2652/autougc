"""
Pipeline State Definition for LangGraph.

This module defines the complete state that flows through the UGC generation pipeline.
Using TypedDict for compatibility with LangGraph's state management.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, TypedDict


class PipelineStatus(str, Enum):
    """Pipeline execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"  # For human-in-the-loop
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStep(str, Enum):
    """Pipeline steps for progress tracking."""

    INITIALIZING = "initializing"
    DOWNLOADING_VIDEO = "downloading_video"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    EXTRACTING_FRAMES = "extracting_frames"
    ANALYZING_VISUALS = "analyzing_visuals"
    GENERATING_BLUEPRINT = "generating_blueprint"
    ANALYZING_PRODUCT = "analyzing_product"
    GENERATING_BASE_PROMPT = "generating_base_prompt"
    GENERATING_MECHANICS = "generating_mechanics"
    FINALIZING_PROMPT = "finalizing_prompt"
    GENERATING_VIDEO = "generating_video"
    COMPLETED = "completed"


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""

    # Analysis settings
    whisper_mode: str = "local"
    whisper_model: str = "base"
    claude_model: str = "claude-sonnet-4-20250514"
    num_frames: int = 5
    num_frames_for_scenes: int = 20
    enable_enhanced_analysis: bool = True

    # Mechanics settings
    enable_mechanics: bool = True
    product_category: str = "general"
    target_duration: float = 8.0
    energy_level: str = "medium"

    # Video generation settings
    video_model: str = "sora2"  # sora2, sora2pro, kling
    video_duration: int = 5
    aspect_ratio: str = "9:16"
    use_image_to_video: bool = True

    # Pipeline behavior
    keep_temp_files: bool = False
    timeout_seconds: int = 300


class ProductContext(TypedDict, total=False):
    """Rich product context for custom mechanics."""

    type: str
    interactions: list[str]
    tactile_features: list[str]
    sound_features: list[str]
    size_description: str
    highlight_feature: str
    custom_instructions: str


class TranscriptSegment(TypedDict):
    """A single segment of the transcript with timing."""

    start: float
    end: float
    text: str


class Transcript(TypedDict, total=False):
    """Transcript data from speech-to-text."""

    full_text: str
    segments: list[TranscriptSegment]
    language: str
    confidence: float


class BlueprintSummary(TypedDict, total=False):
    """Simplified blueprint data for UI display."""

    transcript: str
    hook_style: str
    body_framework: str
    cta_urgency: str
    setting: str
    lighting: str
    energy: str
    duration: float


class ProductAnalysis(TypedDict, total=False):
    """Product analysis results from Claude Vision."""

    type: str
    description: str
    key_features: list[str]
    suggested_showcase: str


class ProgressInfo(TypedDict):
    """Progress information for UI updates."""

    step_number: int
    total_steps: int
    current_step: str
    percentage: float


class PipelineState(TypedDict, total=False):
    """
    Complete state for the UGC generation pipeline.

    This state flows through all nodes in the LangGraph pipeline.
    Each node reads from and writes to this state.

    Using total=False allows partial updates from nodes.
    """

    # =========================================================================
    # INPUT (provided at pipeline start)
    # =========================================================================

    # Video source
    video_url: str
    video_path: str  # Local path after download

    # Product information
    product_images: list[str]  # base64 encoded or URLs
    product_description: str
    product_context: ProductContext

    # Configuration
    config: dict[str, Any]  # Serialized PipelineConfig

    # =========================================================================
    # ANALYSIS OUTPUTS (populated by analysis nodes)
    # =========================================================================

    # Audio extraction
    audio_path: str

    # Transcription
    transcript: Transcript

    # Frame extraction
    frames: list[str]  # Paths to extracted frame images
    frames_base64: list[str]  # Base64 encoded frames for API calls

    # Visual analysis
    visual_analysis: dict[str, Any]

    # Scene segmentation (enhanced analysis)
    scenes: list[dict[str, Any]]

    # Pacing analysis (enhanced analysis)
    pacing: dict[str, Any]

    # Product tracking (enhanced analysis)
    product_tracking: dict[str, Any]

    # =========================================================================
    # BLUEPRINT (core output of analysis phase)
    # =========================================================================

    # Full blueprint (for mechanics engine)
    blueprint: dict[str, Any]

    # Simplified blueprint (for UI)
    blueprint_summary: BlueprintSummary

    # =========================================================================
    # PRODUCT ANALYSIS (populated by product analysis node)
    # =========================================================================

    product_analysis: ProductAnalysis

    # =========================================================================
    # PROMPT GENERATION (populated by prompt nodes)
    # =========================================================================

    # Base prompt from Claude (without mechanics)
    base_prompt: str

    # Suggested script for the video
    suggested_script: str

    # Mechanics-enhanced prompt (detailed human movements)
    mechanics_prompt: str

    # Mechanics timeline data
    mechanics_timeline: dict[str, Any]

    # Final prompt to use for video generation
    # This is either mechanics_prompt (if enabled) or base_prompt
    final_prompt: str

    # =========================================================================
    # VIDEO GENERATION (populated by video generation node)
    # =========================================================================

    # Starting frame for image-to-video
    starting_frame_url: str

    # Uploaded product image URL (for Fal.ai)
    uploaded_image_url: str

    # Generated video URL
    generated_video_url: str

    # Video generation metadata
    video_metadata: dict[str, Any]

    # =========================================================================
    # PIPELINE METADATA
    # =========================================================================

    # Unique job identifier
    job_id: str

    # Current status
    status: str  # PipelineStatus value

    # Current step
    current_step: str  # PipelineStep value

    # Progress info for UI
    progress: ProgressInfo

    # Error information (if failed)
    error: str
    error_details: dict[str, Any]

    # Timestamps
    started_at: str  # ISO format
    completed_at: str  # ISO format

    # Temporary files to clean up
    temp_files: list[str]


def create_initial_state(
    video_url: str = "",
    product_images: list[str] | None = None,
    product_description: str = "",
    product_context: ProductContext | None = None,
    config: PipelineConfig | None = None,
    job_id: str = "",
) -> PipelineState:
    """
    Create an initial pipeline state with defaults.

    Args:
        video_url: URL of the TikTok/Reel to analyze
        product_images: List of product images (base64 or URLs)
        product_description: Text description of the product
        product_context: Rich product context for mechanics
        config: Pipeline configuration
        job_id: Unique job identifier

    Returns:
        Initialized PipelineState ready for pipeline execution
    """
    import uuid
    from datetime import datetime

    if config is None:
        config = PipelineConfig()

    return PipelineState(
        # Inputs
        video_url=video_url,
        video_path="",
        product_images=product_images or [],
        product_description=product_description,
        product_context=product_context or {},
        config={
            "whisper_mode": config.whisper_mode,
            "whisper_model": config.whisper_model,
            "claude_model": config.claude_model,
            "num_frames": config.num_frames,
            "num_frames_for_scenes": config.num_frames_for_scenes,
            "enable_enhanced_analysis": config.enable_enhanced_analysis,
            "enable_mechanics": config.enable_mechanics,
            "product_category": config.product_category,
            "target_duration": config.target_duration,
            "energy_level": config.energy_level,
            "video_model": config.video_model,
            "video_duration": config.video_duration,
            "aspect_ratio": config.aspect_ratio,
            "use_image_to_video": config.use_image_to_video,
            "keep_temp_files": config.keep_temp_files,
            "timeout_seconds": config.timeout_seconds,
        },
        # Analysis outputs (empty)
        audio_path="",
        transcript={},
        frames=[],
        frames_base64=[],
        visual_analysis={},
        scenes=[],
        pacing={},
        product_tracking={},
        # Blueprint (empty)
        blueprint={},
        blueprint_summary={},
        # Product analysis (empty)
        product_analysis={},
        # Prompts (empty)
        base_prompt="",
        suggested_script="",
        mechanics_prompt="",
        mechanics_timeline={},
        final_prompt="",
        # Video generation (empty)
        starting_frame_url="",
        uploaded_image_url="",
        generated_video_url="",
        video_metadata={},
        # Metadata
        job_id=job_id or str(uuid.uuid4()),
        status=PipelineStatus.PENDING.value,
        current_step=PipelineStep.INITIALIZING.value,
        progress=ProgressInfo(
            step_number=0,
            total_steps=12,
            current_step="Initializing",
            percentage=0.0,
        ),
        error="",
        error_details={},
        started_at=datetime.utcnow().isoformat(),
        completed_at="",
        temp_files=[],
    )


def update_progress(
    state: PipelineState,
    step: PipelineStep,
    step_number: int,
) -> dict[str, Any]:
    """
    Helper to create progress update for a pipeline step.

    Args:
        state: Current pipeline state
        step: The step being executed
        step_number: Current step number (1-indexed)

    Returns:
        Dict with progress update fields
    """
    total_steps = 12  # Total steps in the pipeline

    return {
        "current_step": step.value,
        "progress": ProgressInfo(
            step_number=step_number,
            total_steps=total_steps,
            current_step=step.value.replace("_", " ").title(),
            percentage=round((step_number / total_steps) * 100, 1),
        ),
    }


def mark_failed(
    state: PipelineState, error: str, details: dict | None = None
) -> dict[str, Any]:
    """
    Helper to mark pipeline as failed.

    Args:
        state: Current pipeline state
        error: Error message
        details: Optional error details

    Returns:
        Dict with failure update fields
    """
    from datetime import datetime

    return {
        "status": PipelineStatus.FAILED.value,
        "error": error,
        "error_details": details or {},
        "completed_at": datetime.utcnow().isoformat(),
    }


def mark_completed(state: PipelineState) -> dict[str, Any]:
    """
    Helper to mark pipeline as completed.

    Args:
        state: Current pipeline state

    Returns:
        Dict with completion update fields
    """
    from datetime import datetime

    return {
        "status": PipelineStatus.COMPLETED.value,
        "current_step": PipelineStep.COMPLETED.value,
        "completed_at": datetime.utcnow().isoformat(),
        "progress": ProgressInfo(
            step_number=12,
            total_steps=12,
            current_step="Completed",
            percentage=100.0,
        ),
    }
