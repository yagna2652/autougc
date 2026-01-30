"""
Data models for the Mechanics Engine.

Defines the structured output format for mechanics instructions
that get injected into Sora 2 prompts.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# PRODUCT CONTEXT MODEL
# =============================================================================


class ProductContext(BaseModel):
    """
    Rich product context for custom mechanics.

    Use this to provide detailed product-specific information that goes
    beyond generic category modifiers. This enables the mechanics engine
    to generate product-specific instructions like tactile feedback,
    sound features, and custom interactions.
    """

    type: str = Field(
        default="", description="Product type (e.g., 'mechanical keyboard fidget keychain')"
    )
    interactions: list[str] = Field(
        default_factory=list,
        description="Specific interactions (e.g., ['pressing keys', 'clicking switches'])",
    )
    tactile_features: list[str] = Field(
        default_factory=list,
        description="Tactile features (e.g., ['responsive keys', 'satisfying press'])",
    )
    sound_features: list[str] = Field(
        default_factory=list,
        description="Sound features (e.g., ['click sounds', 'key press audio'])",
    )
    size_description: str = Field(
        default="", description="Size context (e.g., 'small handheld, palm-sized')"
    )
    highlight_feature: str = Field(
        default="", description="Primary feature to highlight (e.g., 'the clicking action')"
    )
    custom_instructions: str = Field(
        default="", description="Free-form additional context for the product"
    )


class SegmentType(str, Enum):
    """Types of video segments."""

    HOOK = "hook"
    BODY = "body"
    CTA = "cta"


class HandPosition(str, Enum):
    """Common hand positions for UGC videos."""

    AT_SIDES = "at_sides"
    HOLDING_PRODUCT = "holding_product"
    GESTURING = "gesturing"
    POINTING = "pointing"
    ON_FACE = "on_face"
    COUNTING = "counting"
    WAVING = "waving"
    DEMONSTRATING = "demonstrating"
    REACHING = "reaching"
    RESTING = "resting"


class ExpressionState(str, Enum):
    """Facial expression states."""

    NEUTRAL = "neutral"
    SOFT_SMILE = "soft_smile"
    EXCITED_SMILE = "excited_smile"
    RAISED_EYEBROWS = "raised_eyebrows"
    THINKING = "thinking"
    SURPRISED = "surprised"
    GENUINE_WARMTH = "genuine_warmth"
    CURIOUS = "curious"
    SATISFIED = "satisfied"
    EMPHATIC = "emphatic"


class BodyPosture(str, Enum):
    """Body posture states."""

    UPRIGHT = "upright"
    LEANING_FORWARD = "leaning_forward"
    LEANING_BACK = "leaning_back"
    TURNING = "turning"
    NODDING = "nodding"
    SHRUGGING = "shrugging"


class EyeDirection(str, Enum):
    """Eye direction states."""

    AT_CAMERA = "at_camera"
    AT_PRODUCT = "at_product"
    GLANCING_AWAY = "glancing_away"
    LOOKING_DOWN = "looking_down"
    LOOKING_UP = "looking_up"


# =============================================================================
# MECHANICS COMPONENT MODELS
# =============================================================================


class HandMechanics(BaseModel):
    """Hand position and movement instructions."""

    position: HandPosition = Field(..., description="Hand position state")
    description: str = Field(..., description="Detailed hand movement description")
    which_hand: str = Field(default="both", description="Which hand (left, right, both)")
    movement: str = Field(default="", description="Movement description (rises, rotates, etc.)")
    holds_product: bool = Field(default=False, description="Whether hand is holding product")
    product_angle: str = Field(default="", description="Angle of product if held")


class ExpressionMechanics(BaseModel):
    """Facial expression instructions."""

    state: ExpressionState = Field(..., description="Expression state")
    description: str = Field(..., description="Detailed expression description")
    transition_from: Optional[ExpressionState] = Field(
        default=None, description="Previous expression state for transition"
    )
    transition_desc: str = Field(
        default="", description="How the expression transitions (e.g., 'softens to')"
    )
    micro_expressions: list[str] = Field(
        default_factory=list, description="Subtle micro-expressions to include"
    )


class BodyMechanics(BaseModel):
    """Body posture and movement instructions."""

    posture: BodyPosture = Field(..., description="Body posture state")
    description: str = Field(..., description="Detailed body position description")
    movement: str = Field(default="", description="Body movement (subtle sway, lean, etc.)")
    natural_tremor: bool = Field(
        default=False, description="Include natural micro-movements/tremor"
    )


class EyeMechanics(BaseModel):
    """Eye direction and movement instructions."""

    direction: EyeDirection = Field(..., description="Where eyes are looking")
    description: str = Field(..., description="Detailed eye behavior description")
    blink_pattern: str = Field(
        default="natural", description="Blink pattern (natural, slow, rapid)"
    )
    glance_pattern: str = Field(
        default="", description="Pattern of glances (between phone and product, etc.)"
    )


class ProductMechanics(BaseModel):
    """Product handling instructions."""

    visible: bool = Field(..., description="Whether product is visible in segment")
    interaction: str = Field(
        default="", description="How person interacts with product"
    )
    position_in_frame: str = Field(
        default="", description="Where product appears in frame"
    )
    demonstration: str = Field(
        default="", description="Demonstration action if applicable"
    )
    reveal_style: str = Field(
        default="", description="How product is revealed (from below frame, etc.)"
    )
    # Custom product context fields
    tactile_instruction: str = Field(
        default="", description="Tactile feedback instruction (e.g., 'press keys to show tactile response')"
    )
    sound_instruction: str = Field(
        default="", description="Sound-related instruction (e.g., 'emphasize click sounds')"
    )
    size_instruction: str = Field(
        default="", description="Size/scale instruction (e.g., 'show palm-sized scale')"
    )


# =============================================================================
# TIMELINE MODELS
# =============================================================================


class SceneMechanics(BaseModel):
    """Complete mechanics instructions for a single time segment."""

    segment_type: SegmentType = Field(..., description="Type of segment (hook/body/cta)")
    start_time: float = Field(..., description="Start time in seconds")
    end_time: float = Field(..., description="End time in seconds")
    label: str = Field(default="", description="Segment label for prompt")

    # Component mechanics
    hands: HandMechanics = Field(..., description="Hand mechanics")
    expression: ExpressionMechanics = Field(..., description="Expression mechanics")
    body: BodyMechanics = Field(..., description="Body mechanics")
    eyes: EyeMechanics = Field(..., description="Eye mechanics")
    product: Optional[ProductMechanics] = Field(
        default=None, description="Product mechanics if applicable"
    )

    # Additional instructions
    speaking_style: str = Field(
        default="", description="How dialogue should be delivered"
    )
    energy_level: str = Field(
        default="medium", description="Energy level (low, medium, high)"
    )
    key_action: str = Field(
        default="", description="Primary action happening in this segment"
    )

    def to_prompt_block(self) -> str:
        """Convert segment mechanics to a formatted prompt block."""
        lines = [f"[{self.start_time:.1f}-{self.end_time:.1f}s {self.segment_type.value.upper()}]"]

        lines.append(f"HANDS: {self.hands.description}")
        lines.append(f"EXPRESSION: {self.expression.description}")
        lines.append(f"EYES: {self.eyes.description}")
        lines.append(f"BODY: {self.body.description}")

        if self.product and self.product.visible:
            lines.append(f"PRODUCT: {self.product.interaction}")

        if self.key_action:
            lines.append(f"ACTION: {self.key_action}")

        return "\n".join(lines)


class VideoConfig(BaseModel):
    """Configuration for target video generation."""

    duration: float = Field(default=8.0, description="Target video duration in seconds")
    hook_duration: float = Field(default=2.0, description="Hook segment duration")
    cta_duration: float = Field(default=1.5, description="CTA segment duration")
    has_product: bool = Field(default=True, description="Whether video features a product")
    product_category: str = Field(
        default="general", description="Product category (skincare, supplement, tech, etc.)"
    )
    product_context: Optional[ProductContext] = Field(
        default=None,
        description="Rich product context for custom mechanics beyond generic categories",
    )
    energy_level: str = Field(
        default="medium", description="Overall energy level"
    )
    setting: str = Field(default="bedroom", description="Video setting")


class MechanicsTimeline(BaseModel):
    """Complete mechanics timeline for a video."""

    config: VideoConfig = Field(..., description="Video configuration")
    segments: list[SceneMechanics] = Field(..., description="Ordered list of segment mechanics")
    total_duration: float = Field(..., description="Total video duration")

    # Metadata
    source_blueprint_id: str = Field(
        default="", description="ID of source blueprint if applicable"
    )
    generation_notes: list[str] = Field(
        default_factory=list, description="Notes about how mechanics were generated"
    )

    def to_mechanics_prompt(self) -> str:
        """Convert full timeline to mechanics-enhanced prompt section."""
        blocks = []
        for segment in self.segments:
            blocks.append(segment.to_prompt_block())
        return "\n\n".join(blocks)

    def get_segment_by_type(self, segment_type: SegmentType) -> list[SceneMechanics]:
        """Get all segments of a specific type."""
        return [s for s in self.segments if s.segment_type == segment_type]
