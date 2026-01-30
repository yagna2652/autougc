"""
Mechanics Mapper - Extracts mechanics directly from analyzed video data.

Takes the blueprint's scene_breakdown (gestures, expressions, actions) and
transforms them into structured mechanics instructions for Sora 2.
"""

from typing import Optional

from src.models.blueprint import (
    VideoBlueprint,
    Scene,
    ActionCue,
    ExpressionCue,
    ProductAppearance,
    GestureType,
    FacialExpression,
)
from src.mechanics.models import (
    SegmentType,
    HandPosition,
    ExpressionState,
    BodyPosture,
    EyeDirection,
    HandMechanics,
    ExpressionMechanics,
    BodyMechanics,
    EyeMechanics,
    ProductMechanics,
    ProductContext,
    SceneMechanics,
    VideoConfig,
)


# =============================================================================
# MAPPING TABLES (for enum conversion only, not for content)
# =============================================================================

GESTURE_TO_HAND_POSITION: dict[GestureType, HandPosition] = {
    GestureType.POINTING: HandPosition.POINTING,
    GestureType.WAVING: HandPosition.WAVING,
    GestureType.THUMBS_UP: HandPosition.GESTURING,
    GestureType.HOLDING_PRODUCT: HandPosition.HOLDING_PRODUCT,
    GestureType.APPLYING_PRODUCT: HandPosition.DEMONSTRATING,
    GestureType.EATING_DRINKING: HandPosition.DEMONSTRATING,
    GestureType.HAND_ON_FACE: HandPosition.ON_FACE,
    GestureType.COUNTING_FINGERS: HandPosition.COUNTING,
    GestureType.SHRUGGING: HandPosition.GESTURING,
    GestureType.CLAPPING: HandPosition.GESTURING,
    GestureType.LEANING_IN: HandPosition.AT_SIDES,
    GestureType.DANCING: HandPosition.GESTURING,
    GestureType.WALKING: HandPosition.AT_SIDES,
    GestureType.SITTING: HandPosition.RESTING,
    GestureType.STANDING: HandPosition.AT_SIDES,
    GestureType.LOOKING_AWAY: HandPosition.AT_SIDES,
    GestureType.OTHER: HandPosition.GESTURING,
}

EXPRESSION_TO_STATE: dict[FacialExpression, ExpressionState] = {
    FacialExpression.NEUTRAL: ExpressionState.NEUTRAL,
    FacialExpression.SMILING: ExpressionState.SOFT_SMILE,
    FacialExpression.EXCITED: ExpressionState.EXCITED_SMILE,
    FacialExpression.SURPRISED: ExpressionState.SURPRISED,
    FacialExpression.SKEPTICAL: ExpressionState.THINKING,
    FacialExpression.CONCERNED: ExpressionState.THINKING,
    FacialExpression.THINKING: ExpressionState.THINKING,
    FacialExpression.LAUGHING: ExpressionState.EXCITED_SMILE,
    FacialExpression.SERIOUS: ExpressionState.NEUTRAL,
    FacialExpression.DISAPPOINTED: ExpressionState.NEUTRAL,
    FacialExpression.SATISFIED: ExpressionState.SATISFIED,
    FacialExpression.OTHER: ExpressionState.NEUTRAL,
}


