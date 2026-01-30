"""
Mechanics API routes.

Endpoints for generating mechanics-enhanced prompts from blueprint data.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any

from src.mechanics import MechanicsEngine, VideoConfig, ProductContext
from src.models.blueprint import VideoBlueprint

router = APIRouter()


class ProductContextRequest(BaseModel):
    """Product context for custom mechanics."""

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


class MechanicsRequest(BaseModel):
    """Request body for mechanics generation."""

    blueprint: dict[str, Any] = Field(
        ..., description="Video blueprint data from TikTok analysis"
    )
    base_prompt: str = Field(
        default="",
        description="Base prompt with scene setting and person description",
    )
    product_category: Optional[str] = Field(
        default=None,
        description="Product category (skincare, supplement, tech, food, fashion, general)",
    )
    product_context: Optional[ProductContextRequest] = Field(
        default=None,
        description="Rich product context for custom mechanics beyond generic categories",
    )
    target_duration: float = Field(
        default=8.0,
        description="Target video duration in seconds",
    )
    energy_level: str = Field(
        default="medium",
        description="Energy level (low, medium, high)",
    )
    include_realism_preamble: bool = Field(
        default=True,
        description="Whether to include realism requirements in prompt",
    )


class MechanicsFromStyleRequest(BaseModel):
    """Request body for generating mechanics from style parameters."""

    hook_style: str = Field(
        default="casual_share",
        description="Hook style template (product_reveal, pov_storytelling, curiosity_hook, casual_share)",
    )
    body_framework: str = Field(
        default="demonstration",
        description="Body framework (demonstration, testimonial, education, comparison)",
    )
    cta_style: str = Field(
        default="soft_recommendation",
        description="CTA style (soft_recommendation, urgent_action, curious_tease)",
    )
    product_category: str = Field(
        default="general",
        description="Product category",
    )
    product_context: Optional[ProductContextRequest] = Field(
        default=None,
        description="Rich product context for custom mechanics beyond generic categories",
    )
    duration: float = Field(
        default=8.0,
        description="Target video duration",
    )
    base_prompt: str = Field(
        default="",
        description="Base scene/person description",
    )
    energy_level: str = Field(
        default="medium",
        description="Energy level (low, medium, high)",
    )


class MechanicsResponse(BaseModel):
    """Response for mechanics generation."""

    mechanics_prompt: str = Field(
        ..., description="Complete mechanics-enhanced prompt"
    )
    timeline_data: Optional[dict[str, Any]] = Field(
        default=None,
        description="Structured timeline data (if requested)",
    )
    config: dict[str, Any] = Field(
        ..., description="Video configuration used"
    )


class EnhancePromptRequest(BaseModel):
    """Request to enhance an existing prompt with mechanics."""

    original_prompt: str = Field(
        ..., description="Original video generation prompt"
    )
    blueprint: dict[str, Any] = Field(
        ..., description="Video blueprint data"
    )
    product_category: Optional[str] = Field(
        default=None,
        description="Product category override",
    )
    product_context: Optional[ProductContextRequest] = Field(
        default=None,
        description="Rich product context for custom mechanics beyond generic categories",
    )
    target_duration: float = Field(
        default=8.0,
        description="Target video duration",
    )


def _convert_product_context(ctx: Optional[ProductContextRequest]) -> Optional[ProductContext]:
    """Convert API request product context to model ProductContext."""
    if not ctx:
        return None
    return ProductContext(
        type=ctx.type,
        interactions=ctx.interactions,
        tactile_features=ctx.tactile_features,
        sound_features=ctx.sound_features,
        size_description=ctx.size_description,
        highlight_feature=ctx.highlight_feature,
        custom_instructions=ctx.custom_instructions,
    )


@router.post("/mechanics/generate", response_model=MechanicsResponse)
async def generate_mechanics(request: MechanicsRequest):
    """
    Generate mechanics-enhanced prompt from blueprint data.

    Takes analyzed TikTok blueprint data and generates a detailed
    prompt with human mechanics instructions for Sora 2.

    Args:
        request: Mechanics generation request with blueprint data

    Returns:
        MechanicsResponse with enhanced prompt and config
    """
    try:
        # Parse blueprint
        blueprint = VideoBlueprint.model_validate(request.blueprint)

        # Convert product context if provided
        product_context = _convert_product_context(request.product_context)

        # Create config
        config = VideoConfig(
            duration=request.target_duration,
            has_product=True,
            product_category=request.product_category or "general",
            product_context=product_context,
            energy_level=request.energy_level,
        )

        # Initialize engine
        engine = MechanicsEngine(config)

        # Generate mechanics prompt
        mechanics_prompt = engine.generate_mechanics_prompt(
            blueprint=blueprint,
            base_prompt=request.base_prompt,
            product_category=request.product_category,
            target_duration=request.target_duration,
        )

        # Get timeline for response
        timeline = engine.generate_timeline(blueprint)

        return MechanicsResponse(
            mechanics_prompt=mechanics_prompt,
            timeline_data=timeline.model_dump(),
            config=config.model_dump(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate mechanics: {str(e)}",
        )


@router.post("/mechanics/from-style", response_model=MechanicsResponse)
async def generate_from_style(request: MechanicsFromStyleRequest):
    """
    Generate mechanics prompt from style parameters.

    Use this when you don't have a blueprint but know the styles you want.

    Args:
        request: Style-based generation request

    Returns:
        MechanicsResponse with generated prompt
    """
    try:
        # Convert product context if provided
        product_context = _convert_product_context(request.product_context)

        # Create config
        config = VideoConfig(
            duration=request.duration,
            has_product=True,
            product_category=request.product_category,
            product_context=product_context,
            energy_level=request.energy_level,
        )

        # Initialize engine
        engine = MechanicsEngine(config)

        # Generate from style parameters
        mechanics_prompt = engine.generate_from_config(
            hook_style=request.hook_style,
            body_framework=request.body_framework,
            cta_style=request.cta_style,
            product_category=request.product_category,
            duration=request.duration,
            base_prompt=request.base_prompt,
        )

        return MechanicsResponse(
            mechanics_prompt=mechanics_prompt,
            config=config.model_dump(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate mechanics from style: {str(e)}",
        )


@router.post("/mechanics/enhance", response_model=MechanicsResponse)
async def enhance_prompt(request: EnhancePromptRequest):
    """
    Enhance an existing prompt with mechanics instructions.

    Takes an original video prompt and appends mechanics
    instructions derived from blueprint analysis.

    Args:
        request: Enhancement request with original prompt and blueprint

    Returns:
        MechanicsResponse with enhanced prompt
    """
    try:
        # Parse blueprint
        blueprint = VideoBlueprint.model_validate(request.blueprint)

        # Convert product context if provided
        product_context = _convert_product_context(request.product_context)

        # Create config
        config = VideoConfig(
            duration=request.target_duration,
            has_product=True,
            product_category=request.product_category or "general",
            product_context=product_context,
        )

        # Initialize engine
        engine = MechanicsEngine(config)

        # Enhance prompt
        enhanced_prompt = engine.enhance_prompt(
            original_prompt=request.original_prompt,
            blueprint=blueprint,
        )

        return MechanicsResponse(
            mechanics_prompt=enhanced_prompt,
            config=config.model_dump(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enhance prompt: {str(e)}",
        )


@router.get("/mechanics/templates")
async def list_templates():
    """
    List available mechanics templates.

    Returns available hook styles, body frameworks, CTA styles,
    and product categories for reference.
    """
    return {
        "hook_styles": [
            {
                "name": "product_reveal",
                "description": "Product rises into frame with excited reveal",
            },
            {
                "name": "pov_storytelling",
                "description": "POV style hook with direct camera address",
            },
            {
                "name": "curiosity_hook",
                "description": "Creates curiosity with skeptical-to-surprised transition",
            },
            {
                "name": "casual_share",
                "description": "Casual, friend-sharing-discovery style hook",
            },
        ],
        "body_frameworks": [
            {
                "name": "demonstration",
                "description": "Active product demonstration",
            },
            {
                "name": "testimonial",
                "description": "Personal experience sharing",
            },
            {
                "name": "education",
                "description": "Teaching/explaining content",
            },
            {
                "name": "comparison",
                "description": "Before/after or product comparison",
            },
        ],
        "cta_styles": [
            {
                "name": "soft_recommendation",
                "description": "Gentle, friendly recommendation",
            },
            {
                "name": "urgent_action",
                "description": "Energetic call to action",
            },
            {
                "name": "curious_tease",
                "description": "Leaves viewer curious, soft close",
            },
        ],
        "product_categories": [
            "skincare",
            "supplement",
            "tech",
            "food",
            "fashion",
            "general",
        ],
    }
