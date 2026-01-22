"""
Data models for Video Blueprint - the structured output of video analysis.

Enhanced with:
- Scene-by-scene breakdown
- Action/gesture annotations
- Product placement tracking
- Shot type classification
- Pacing metrics
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class HookStyle(str, Enum):
    """Common hook styles used in TikTok/Reels."""

    POV_TREND = "pov_trend"
    REVELATION = "revelation"
    QUESTION = "question"
    CONTROVERSIAL = "controversial"
    STORY_START = "story_start"
    CURIOSITY_GAP = "curiosity_gap"
    PATTERN_INTERRUPT = "pattern_interrupt"
    RELATABLE = "relatable"
    SHOCK = "shock"
    OTHER = "other"


class BodyFramework(str, Enum):
    """Content frameworks for the body section."""

    TESTIMONIAL = "testimonial"
    EDUCATION = "education"
    PROBLEM_AGITATION = "problem_agitation"
    DEMONSTRATION = "demonstration"
    SOCIAL_PROOF = "social_proof"
    STORYTELLING = "storytelling"
    COMPARISON = "comparison"
    TUTORIAL = "tutorial"
    BEHIND_THE_SCENES = "behind_the_scenes"
    OTHER = "other"


class CTAUrgency(str, Enum):
    """CTA urgency levels."""

    SOFT = "soft"
    MEDIUM = "medium"
    URGENT = "urgent"
    FOMO = "fomo"
    DISCOUNT = "discount"
    CURIOSITY = "curiosity"
    DIRECT = "direct"


class ShotType(str, Enum):
    """Types of camera shots."""

    EXTREME_CLOSE_UP = "extreme_close_up"  # Face detail, product detail
    CLOSE_UP = "close_up"  # Head and shoulders
    MEDIUM_CLOSE_UP = "medium_close_up"  # Chest up
    MEDIUM_SHOT = "medium_shot"  # Waist up
    MEDIUM_WIDE = "medium_wide"  # Knees up
    WIDE_SHOT = "wide_shot"  # Full body
    EXTREME_WIDE = "extreme_wide"  # Environment shot
    PRODUCT_SHOT = "product_shot"  # Focused on product
    SCREEN_RECORDING = "screen_recording"  # App/website capture
    TEXT_CARD = "text_card"  # Text only frame


class SceneType(str, Enum):
    """Types of scenes in UGC content."""

    TALKING_HEAD = "talking_head"  # Person speaking to camera
    DEMONSTRATION = "demonstration"  # Showing how to use product
    B_ROLL = "b_roll"  # Supplementary footage
    PRODUCT_SHOWCASE = "product_showcase"  # Focused product display
    BEFORE_AFTER = "before_after"  # Comparison shot
    TESTIMONIAL = "testimonial"  # Speaking about experience
    LIFESTYLE = "lifestyle"  # Product in use naturally
    UNBOXING = "unboxing"  # Opening/revealing product
    TRANSITION = "transition"  # Movement between locations
    REACTION = "reaction"  # Emotional response shot
    TEXT_OVERLAY = "text_overlay"  # Text-heavy informational


class TransitionType(str, Enum):
    """Types of transitions between scenes."""

    CUT = "cut"  # Direct cut
    JUMP_CUT = "jump_cut"  # Same angle, time skip
    SWIPE = "swipe"  # Swipe transition
    ZOOM = "zoom"  # Zoom in/out transition
    FADE = "fade"  # Fade in/out
    WHIP_PAN = "whip_pan"  # Fast pan
    MATCH_CUT = "match_cut"  # Matching action/shape
    HAND_COVER = "hand_cover"  # Hand covers camera
    NONE = "none"  # No transition (continuous)


class GestureType(str, Enum):
    """Common gestures in UGC content."""

    POINTING = "pointing"
    WAVING = "waving"
    THUMBS_UP = "thumbs_up"
    HOLDING_PRODUCT = "holding_product"
    APPLYING_PRODUCT = "applying_product"
    EATING_DRINKING = "eating_drinking"
    HAND_ON_FACE = "hand_on_face"
    COUNTING_FINGERS = "counting_fingers"
    SHRUGGING = "shrugging"
    CLAPPING = "clapping"
    DANCING = "dancing"
    WALKING = "walking"
    SITTING = "sitting"
    STANDING = "standing"
    LEANING_IN = "leaning_in"
    LOOKING_AWAY = "looking_away"
    OTHER = "other"


class FacialExpression(str, Enum):
    """Common facial expressions."""

    NEUTRAL = "neutral"
    SMILING = "smiling"
    EXCITED = "excited"
    SURPRISED = "surprised"
    SKEPTICAL = "skeptical"
    CONCERNED = "concerned"
    THINKING = "thinking"
    LAUGHING = "laughing"
    SERIOUS = "serious"
    DISAPPOINTED = "disappointed"
    SATISFIED = "satisfied"
    OTHER = "other"


class TranscriptSegment(BaseModel):
    """A single segment of the transcript with timing."""

    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcribed text for this segment")
    word_count: int = Field(default=0, description="Number of words in segment")
    emphasis_words: list[str] = Field(
        default_factory=list, description="Words that should be emphasized"
    )


# =============================================================================
# ACTION & GESTURE MODELS
# =============================================================================


class ActionCue(BaseModel):
    """A specific action or gesture at a point in time."""

    timestamp: float = Field(..., description="When the action occurs (seconds)")
    duration: float = Field(default=1.0, description="How long the action lasts")
    gesture: GestureType = Field(..., description="Type of gesture/action")
    description: str = Field(..., description="Detailed description of the action")
    body_parts: list[str] = Field(
        default_factory=list, description="Body parts involved (hands, face, etc.)"
    )
    direction: str = Field(
        default="", description="Direction of movement (toward camera, left, etc.)"
    )
    intensity: str = Field(
        default="medium", description="Intensity level (subtle, medium, exaggerated)"
    )


class ExpressionCue(BaseModel):
    """Facial expression at a point in time."""

    timestamp: float = Field(..., description="When the expression occurs")
    duration: float = Field(default=1.0, description="How long the expression lasts")
    expression: FacialExpression = Field(..., description="Type of expression")
    description: str = Field(default="", description="Additional expression details")
    eye_contact: bool = Field(default=True, description="Whether looking at camera")


# =============================================================================
# SCENE MODELS
# =============================================================================


class SceneTransition(BaseModel):
    """Transition between two scenes."""

    type: TransitionType = Field(..., description="Type of transition")
    duration: float = Field(default=0.0, description="Transition duration in seconds")
    description: str = Field(default="", description="Additional transition details")


class ProductAppearance(BaseModel):
    """When and how a product appears in a scene."""

    timestamp: float = Field(..., description="When product appears")
    duration: float = Field(..., description="How long product is visible")
    product_name: str = Field(default="", description="Name/type of product if known")
    visibility: str = Field(
        default="full", description="Visibility level (full, partial, background)"
    )
    interaction: str = Field(
        default="none",
        description="How person interacts (holding, using, pointing at, etc.)",
    )
    position_in_frame: str = Field(
        default="center", description="Where in frame (center, left, right, etc.)"
    )
    shot_type: ShotType = Field(
        default=ShotType.MEDIUM_SHOT, description="Shot type during appearance"
    )
    is_demo: bool = Field(
        default=False, description="Whether this is a demonstration moment"
    )
    description: str = Field(default="", description="Additional details")


class Scene(BaseModel):
    """A distinct scene or shot in the video."""

    scene_number: int = Field(..., description="Sequential scene number")
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    duration: float = Field(..., description="Scene duration in seconds")

    # Scene classification
    scene_type: SceneType = Field(..., description="Type of scene")
    shot_type: ShotType = Field(..., description="Camera shot type")

    # Location & setting
    location: str = Field(default="", description="Where this scene takes place")
    setting_change: bool = Field(
        default=False, description="Whether location changed from previous scene"
    )

    # Content
    transcript_text: str = Field(
        default="", description="What is said during this scene"
    )
    on_screen_text: list[str] = Field(
        default_factory=list, description="Text overlays in this scene"
    )

    # Visual details
    framing_description: str = Field(default="", description="Detailed framing notes")
    camera_movement: str = Field(
        default="static", description="Camera movement in this scene"
    )
    lighting_notes: str = Field(default="", description="Lighting specific to scene")

    # People & actions
    people_visible: int = Field(default=1, description="Number of people visible")
    speaker: str = Field(
        default="main", description="Who is speaking (main, secondary, none)"
    )
    actions: list[ActionCue] = Field(
        default_factory=list, description="Actions/gestures in this scene"
    )
    expressions: list[ExpressionCue] = Field(
        default_factory=list, description="Facial expressions in this scene"
    )

    # Product
    product_appearances: list[ProductAppearance] = Field(
        default_factory=list, description="Product appearances in this scene"
    )

    # Transition
    transition_in: Optional[SceneTransition] = Field(
        default=None, description="How this scene starts"
    )
    transition_out: Optional[SceneTransition] = Field(
        default=None, description="How this scene ends"
    )

    # Recreation instructions
    recreation_instruction: str = Field(
        default="", description="Specific instruction to recreate this scene"
    )


class SceneBreakdown(BaseModel):
    """Complete scene-by-scene breakdown of the video."""

    total_scenes: int = Field(..., description="Total number of scenes")
    scenes: list[Scene] = Field(..., description="List of all scenes")
    scene_types_summary: dict[str, int] = Field(
        default_factory=dict, description="Count of each scene type"
    )
    avg_scene_duration: float = Field(
        default=0.0, description="Average scene duration in seconds"
    )
    location_changes: int = Field(default=0, description="Number of location changes")


# =============================================================================
# PRODUCT TRACKING MODELS
# =============================================================================


class ProductInfo(BaseModel):
    """Information about a product featured in the video."""

    name: str = Field(default="", description="Product name if identifiable")
    brand: str = Field(default="", description="Brand name if identifiable")
    category: str = Field(default="", description="Product category")
    total_screen_time: float = Field(
        default=0.0, description="Total seconds product is visible"
    )
    first_appearance: float = Field(
        default=0.0, description="When product first appears"
    )
    demo_moments: list[float] = Field(
        default_factory=list, description="Timestamps of demo moments"
    )
    key_features_shown: list[str] = Field(
        default_factory=list, description="Product features highlighted"
    )
    appearance_count: int = Field(
        default=0, description="Number of times product appears"
    )


class ProductTracking(BaseModel):
    """Tracking of all products in the video."""

    products: list[ProductInfo] = Field(
        default_factory=list, description="All products identified"
    )
    primary_product: Optional[ProductInfo] = Field(
        default=None, description="Main product being promoted"
    )
    total_product_screen_time: float = Field(
        default=0.0, description="Total time any product is visible"
    )
    product_to_content_ratio: float = Field(
        default=0.0, description="Ratio of product time to total duration"
    )


# =============================================================================
# PACING MODELS
# =============================================================================


class PacingMetrics(BaseModel):
    """Detailed pacing and timing metrics."""

    # Speech metrics
    total_word_count: int = Field(default=0, description="Total words spoken")
    words_per_minute: float = Field(default=0.0, description="Speaking rate WPM")
    speaking_time: float = Field(
        default=0.0, description="Total time spent speaking (seconds)"
    )
    silence_time: float = Field(
        default=0.0, description="Total silence duration (seconds)"
    )
    speaking_ratio: float = Field(
        default=0.0, description="Ratio of speaking to total duration"
    )

    # Pause analysis
    pauses: list[dict] = Field(
        default_factory=list,
        description="List of pauses with start, end, duration, and type",
    )
    avg_pause_duration: float = Field(default=0.0, description="Average pause duration")
    longest_pause: float = Field(default=0.0, description="Longest pause duration")

    # Segment pacing
    hook_wpm: float = Field(default=0.0, description="WPM during hook section")
    body_wpm: float = Field(default=0.0, description="WPM during body section")
    cta_wpm: float = Field(default=0.0, description="WPM during CTA section")

    # Emphasis
    emphasis_points: list[dict] = Field(
        default_factory=list,
        description="Words/phrases to emphasize with timestamps",
    )

    # Scene pacing
    cuts_per_minute: float = Field(
        default=0.0, description="Number of scene cuts per minute"
    )
    fastest_scene: float = Field(default=0.0, description="Duration of shortest scene")
    slowest_scene: float = Field(default=0.0, description="Duration of longest scene")


class Transcript(BaseModel):
    """Full transcript with word-level or segment-level timing."""

    full_text: str = Field(..., description="Complete transcript as single string")
    segments: list[TranscriptSegment] = Field(
        default_factory=list, description="Timed segments of the transcript"
    )
    language: str = Field(default="en", description="Detected language code")
    confidence: Optional[float] = Field(
        default=None, description="Overall transcription confidence score"
    )


class HookSection(BaseModel):
    """The hook section of the video (first few seconds)."""

    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Script/transcript for the hook")
    style: HookStyle = Field(..., description="Identified hook style")
    style_reasoning: str = Field(
        default="", description="Why this hook style was identified"
    )


class BodySection(BaseModel):
    """The body/main content section of the video."""

    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Script/transcript for the body")
    framework: BodyFramework = Field(..., description="Content framework used")
    framework_reasoning: str = Field(
        default="", description="Why this framework was identified"
    )
    key_points: list[str] = Field(
        default_factory=list, description="Main points covered in the body"
    )


class CTASection(BaseModel):
    """The call-to-action section (usually last few seconds)."""

    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Script/transcript for the CTA")
    urgency: CTAUrgency = Field(..., description="Urgency level of the CTA")
    action_requested: str = Field(
        default="", description="What action the viewer is asked to take"
    )


class VideoStructure(BaseModel):
    """The overall structure breakdown of the video."""

    hook: HookSection = Field(..., description="Hook section analysis")
    body: BodySection = Field(..., description="Body section analysis")
    cta: CTASection = Field(..., description="CTA section analysis")
    total_duration: float = Field(..., description="Total video duration in seconds")


class TextOverlay(BaseModel):
    """On-screen text overlay detected in the video."""

    text: str = Field(..., description="The text content")
    timestamp: float = Field(..., description="When the text appears (seconds)")
    duration: Optional[float] = Field(
        default=None, description="How long the text is visible"
    )
    position: str = Field(
        default="center", description="Position on screen (top, center, bottom, etc.)"
    )
    style_description: str = Field(
        default="", description="Visual style of the text (font, color, effects)"
    )


class AvatarAppearance(BaseModel):
    """Detailed appearance attributes of the person in the video."""

    age_range: str = Field(default="", description="Estimated age range")
    gender: str = Field(default="", description="Perceived gender")
    ethnicity: str = Field(default="", description="Perceived ethnicity")
    hair: str = Field(default="", description="Hair description")
    clothing: str = Field(default="", description="Clothing description")
    makeup: str = Field(default="", description="Makeup description")
    accessories: str = Field(default="", description="Accessories worn")


class VisualStyle(BaseModel):
    """Visual style analysis of the video."""

    setting: str = Field(
        ..., description="Where the video takes place (bedroom, studio, outdoors, etc.)"
    )
    lighting: str = Field(
        ..., description="Lighting style (natural, ring light, dramatic, etc.)"
    )
    framing: str = Field(
        ..., description="Camera framing (close-up, medium shot, full body, etc.)"
    )
    avatar_description: str = Field(
        ..., description="Description of the person in the video"
    )
    avatar_appearance: AvatarAppearance = Field(
        default_factory=AvatarAppearance,
        description="Detailed appearance attributes",
    )
    background: str = Field(..., description="Background description")
    camera_movement: str = Field(
        default="static",
        description="Camera movement style (static, handheld, panning, etc.)",
    )
    color_palette: str = Field(
        default="", description="Dominant colors and overall color mood"
    )
    text_overlays: list[TextOverlay] = Field(
        default_factory=list, description="On-screen text detected"
    )
    visual_effects: list[str] = Field(
        default_factory=list, description="Any visual effects or transitions used"
    )


class AudioStyle(BaseModel):
    """Audio style analysis of the video."""

    voice_tone: str = Field(
        ..., description="Tone of voice (casual, energetic, calm, authoritative, etc.)"
    )
    pacing: str = Field(..., description="Speech pacing (slow, medium, fast, varied)")
    energy_level: str = Field(
        default="medium", description="Overall energy (low, medium, high)"
    )
    has_background_music: bool = Field(
        default=False, description="Whether background music is present"
    )
    music_description: Optional[str] = Field(
        default=None, description="Description of background music if present"
    )
    has_sound_effects: bool = Field(
        default=False, description="Whether sound effects are used"
    )
    sound_effects: list[str] = Field(
        default_factory=list, description="List of sound effects detected"
    )


class EngagementAnalysis(BaseModel):
    """Analysis of what makes this video engaging."""

    hook_technique: str = Field(
        ..., description="What technique the hook uses to grab attention"
    )
    retention_tactics: list[str] = Field(
        default_factory=list, description="Tactics used to keep viewers watching"
    )
    cta_approach: str = Field(..., description="How the CTA is delivered")
    emotional_triggers: list[str] = Field(
        default_factory=list,
        description="Emotional triggers used (curiosity, FOMO, aspiration, etc.)",
    )
    target_audience_signals: list[str] = Field(
        default_factory=list, description="Signals indicating who this video targets"
    )
    virality_factors: list[str] = Field(
        default_factory=list, description="Elements that could contribute to virality"
    )


class VideoBlueprint(BaseModel):
    """
    Complete blueprint of an analyzed video.
    Contains everything needed to recreate a similar video.
    """

    # Metadata
    source_video: str = Field(..., description="Path or identifier of source video")
    analysis_version: str = Field(default="2.0", description="Blueprint schema version")

    # Core content
    transcript: Transcript = Field(..., description="Full transcript with timing")
    structure: VideoStructure = Field(..., description="Hook/Body/CTA breakdown")

    # Style analysis
    visual_style: VisualStyle = Field(..., description="Visual style analysis")
    audio_style: AudioStyle = Field(..., description="Audio style analysis")

    # Strategic analysis
    engagement_analysis: EngagementAnalysis = Field(
        ..., description="What makes this video work"
    )

    # Enhanced analysis (v2.0)
    scene_breakdown: Optional[SceneBreakdown] = Field(
        default=None, description="Scene-by-scene breakdown"
    )
    product_tracking: Optional[ProductTracking] = Field(
        default=None, description="Product appearance tracking"
    )
    pacing_metrics: Optional[PacingMetrics] = Field(
        default=None, description="Detailed pacing analysis"
    )

    # Recreation hints
    recreation_notes: list[str] = Field(
        default_factory=list, description="Notes for recreating this video style"
    )

    # Scene-level recreation script
    recreation_script: list[str] = Field(
        default_factory=list,
        description="Step-by-step recreation instructions per scene",
    )

    def to_json(self, indent: int = 2) -> str:
        """Export blueprint as formatted JSON string."""
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "VideoBlueprint":
        """Load blueprint from JSON string."""
        return cls.model_validate_json(json_str)

    def save(self, path: str) -> None:
        """Save blueprint to a JSON file."""
        with open(path, "w") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls, path: str) -> "VideoBlueprint":
        """Load blueprint from a JSON file."""
        with open(path, "r") as f:
            return cls.from_json(f.read())
