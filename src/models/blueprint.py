"""
Data models for Video Blueprint - the structured output of video analysis.
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


class TranscriptSegment(BaseModel):
    """A single segment of the transcript with timing."""

    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Transcribed text for this segment")


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
    analysis_version: str = Field(default="1.0", description="Blueprint schema version")

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

    # Recreation hints
    recreation_notes: list[str] = Field(
        default_factory=list, description="Notes for recreating this video style"
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