class MechanicsMapper:
    """
    Extracts mechanics directly from analyzed video blueprint data.

    This mapper uses the actual gestures, expressions, and product interactions
    observed in the TikTok video, rather than relying on generic templates.
    """

    def __init__(self, config: VideoConfig):
        """
        Initialize the mapper with video configuration.

        Args:
            config: Target video configuration
        """
        self.config = config

    def map_blueprint(self, blueprint: VideoBlueprint) -> list[SceneMechanics]:
        """
        Map a complete blueprint to mechanics instructions.

        Extracts mechanics directly from the blueprint's scene_breakdown,
        scaling timestamps to fit the target video duration.

        Args:
            blueprint: Analyzed video blueprint with scene_breakdown

        Returns:
            List of SceneMechanics for each segment
        """
        # If no scene breakdown, we can't extract real mechanics
        if not blueprint.scene_breakdown or not blueprint.scene_breakdown.scenes:
            return self._create_minimal_segments_from_structure(blueprint)

        # Calculate time scaling factor
        original_duration = blueprint.structure.total_duration
        target_duration = self.config.duration
        time_scale = target_duration / original_duration if original_duration > 0 else 1.0

        # Get structure boundaries (scaled)
        hook_end = blueprint.structure.hook.end * time_scale
        cta_start = blueprint.structure.cta.start * time_scale

        segments = []

        # Group scenes into hook/body/cta based on their timing
        hook_scenes = []
        body_scenes = []
        cta_scenes = []

        for scene in blueprint.scene_breakdown.scenes:
            scaled_start = scene.start * time_scale
            if scaled_start < hook_end:
                hook_scenes.append(scene)
            elif scaled_start >= cta_start:
                cta_scenes.append(scene)
            else:
                body_scenes.append(scene)

        # Create hook segment from hook scenes
        if hook_scenes:
            hook_segment = self._create_segment_from_scenes(
                scenes=hook_scenes,
                segment_type=SegmentType.HOOK,
                start_time=0.0,
                end_time=min(hook_end, self.config.hook_duration),
                label="HOOK",
                time_scale=time_scale,
            )
            segments.append(hook_segment)

        # Create body segment(s) from body scenes
        if body_scenes:
            body_start = self.config.hook_duration
            body_end = self.config.duration - self.config.cta_duration

            # For longer videos, split body into multiple segments
            if len(body_scenes) > 2 and (body_end - body_start) > 4.0:
                mid_idx = len(body_scenes) // 2
                mid_time = body_start + (body_end - body_start) / 2

                body1 = self._create_segment_from_scenes(
                    scenes=body_scenes[:mid_idx],
                    segment_type=SegmentType.BODY,
                    start_time=body_start,
                    end_time=mid_time,
                    label="BODY-1",
                    time_scale=time_scale,
                )
                segments.append(body1)

                body2 = self._create_segment_from_scenes(
                    scenes=body_scenes[mid_idx:],
                    segment_type=SegmentType.BODY,
                    start_time=mid_time,
                    end_time=body_end,
                    label="BODY-2",
                    time_scale=time_scale,
                )
                segments.append(body2)
            else:
                body_segment = self._create_segment_from_scenes(
                    scenes=body_scenes,
                    segment_type=SegmentType.BODY,
                    start_time=body_start,
                    end_time=body_end,
                    label="BODY",
                    time_scale=time_scale,
                )
                segments.append(body_segment)

        # Create CTA segment from CTA scenes
        if cta_scenes:
            cta_segment = self._create_segment_from_scenes(
                scenes=cta_scenes,
                segment_type=SegmentType.CTA,
                start_time=self.config.duration - self.config.cta_duration,
                end_time=self.config.duration,
                label="CTA",
                time_scale=time_scale,
            )
            segments.append(cta_segment)

        # Ensure we have all three segments (fill gaps if needed)
        segments = self._ensure_complete_timeline(segments, blueprint)

        return segments

    def _create_segment_from_scenes(
        self,
        scenes: list[Scene],
        segment_type: SegmentType,
        start_time: float,
        end_time: float,
        label: str,
        time_scale: float,
    ) -> SceneMechanics:
        """
        Create a mechanics segment by aggregating data from multiple scenes.

        Extracts actual gestures, expressions, and product interactions
        from the analyzed scenes.
        """
        # Collect all actions, expressions, and product appearances from scenes
        all_actions: list[ActionCue] = []
        all_expressions: list[ExpressionCue] = []
        all_products: list[ProductAppearance] = []

        for scene in scenes:
            all_actions.extend(scene.actions)
            all_expressions.extend(scene.expressions)
            all_products.extend(scene.product_appearances)

        # Extract hand mechanics from actions
        hands = self._extract_hand_mechanics(all_actions, scenes)

        # Extract expression mechanics
        expression = self._extract_expression_mechanics(all_expressions, scenes)

        # Extract body mechanics from scene descriptions
        body = self._extract_body_mechanics(all_actions, scenes)

        # Extract eye mechanics
        eyes = self._extract_eye_mechanics(all_expressions, all_products, scenes)

        # Extract product mechanics
        product = self._extract_product_mechanics(all_products, scenes)

        # Determine energy level from scene context
        energy = self._determine_energy_level(scenes, segment_type)

        # Get key action description
        key_action = self._get_key_action(scenes, segment_type)

        return SceneMechanics(
            segment_type=segment_type,
            start_time=start_time,
            end_time=end_time,
            label=label,
            hands=hands,
            expression=expression,
            body=body,
            eyes=eyes,
            product=product if product and product.visible else None,
            energy_level=energy,
            key_action=key_action,
        )

    def _extract_hand_mechanics(
        self, actions: list[ActionCue], scenes: list[Scene]
    ) -> HandMechanics:
        """Extract hand mechanics from actual observed actions."""

        if not actions:
            # Fall back to scene recreation instructions
            for scene in scenes:
                if scene.recreation_instruction:
                    return HandMechanics(
                        position=HandPosition.GESTURING,
                        description=scene.recreation_instruction,
                        which_hand="both",
                    )
            return HandMechanics(
                position=HandPosition.GESTURING,
                description="Natural hand movements matching speech",
                which_hand="both",
            )

        # Build description from actual actions
        descriptions = []
        primary_position = HandPosition.GESTURING
        holds_product = False
        which_hand = "both"
        movement = ""

        for action in actions:
            # Get position from gesture type
            if action.gesture in GESTURE_TO_HAND_POSITION:
                primary_position = GESTURE_TO_HAND_POSITION[action.gesture]

            # Check if holding product
            if action.gesture in [GestureType.HOLDING_PRODUCT, GestureType.APPLYING_PRODUCT]:
                holds_product = True

            # Use the actual description from analysis
            if action.description:
                descriptions.append(action.description)

            # Capture movement direction
            if action.direction:
                movement = action.direction

            # Determine which hand
            if action.body_parts:
                if "right hand" in " ".join(action.body_parts).lower():
                    which_hand = "right"
                elif "left hand" in " ".join(action.body_parts).lower():
                    which_hand = "left"

        # Combine descriptions
        if descriptions:
            # Use unique descriptions, preserving order
            seen = set()
            unique_descs = []
            for d in descriptions:
                if d not in seen:
                    seen.add(d)
                    unique_descs.append(d)
            combined_description = ", then ".join(unique_descs[:3])  # Limit to 3 actions
        else:
            combined_description = f"{primary_position.value.replace('_', ' ')}"

        return HandMechanics(
            position=primary_position,
            description=combined_description,
            which_hand=which_hand,
            movement=movement,
            holds_product=holds_product,
        )

    def _extract_expression_mechanics(
        self, expressions: list[ExpressionCue], scenes: list[Scene]
    ) -> ExpressionMechanics:
        """Extract expression mechanics from actual observed expressions."""

        if not expressions:
            # Fall back to scene transcript for emotional context
            for scene in scenes:
                if scene.transcript_text:
                    return ExpressionMechanics(
                        state=ExpressionState.NEUTRAL,
                        description=f"Expression matching: '{scene.transcript_text[:50]}...'",
                    )
            return ExpressionMechanics(
                state=ExpressionState.NEUTRAL,
                description="Natural expression matching speech content",
            )

        # Build expression arc from observed expressions
        descriptions = []
        states = []

        for expr in expressions:
            state = EXPRESSION_TO_STATE.get(expr.expression, ExpressionState.NEUTRAL)
            states.append(state)

            if expr.description:
                descriptions.append(expr.description)

        # Determine primary state and transitions
        primary_state = states[-1] if states else ExpressionState.NEUTRAL
        transition_from = states[0] if len(states) > 1 and states[0] != primary_state else None

        # Build description
        if descriptions:
            if len(descriptions) > 1:
                # Show expression arc
                combined = f"{descriptions[0]} → {descriptions[-1]}"
            else:
                combined = descriptions[0]
        else:
            combined = f"{primary_state.value.replace('_', ' ')}"

        # Extract micro-expressions from detailed descriptions
        micro_expressions = []
        for expr in expressions:
            if expr.description:
                # Look for micro-expression indicators
                desc_lower = expr.description.lower()
                if "eyebrow" in desc_lower:
                    micro_expressions.append("eyebrow movement")
                if "squint" in desc_lower or "narrow" in desc_lower:
                    micro_expressions.append("eye squint")
                if "nod" in desc_lower:
                    micro_expressions.append("subtle nod")

        return ExpressionMechanics(
            state=primary_state,
            description=combined,
            transition_from=transition_from,
            transition_desc="transitions to" if transition_from else "",
            micro_expressions=micro_expressions[:2],  # Limit to 2
        )

    def _extract_body_mechanics(
        self, actions: list[ActionCue], scenes: list[Scene]
    ) -> BodyMechanics:
        """Extract body mechanics from actions and scene context."""

        posture = BodyPosture.UPRIGHT
        movement = ""
        descriptions = []

        # Check actions for body-related movements
        for action in actions:
            if action.gesture == GestureType.LEANING_IN:
                posture = BodyPosture.LEANING_FORWARD
                descriptions.append("leaning toward camera")
            elif action.gesture == GestureType.SHRUGGING:
                posture = BodyPosture.SHRUGGING
                descriptions.append("casual shrug")
            elif action.gesture == GestureType.SITTING:
                descriptions.append("seated position")
            elif action.gesture == GestureType.STANDING:
                descriptions.append("standing")

            # Check body parts for movement hints
            if action.body_parts:
                body_parts_str = " ".join(action.body_parts).lower()
                if "shoulder" in body_parts_str:
                    descriptions.append("shoulder movement")
                if "torso" in body_parts_str or "body" in body_parts_str:
                    descriptions.append("body movement")

            if action.direction:
                movement = action.direction

        # Check scene framing for posture hints
        for scene in scenes:
            if scene.framing_description:
                framing_lower = scene.framing_description.lower()
                if "lean" in framing_lower:
                    posture = BodyPosture.LEANING_FORWARD
                if "forward" in framing_lower:
                    descriptions.append("engaged forward posture")

        if descriptions:
            combined = ", ".join(set(descriptions))
        else:
            combined = "Natural posture with subtle movements"

        return BodyMechanics(
            posture=posture,
            description=combined,
            movement=movement,
            natural_tremor=True,  # Always include for realism
        )

    def _extract_eye_mechanics(
        self,
        expressions: list[ExpressionCue],
        products: list[ProductAppearance],
        scenes: list[Scene],
    ) -> EyeMechanics:
        """Extract eye mechanics from expressions and product interactions."""

        direction = EyeDirection.AT_CAMERA
        glance_pattern = ""
        descriptions = []

        # Check expression cues for eye contact info
        has_eye_contact = True
        for expr in expressions:
            if not expr.eye_contact:
                has_eye_contact = False
                direction = EyeDirection.GLANCING_AWAY
                descriptions.append("occasional glances away")

        # If there are product appearances, eyes likely alternate
        if products:
            direction = EyeDirection.AT_PRODUCT
            glance_pattern = "camera → product → camera"
            descriptions.append("glances between camera and product")

        # Check scene descriptions for eye behavior
        for scene in scenes:
            if scene.recreation_instruction:
                instr_lower = scene.recreation_instruction.lower()
                if "look at product" in instr_lower:
                    direction = EyeDirection.AT_PRODUCT
                if "eye contact" in instr_lower:
                    direction = EyeDirection.AT_CAMERA
                    descriptions.append("direct eye contact")

        if not descriptions:
            if has_eye_contact:
                descriptions.append("Natural eye contact with camera")
            else:
                descriptions.append("Conversational eye movement")

        return EyeMechanics(
            direction=direction,
            description=descriptions[0] if descriptions else "Natural eye contact",
            blink_pattern="natural",
            glance_pattern=glance_pattern,
        )

    def _extract_product_mechanics(
        self, products: list[ProductAppearance], scenes: list[Scene]
    ) -> Optional[ProductMechanics]:
        """Extract product mechanics from observed product appearances and product context."""

        if not products:
            return None

        # Aggregate product interaction info
        interactions = []
        positions = []
        demonstrations = []
        reveal_styles = []

        for prod in products:
            if prod.interaction and prod.interaction != "none":
                interactions.append(prod.interaction)
            if prod.position_in_frame:
                positions.append(prod.position_in_frame)
            if prod.is_demo and prod.description:
                demonstrations.append(prod.description)
            if prod.description:
                desc_lower = prod.description.lower()
                if "reveal" in desc_lower or "enters" in desc_lower:
                    reveal_styles.append(prod.description)

        # Build combined descriptions
        interaction = interactions[0] if interactions else "held in frame"
        position = positions[0] if positions else "center frame"
        demonstration = demonstrations[0] if demonstrations else ""
        reveal = reveal_styles[0] if reveal_styles else ""

        # Extract custom context instructions if available
        tactile_instruction = ""
        sound_instruction = ""
        size_instruction = ""

        if self.config.product_context:
            ctx = self.config.product_context
            tactile_instruction = self._build_tactile_instruction(ctx)
            sound_instruction = self._build_sound_instruction(ctx)
            size_instruction = self._build_size_instruction(ctx)

            # Enhance interaction with custom context
            interaction = self._enhance_interaction_with_context(
                interaction, ctx, demonstrations
            )

        return ProductMechanics(
            visible=True,
            interaction=interaction,
            position_in_frame=position,
            demonstration=demonstration,
            reveal_style=reveal,
            tactile_instruction=tactile_instruction,
            sound_instruction=sound_instruction,
            size_instruction=size_instruction,
        )

    def _build_tactile_instruction(self, ctx: ProductContext) -> str:
        """Build tactile feedback instruction from product context."""
        parts = []

        if ctx.tactile_features:
            features = ", ".join(ctx.tactile_features[:2])
            parts.append(f"demonstrating {features}")

        if ctx.interactions:
            # Find interaction that suggests tactile feedback
            tactile_verbs = ["press", "click", "push", "squeeze", "touch", "feel"]
            for interaction in ctx.interactions:
                interaction_lower = interaction.lower()
                if any(verb in interaction_lower for verb in tactile_verbs):
                    parts.append(f"{interaction} to show tactile response")
                    break

        if ctx.highlight_feature and "tactile" in ctx.highlight_feature.lower():
            parts.append(f"emphasizing {ctx.highlight_feature}")

        return ", ".join(parts) if parts else ""

    def _build_sound_instruction(self, ctx: ProductContext) -> str:
        """Build sound-related instruction from product context."""
        if not ctx.sound_features:
            return ""

        sounds = ctx.sound_features[:2]
        if len(sounds) == 1:
            return f"with audible {sounds[0]}"
        return f"with audible {sounds[0]} and {sounds[1]}"

    def _build_size_instruction(self, ctx: ProductContext) -> str:
        """Build size/scale instruction from product context."""
        if not ctx.size_description:
            return ""

        size = ctx.size_description.lower()
        if "palm" in size or "handheld" in size or "small" in size:
            return f"held in palm showing {ctx.size_description}"
        elif "large" in size or "big" in size:
            return f"shown at full scale demonstrating {ctx.size_description}"
        return f"showing {ctx.size_description}"

    def _enhance_interaction_with_context(
        self,
        base_interaction: str,
        ctx: ProductContext,
        demonstrations: list[str],
    ) -> str:
        """Enhance the base interaction with product context details."""
        parts = []

        # Start with product type if available
        if ctx.type:
            parts.append(ctx.type)

        # Add base interaction
        parts.append(base_interaction)

        # Add primary interactions from context
        if ctx.interactions and not demonstrations:
            primary_interaction = ctx.interactions[0]
            if primary_interaction.lower() not in base_interaction.lower():
                parts.append(primary_interaction)

        # Add highlight feature
        if ctx.highlight_feature:
            highlight = ctx.highlight_feature
            if highlight.lower() not in base_interaction.lower():
                parts.append(f"highlighting {highlight}")

        # Add custom instructions if present
        if ctx.custom_instructions:
            parts.append(ctx.custom_instructions)

        return ", ".join(parts)

    def _determine_energy_level(
        self, scenes: list[Scene], segment_type: SegmentType
    ) -> str:
        """Determine energy level from scene context."""

        # Check scene expressions for energy indicators
        excited_count = 0
        calm_count = 0

        for scene in scenes:
            for expr in scene.expressions:
                if expr.expression in [FacialExpression.EXCITED, FacialExpression.LAUGHING]:
                    excited_count += 1
                elif expr.expression in [FacialExpression.NEUTRAL, FacialExpression.THINKING]:
                    calm_count += 1

            # Check action intensity
            for action in scene.actions:
                if action.intensity == "exaggerated":
                    excited_count += 1
                elif action.intensity == "subtle":
                    calm_count += 1

        if excited_count > calm_count:
            return "high"
        elif calm_count > excited_count:
            return "low"
        return "medium"

    def _get_key_action(self, scenes: list[Scene], segment_type: SegmentType) -> str:
        """Get the key action description for a segment."""

        # Use recreation instructions if available
        for scene in scenes:
            if scene.recreation_instruction:
                return scene.recreation_instruction

        # Use transcript context
        for scene in scenes:
            if scene.transcript_text:
                return f"Speaking: '{scene.transcript_text[:40]}...'"

        # Default based on segment type
        defaults = {
            SegmentType.HOOK: "Capturing attention",
            SegmentType.BODY: "Main content delivery",
            SegmentType.CTA: "Call to action",
        }
        return defaults.get(segment_type, "")

    def _create_minimal_segments_from_structure(
        self, blueprint: VideoBlueprint
    ) -> list[SceneMechanics]:
        """
        Create minimal segments when no scene_breakdown is available.
        Uses transcript and structure info to create basic mechanics.
        """
        segments = []

        # Hook
        hook = blueprint.structure.hook
        segments.append(SceneMechanics(
            segment_type=SegmentType.HOOK,
            start_time=0.0,
            end_time=self.config.hook_duration,
            label="HOOK",
            hands=HandMechanics(
                position=HandPosition.GESTURING,
                description=f"Gesture matching: '{hook.text[:30]}...'",
                which_hand="both",
            ),
            expression=ExpressionMechanics(
                state=ExpressionState.RAISED_EYEBROWS,
                description="Attention-grabbing expression to match hook",
            ),
            body=BodyMechanics(
                posture=BodyPosture.LEANING_FORWARD,
                description="Engaged forward lean",
                natural_tremor=True,
            ),
            eyes=EyeMechanics(
                direction=EyeDirection.AT_CAMERA,
                description="Direct eye contact for hook impact",
            ),
            energy_level="high",
            key_action=f"Hook: {hook.style.value}",
        ))

        # Body
        body = blueprint.structure.body
        body_start = self.config.hook_duration
        body_end = self.config.duration - self.config.cta_duration
        segments.append(SceneMechanics(
            segment_type=SegmentType.BODY,
            start_time=body_start,
            end_time=body_end,
            label="BODY",
            hands=HandMechanics(
                position=HandPosition.DEMONSTRATING if self.config.has_product else HandPosition.GESTURING,
                description=f"Gestures for: '{body.text[:30]}...'",
                which_hand="both",
                holds_product=self.config.has_product,
            ),
            expression=ExpressionMechanics(
                state=ExpressionState.GENUINE_WARMTH,
                description="Expression matching body content",
            ),
            body=BodyMechanics(
                posture=BodyPosture.UPRIGHT,
                description="Natural posture for content delivery",
                natural_tremor=True,
            ),
            eyes=EyeMechanics(
                direction=EyeDirection.AT_PRODUCT if self.config.has_product else EyeDirection.AT_CAMERA,
                description="Glances between camera and product" if self.config.has_product else "Natural eye contact",
            ),
            product=ProductMechanics(
                visible=self.config.has_product,
                interaction="Demonstrating product",
                position_in_frame="center",
            ) if self.config.has_product else None,
            energy_level="medium",
            key_action=f"Body: {body.framework.value}",
        ))

        # CTA
        cta = blueprint.structure.cta
        cta_start = self.config.duration - self.config.cta_duration
        segments.append(SceneMechanics(
            segment_type=SegmentType.CTA,
            start_time=cta_start,
            end_time=self.config.duration,
            label="CTA",
            hands=HandMechanics(
                position=HandPosition.GESTURING,
                description=f"Gesture for CTA: '{cta.text[:30]}...'",
                which_hand="both",
            ),
            expression=ExpressionMechanics(
                state=ExpressionState.SOFT_SMILE,
                description="Warm, inviting expression for CTA",
            ),
            body=BodyMechanics(
                posture=BodyPosture.LEANING_FORWARD,
                description="Slight lean for emphasis",
                natural_tremor=True,
            ),
            eyes=EyeMechanics(
                direction=EyeDirection.AT_CAMERA,
                description="Direct eye contact for CTA impact",
            ),
            energy_level="medium",
            key_action=f"CTA: {cta.urgency.value}",
        ))

        return segments

    def _ensure_complete_timeline(
        self, segments: list[SceneMechanics], blueprint: VideoBlueprint
    ) -> list[SceneMechanics]:
        """Ensure we have hook, body, and CTA segments."""

        has_hook = any(s.segment_type == SegmentType.HOOK for s in segments)
        has_body = any(s.segment_type == SegmentType.BODY for s in segments)
        has_cta = any(s.segment_type == SegmentType.CTA for s in segments)

        if not has_hook or not has_body or not has_cta:
            # Fill in missing segments from structure
            minimal = self._create_minimal_segments_from_structure(blueprint)

            if not has_hook:
                segments.insert(0, minimal[0])
            if not has_body:
                segments.insert(1, minimal[1])
            if not has_cta:
                segments.append(minimal[2])

        # Sort by start time
        segments.sort(key=lambda s: s.start_time)

        return segments
