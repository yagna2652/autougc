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
# UGC Intent Classification Types
# =============================================================================

# Literal types for classification categories
UGCArchetype = Literal[
    "testimonial",
    "problem_solution",
    "casual_review",
    "founder_rant",
    "storytime",
    "unboxing",
    "comparison",
    "educational_tip",
    "other",
]

PrimaryIntent = Literal[
    "build_trust",
    "explain_value",
    "spark_curiosity",
    "normalize_product_use",
    "social_proof",
    "other",
]

HookType = Literal[
    "relatable_problem",
    "bold_claim",
    "curiosity_gap",
    "emotional_statement",
    "none",
    "other",
]

NarrativeStructure = Literal[
    "hook_then_story",
    "story_then_reveal",
    "linear_explanation",
    "moment_in_time",
    "list_format",
    "other",
]

TrustMechanism = Literal[
    "personal_experience",
    "specificity",
    "authority",
    "vulnerability",
    "demonstration",
    "social_context",
    "other",
]

CTAStyle = Literal["soft_mention", "implicit", "direct_ask", "none", "other"]

EnergyLevel = Literal["low", "medium", "high"]

AuthenticityStyle = Literal[
    "casual_imperfect",
    "emotional_honesty",
    "matter_of_fact",
    "spontaneous",
    "polished_realism",
    "other",
]

Pacing = Literal["slow", "medium", "fast"]

ScriptDependency = Literal["high", "medium", "low"]


class UGCIntentData(TypedDict, total=False):
    """
    Output from classify_ugc_intent node - semantic classification of video style.

    Used to guide interaction planning and prompt generation to match
    the original video's communication style.
    """

    ugc_archetype: UGCArchetype | str
    primary_intent: PrimaryIntent | str
    hook_type: HookType | str
    narrative_structure: NarrativeStructure | str
    trust_mechanism: TrustMechanism | str
    cta_style: CTAStyle | str
    energy_level: EnergyLevel | str
    authenticity_style: AuthenticityStyle | str
    pacing: Pacing | str
    script_dependency: ScriptDependency | str


# =============================================================================
# Interaction Planning Types
# =============================================================================

InteractionPrimitive = Literal[
    "closeup_click_loop",
    "selfie_click_while_talking",
    "pocket_pull_and_click",
    "desk_idle_click",
    "anxiety_relief_click",
    "sound_showcase_asmr",
    "keychain_dangle_then_click",
    "compare_clicks_variation",
]

InteractionFraming = Literal["macro_closeup", "selfie_medium", "close", "desk_topdown"]


class InteractionBeat(TypedDict, total=False):
    """A single beat/step in the interaction sequence."""

    primitive: InteractionPrimitive | str
    duration_s: float
    framing: InteractionFraming | str
    audio_emphasis: bool
    notes: str


class InteractionPlanData(TypedDict, total=False):
    """
    Output from plan_interactions node - planned interaction sequence.

    Defines the choreographed sequence of actions for the product video,
    ensuring mechanical plausibility and visual appeal.
    """

    sequence: list[InteractionBeat]
    total_duration_s: float
    key_mechanics_notes: str

    # Added by validation if plan has issues
    validation_warnings: list[str]


# =============================================================================
# Selected Interaction Types
# =============================================================================


class InteractionClip(TypedDict, total=False):
    """A clip from the interaction library."""

    id: str
    path: str
    primitive: str
    framing: str
    duration_s: float
    description: str


class SelectedInteraction(TypedDict, total=False):
    """Result of matching a planned beat to a library clip."""

    beat_index: int
    primitive: str
    match_status: Literal["matched", "fallback", "no_match"] | str
    clip: InteractionClip | None
    fallback_reason: str


# =============================================================================
# Product Analysis Types
# =============================================================================


class ProductVisualFeatures(TypedDict, total=False):
    """
    Visual features extracted from product images by analyze_product node.

    Provides structured details about the product's appearance for
    accurate video generation.
    """

    colors: list[str]  # List of specific colors visible
    materials: list[str]  # List of materials (plastic, metal, etc.)
    finish: Literal["matte", "glossy", "translucent", "mixed"] | str
    size_reference: str  # Size compared to common objects
    key_components: list[str]  # List of visible parts
    unique_features: list[str]  # List of distinctive visual elements
    best_angles: list[str]  # List of recommended viewing angles


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


class InteractionConstraints(TypedDict, total=False):
    """Constraints for interaction planning."""

    max_duration_s: float
    max_beats: int
    required_primitives: list[str]
    forbidden_primitives: list[str]
    prefer_audio_emphasis: bool
