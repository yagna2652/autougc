"""
Prompt Composer - Assembles mechanics into Sora 2-optimized prompts.

Takes structured mechanics data and composes it into a natural language
prompt format that produces realistic human movement in Sora 2.
"""

from src.mechanics.models import (
    MechanicsTimeline,
    SceneMechanics,
    VideoConfig,
    SegmentType,
)


class PromptComposer:
    """Composes mechanics-enhanced prompts for video generation."""

    # Realism requirements that should be prepended to all prompts
    REALISM_PREAMBLE = """CRITICAL REALISM REQUIREMENTS:
- iPhone front camera quality with natural sensor noise
- Real skin with pores, texture, natural imperfections
- Handheld micro-shake, not perfectly stabilized
- Person looking at phone screen, not through camera lens
- Natural indoor lighting from windows (not studio)
- Genuine micro-expressions and natural blink patterns
- Subtle body sway and natural arm tremor when holding items
- Authentic bedroom/bathroom/living room setting
"""

    def __init__(self, config: VideoConfig):
        """
        Initialize the composer with video configuration.

        Args:
            config: Target video configuration
        """
        self.config = config

    def compose_full_prompt(
        self,
        timeline: MechanicsTimeline,
        base_prompt: str,
        include_realism_preamble: bool = True,
    ) -> str:
        """
        Compose a complete mechanics-enhanced prompt.

        Args:
            timeline: MechanicsTimeline with all segment mechanics
            base_prompt: Original prompt to enhance (scene setting, person description)
            include_realism_preamble: Whether to include realism requirements

        Returns:
            Complete prompt with mechanics instructions
        """
        sections = []

        # Add realism requirements
        if include_realism_preamble:
            sections.append(self.REALISM_PREAMBLE)

        # Add base prompt (setting, person, product description)
        if base_prompt:
            sections.append(f"SCENE: {base_prompt}")

        # Add mechanics timeline
        mechanics_section = self._compose_mechanics_section(timeline)
        sections.append(mechanics_section)

        # Add energy/pacing guidance
        pacing_guidance = self._compose_pacing_guidance(timeline)
        sections.append(pacing_guidance)

        return "\n\n".join(sections)

    def compose_mechanics_only(self, timeline: MechanicsTimeline) -> str:
        """
        Compose just the mechanics section (for appending to existing prompts).

        Args:
            timeline: MechanicsTimeline with all segment mechanics

        Returns:
            Mechanics-only prompt section
        """
        return self._compose_mechanics_section(timeline)

    def _compose_mechanics_section(self, timeline: MechanicsTimeline) -> str:
        """Compose the detailed mechanics timeline section."""
        blocks = []

        for segment in timeline.segments:
            block = self._compose_segment_block(segment)
            blocks.append(block)

        return "HUMAN MECHANICS TIMELINE:\n" + "\n\n".join(blocks)

    def _compose_segment_block(self, segment: SceneMechanics) -> str:
        """Compose a single segment's mechanics block."""
        lines = []

        # Header with timing
        header = f"[{segment.start_time:.1f}-{segment.end_time:.1f}s {segment.label}]"
        lines.append(header)

        # Hand mechanics
        hand_desc = self._format_hand_instruction(segment)
        lines.append(f"HANDS: {hand_desc}")

        # Expression mechanics
        expr_desc = self._format_expression_instruction(segment)
        lines.append(f"EXPRESSION: {expr_desc}")

        # Eye mechanics
        eye_desc = self._format_eye_instruction(segment)
        lines.append(f"EYES: {eye_desc}")

        # Body mechanics
        body_desc = self._format_body_instruction(segment)
        lines.append(f"BODY: {body_desc}")

        # Product mechanics (if applicable)
        if segment.product and segment.product.visible:
            product_desc = self._format_product_instruction(segment)
            lines.append(f"PRODUCT: {product_desc}")

        return "\n".join(lines)

    def _format_hand_instruction(self, segment: SceneMechanics) -> str:
        """Format hand mechanics into natural instruction."""
        hands = segment.hands

        parts = []

        # Which hand and position
        if hands.which_hand != "both":
            parts.append(f"{hands.which_hand.capitalize()} hand")
        else:
            parts.append("Hands")

        # Movement if specified
        if hands.movement:
            parts.append(hands.movement)

        # Product handling
        if hands.holds_product:
            product_desc = "holding product"
            if hands.product_angle:
                product_desc += f" at {hands.product_angle}"
            parts.append(product_desc)

        # Main description
        if hands.description:
            # If description is comprehensive, use it directly
            if len(hands.description) > 30:
                return hands.description
            parts.append(hands.description)

        return ", ".join(parts) if parts else hands.description

    def _format_expression_instruction(self, segment: SceneMechanics) -> str:
        """Format expression mechanics into natural instruction."""
        expr = segment.expression

        parts = []

        # Transition if present
        if expr.transition_from and expr.transition_desc:
            from_state = expr.transition_from.value.replace("_", " ")
            to_state = expr.state.value.replace("_", " ")
            parts.append(f"{from_state.capitalize()} {expr.transition_desc} {to_state}")
        elif expr.description:
            parts.append(expr.description)
        else:
            parts.append(expr.state.value.replace("_", " ").capitalize())

        # Micro-expressions
        if expr.micro_expressions:
            micro = ", ".join(expr.micro_expressions[:2])  # Limit to 2
            parts.append(f"with {micro}")

        return " ".join(parts) if parts else expr.description

    def _format_eye_instruction(self, segment: SceneMechanics) -> str:
        """Format eye mechanics into natural instruction."""
        eyes = segment.eyes

        parts = []

        # Main direction/behavior
        if eyes.description:
            parts.append(eyes.description)
        else:
            direction = eyes.direction.value.replace("_", " ")
            parts.append(f"Looking {direction}")

        # Glance pattern
        if eyes.glance_pattern and eyes.glance_pattern not in eyes.description:
            parts.append(f"({eyes.glance_pattern})")

        return " ".join(parts)

    def _format_body_instruction(self, segment: SceneMechanics) -> str:
        """Format body mechanics into natural instruction."""
        body = segment.body

        parts = []

        # Main posture/description
        if body.description:
            parts.append(body.description)
        else:
            posture = body.posture.value.replace("_", " ")
            parts.append(posture.capitalize())

        # Movement
        if body.movement and body.movement not in str(body.description):
            parts.append(body.movement)

        # Natural tremor
        if body.natural_tremor and "tremor" not in str(body.description):
            parts.append("natural micro-movements")

        return ", ".join(parts)

    def _format_product_instruction(self, segment: SceneMechanics) -> str:
        """Format product mechanics into natural instruction."""
        product = segment.product

        parts = []

        # Reveal style (for hooks)
        if product.reveal_style and segment.segment_type == SegmentType.HOOK:
            parts.append(product.reveal_style)

        # Size instruction (important for scale context)
        if product.size_instruction:
            parts.append(product.size_instruction)
        elif product.position_in_frame:
            parts.append(f"positioned {product.position_in_frame}")

        # Interaction/demonstration with tactile context
        if product.tactile_instruction:
            parts.append(product.tactile_instruction)
        elif product.demonstration:
            parts.append(product.demonstration)
        elif product.interaction:
            parts.append(product.interaction)

        # Sound instruction
        if product.sound_instruction:
            parts.append(product.sound_instruction)

        return ", ".join(parts) if parts else product.interaction

    def _compose_pacing_guidance(self, timeline: MechanicsTimeline) -> str:
        """Compose pacing and energy guidance section."""
        lines = ["PACING GUIDANCE:"]

        # Overall energy
        energy = timeline.config.energy_level
        energy_desc = {
            "low": "Relaxed, conversational pace with gentle movements",
            "medium": "Natural energy with engaged body language",
            "high": "Energetic and expressive with dynamic movements",
        }
        lines.append(f"- Energy: {energy_desc.get(energy, energy_desc['medium'])}")

        # Segment-specific pacing
        for segment in timeline.segments:
            if segment.segment_type == SegmentType.HOOK:
                lines.append("- Hook: Immediate engagement, quick to capture attention")
            elif segment.segment_type == SegmentType.CTA:
                lines.append("- CTA: Clear, direct delivery with maintained energy")

        # Natural movement reminder
        lines.append("- Throughout: Maintain natural micro-movements, avoid robotic stillness")

        return "\n".join(lines)

    def enhance_existing_prompt(
        self,
        original_prompt: str,
        timeline: MechanicsTimeline,
    ) -> str:
        """
        Enhance an existing video prompt with mechanics instructions.

        Args:
            original_prompt: The original prompt to enhance
            timeline: MechanicsTimeline with mechanics data

        Returns:
            Enhanced prompt with mechanics appended
        """
        mechanics = self.compose_mechanics_only(timeline)
        pacing = self._compose_pacing_guidance(timeline)

        return f"""{original_prompt}

{self.REALISM_PREAMBLE}

{mechanics}

{pacing}"""

    def compose_segment_prompt(self, segment: SceneMechanics) -> str:
        """
        Compose a prompt for a single segment.

        Useful for generating segment-by-segment or testing individual mechanics.

        Args:
            segment: Single segment mechanics

        Returns:
            Prompt for the segment
        """
        return self._compose_segment_block(segment)
