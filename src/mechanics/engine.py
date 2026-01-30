"""
Mechanics Engine - Main orchestrator for mechanics-enhanced prompt generation.

This is the primary entry point for the Mechanics Engine. It coordinates
the mapper and composer to transform blueprint data into Sora 2-optimized
prompts with human mechanics instructions.
"""

from typing import Optional

from src.models.blueprint import VideoBlueprint
from src.mechanics.models import (
    MechanicsTimeline,
    SceneMechanics,
    VideoConfig,
    SegmentType,
)
from src.mechanics.mapper import MechanicsMapper
from src.mechanics.composer import PromptComposer


class MechanicsEngine:
    """
    Main orchestrator for mechanics-enhanced prompt generation.

    Takes TikTok blueprint data and transforms it into Sora 2 prompts
    with detailed human mechanics instructions.
    """

    def __init__(self, config: Optional[VideoConfig] = None):
        """
        Initialize the Mechanics Engine.

        Args:
            config: Optional video configuration. If not provided,
                   will use defaults or infer from blueprint.
        """
        self.config = config or VideoConfig()
        self.mapper = MechanicsMapper(self.config)
        self.composer = PromptComposer(self.config)

    def generate_mechanics_prompt(
        self,
        blueprint: VideoBlueprint,
        base_prompt: str = "",
        product_category: Optional[str] = None,
        target_duration: Optional[float] = None,
    ) -> str:
        """
        Generate a complete mechanics-enhanced prompt from a blueprint.

        This is the main entry point for most use cases.

        Args:
            blueprint: Analyzed TikTok video blueprint
            base_prompt: Optional base prompt (scene, person description)
            product_category: Optional product category override
            target_duration: Optional target video duration override

        Returns:
            Complete mechanics-enhanced prompt ready for Sora 2
        """
        # Update config if overrides provided
        if product_category:
            self.config.product_category = product_category
            self.mapper = MechanicsMapper(self.config)

        if target_duration:
            self.config.duration = target_duration
            self._recalculate_segment_durations()

        # Generate mechanics timeline
        timeline = self.generate_timeline(blueprint)

        # Compose full prompt
        prompt = self.composer.compose_full_prompt(timeline, base_prompt)

        return prompt

    def generate_timeline(self, blueprint: VideoBlueprint) -> MechanicsTimeline:
        """
        Generate a mechanics timeline from a blueprint.

        Useful when you need the structured timeline data, not just the prompt.

        Args:
            blueprint: Analyzed TikTok video blueprint

        Returns:
            MechanicsTimeline with all segment mechanics
        """
        # Map blueprint to mechanics
        segments = self.mapper.map_blueprint(blueprint)

        # Create timeline
        timeline = MechanicsTimeline(
            config=self.config,
            segments=segments,
            total_duration=self.config.duration,
            source_blueprint_id=blueprint.source_video,
            generation_notes=self._generate_notes(blueprint, segments),
        )

        return timeline

    def enhance_prompt(
        self,
        original_prompt: str,
        blueprint: VideoBlueprint,
    ) -> str:
        """
        Enhance an existing prompt with mechanics from a blueprint.

        Use this when you already have a prompt and want to add mechanics.

        Args:
            original_prompt: Existing video generation prompt
            blueprint: Blueprint to extract mechanics from

        Returns:
            Enhanced prompt with mechanics appended
        """
        timeline = self.generate_timeline(blueprint)
        return self.composer.enhance_existing_prompt(original_prompt, timeline)

    def generate_from_config(
        self,
        hook_style: str = "casual_share",
        body_framework: str = "demonstration",
        cta_style: str = "soft_recommendation",
        product_category: str = "general",
        duration: float = 8.0,
        base_prompt: str = "",
    ) -> str:
        """
        Generate mechanics prompt directly from style parameters.

        Use this when you don't have a blueprint but know the styles you want.

        Args:
            hook_style: Hook template to use
            body_framework: Body template to use
            cta_style: CTA template to use
            product_category: Product category
            duration: Target video duration
            base_prompt: Base scene/person description

        Returns:
            Mechanics-enhanced prompt
        """
        from src.mechanics.templates import (
            get_hook_template,
            get_body_template,
            get_cta_template,
        )

        # Update config
        self.config.duration = duration
        self.config.product_category = product_category
        self._recalculate_segment_durations()

        # Get templates
        hook_template = get_hook_template(hook_style)
        body_template = get_body_template(body_framework)
        cta_template = get_cta_template(cta_style)

        # Create segments from templates
        segments = []

        # Hook segment
        hook_segment = self._create_segment_from_template(
            hook_template,
            SegmentType.HOOK,
            0.0,
            self.config.hook_duration,
            "HOOK",
        )
        segments.append(hook_segment)

        # Body segment
        body_start = self.config.hook_duration
        body_end = self.config.duration - self.config.cta_duration
        body_segment = self._create_segment_from_template(
            body_template,
            SegmentType.BODY,
            body_start,
            body_end,
            "BODY",
        )
        segments.append(body_segment)

        # CTA segment
        cta_start = self.config.duration - self.config.cta_duration
        cta_segment = self._create_segment_from_template(
            cta_template,
            SegmentType.CTA,
            cta_start,
            self.config.duration,
            "CTA",
        )
        segments.append(cta_segment)

        # Create timeline
        timeline = MechanicsTimeline(
            config=self.config,
            segments=segments,
            total_duration=self.config.duration,
            generation_notes=[
                f"Generated from templates: hook={hook_style}, body={body_framework}, cta={cta_style}"
            ],
        )

        return self.composer.compose_full_prompt(timeline, base_prompt)

    def _create_segment_from_template(
        self,
        template: dict,
        segment_type: SegmentType,
        start_time: float,
        end_time: float,
        label: str,
    ) -> SceneMechanics:
        """Create a SceneMechanics from a template dict."""
        from src.mechanics.templates import get_product_modifiers
        from src.mechanics.models import ProductMechanics

        product = None
        if self.config.has_product and "product" in template:
            template_product = template["product"]
            modifiers = get_product_modifiers(self.config.product_category)

            # Build custom context instructions if product_context is available
            tactile_instruction = ""
            sound_instruction = ""
            size_instruction = ""
            interaction = template_product.interaction

            if self.config.product_context:
                ctx = self.config.product_context
                tactile_instruction = self._build_tactile_instruction(ctx)
                sound_instruction = self._build_sound_instruction(ctx)
                size_instruction = self._build_size_instruction(ctx)
                interaction = self._enhance_interaction_with_context(
                    template_product.interaction, ctx
                )

            product = ProductMechanics(
                visible=template_product.visible,
                interaction=interaction,
                position_in_frame=template_product.position_in_frame,
                demonstration=template_product.demonstration,
                reveal_style=modifiers.get("typical_reveal", ""),
                tactile_instruction=tactile_instruction,
                sound_instruction=sound_instruction,
                size_instruction=size_instruction,
            )

        return SceneMechanics(
            segment_type=segment_type,
            start_time=start_time,
            end_time=end_time,
            label=label,
            hands=template["hands"],
            expression=template["expression"],
            body=template["body"],
            eyes=template["eyes"],
            product=product,
            energy_level=self.config.energy_level,
        )

    def _build_tactile_instruction(self, ctx) -> str:
        """Build tactile feedback instruction from product context."""
        parts = []

        if ctx.tactile_features:
            features = ", ".join(ctx.tactile_features[:2])
            parts.append(f"demonstrating {features}")

        if ctx.interactions:
            tactile_verbs = ["press", "click", "push", "squeeze", "touch", "feel"]
            for interaction in ctx.interactions:
                interaction_lower = interaction.lower()
                if any(verb in interaction_lower for verb in tactile_verbs):
                    parts.append(f"{interaction} to show tactile response")
                    break

        if ctx.highlight_feature and "tactile" in ctx.highlight_feature.lower():
            parts.append(f"emphasizing {ctx.highlight_feature}")

        return ", ".join(parts) if parts else ""

    def _build_sound_instruction(self, ctx) -> str:
        """Build sound-related instruction from product context."""
        if not ctx.sound_features:
            return ""

        sounds = ctx.sound_features[:2]
        if len(sounds) == 1:
            return f"with audible {sounds[0]}"
        return f"with audible {sounds[0]} and {sounds[1]}"

    def _build_size_instruction(self, ctx) -> str:
        """Build size/scale instruction from product context."""
        if not ctx.size_description:
            return ""

        size = ctx.size_description.lower()
        if "palm" in size or "handheld" in size or "small" in size:
            return f"held in palm showing {ctx.size_description}"
        elif "large" in size or "big" in size:
            return f"shown at full scale demonstrating {ctx.size_description}"
        return f"showing {ctx.size_description}"

    def _enhance_interaction_with_context(self, base_interaction: str, ctx) -> str:
        """Enhance the base interaction with product context details."""
        parts = []

        if ctx.type:
            parts.append(ctx.type)

        parts.append(base_interaction)

        if ctx.interactions:
            primary_interaction = ctx.interactions[0]
            if primary_interaction.lower() not in base_interaction.lower():
                parts.append(primary_interaction)

        if ctx.highlight_feature:
            highlight = ctx.highlight_feature
            if highlight.lower() not in base_interaction.lower():
                parts.append(f"highlighting {highlight}")

        if ctx.custom_instructions:
            parts.append(ctx.custom_instructions)

        return ", ".join(parts)

    def _recalculate_segment_durations(self) -> None:
        """Recalculate segment durations based on total duration."""
        total = self.config.duration

        if total <= 4:
            # Short video: minimal hook/cta
            self.config.hook_duration = 1.0
            self.config.cta_duration = 1.0
        elif total <= 8:
            # Medium video: standard splits
            self.config.hook_duration = 2.0
            self.config.cta_duration = 1.5
        else:
            # Longer video: proportional splits
            self.config.hook_duration = min(3.0, total * 0.2)
            self.config.cta_duration = min(2.0, total * 0.15)

    def _generate_notes(
        self, blueprint: VideoBlueprint, segments: list[SceneMechanics]
    ) -> list[str]:
        """Generate metadata notes about the mechanics generation."""
        notes = []

        # Source info
        notes.append(f"Source: {blueprint.source_video}")

        # Style info
        notes.append(f"Hook style: {blueprint.structure.hook.style.value}")
        notes.append(f"Body framework: {blueprint.structure.body.framework.value}")
        notes.append(f"CTA urgency: {blueprint.structure.cta.urgency.value}")

        # Segment count
        notes.append(f"Generated {len(segments)} mechanics segments")

        # Product info
        if blueprint.product_tracking and blueprint.product_tracking.primary_product:
            product = blueprint.product_tracking.primary_product
            notes.append(f"Product: {product.name or product.category}")

        return notes

    def get_config(self) -> VideoConfig:
        """Get the current video configuration."""
        return self.config

    def update_config(self, **kwargs) -> None:
        """
        Update configuration parameters.

        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        # Recreate mapper with new config
        self.mapper = MechanicsMapper(self.config)
        self.composer = PromptComposer(self.config)
