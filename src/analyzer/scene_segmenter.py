"""
Scene Segmenter - Detects and analyzes individual scenes in videos.

Uses visual analysis to:
1. Detect scene boundaries (cuts, transitions)
2. Classify each scene type
3. Identify shot types
4. Track location changes
5. Extract per-scene actions and expressions

All LLM calls are traced via LangSmith for full prompt observability.
"""

import base64
from pathlib import Path

import anthropic

from src.models.blueprint import (
    ActionCue,
    ExpressionCue,
    FacialExpression,
    GestureType,
    ProductAppearance,
    Scene,
    SceneBreakdown,
    SceneTransition,
    SceneType,
    ShotType,
    TransitionType,
)
from src.tracing import TracedAnthropicClient, is_tracing_enabled


class SceneSegmenter:
    """
    Segments video into distinct scenes and analyzes each one.

    Uses dense frame sampling and Claude Vision to detect scene boundaries
    and extract detailed per-scene information.
    """

    def __init__(self, anthropic_api_key: str, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the scene segmenter.

        Args:
            anthropic_api_key: API key for Anthropic
            model: Claude model to use for analysis
        """
        # Use traced client for LangSmith observability
        if is_tracing_enabled():
            self.client = TracedAnthropicClient(
                api_key=anthropic_api_key, trace_name="scene_segmenter"
            )
        else:
            self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.model = model

    def segment_video(
        self,
        frame_paths: list[Path],
        frame_timestamps: list[float],
        transcript_segments: list[dict],
        total_duration: float,
    ) -> SceneBreakdown:
        """
        Segment video into scenes based on frames and transcript.

        Args:
            frame_paths: Paths to extracted frames
            frame_timestamps: Timestamp for each frame
            transcript_segments: Transcript segments with timing
            total_duration: Total video duration

        Returns:
            SceneBreakdown with all detected scenes
        """
        # First pass: detect scene boundaries
        scene_boundaries = self._detect_scene_boundaries(frame_paths, frame_timestamps)

        # Second pass: analyze each scene in detail
        scenes = self._analyze_scenes(
            frame_paths,
            frame_timestamps,
            scene_boundaries,
            transcript_segments,
            total_duration,
        )

        # Build summary
        scene_types_summary = {}
        for scene in scenes:
            scene_type = scene.scene_type.value
            scene_types_summary[scene_type] = scene_types_summary.get(scene_type, 0) + 1

        location_changes = sum(1 for s in scenes if s.setting_change)

        avg_duration = sum(s.duration for s in scenes) / len(scenes) if scenes else 0.0

        return SceneBreakdown(
            total_scenes=len(scenes),
            scenes=scenes,
            scene_types_summary=scene_types_summary,
            avg_scene_duration=avg_duration,
            location_changes=location_changes,
        )

    def _detect_scene_boundaries(
        self,
        frame_paths: list[Path],
        frame_timestamps: list[float],
    ) -> list[float]:
        """
        Detect scene boundaries by analyzing frame sequences.

        Returns list of timestamps where new scenes start.
        """
        if not frame_paths:
            return [0.0]

        # Prepare frames for analysis (limit to avoid token limits)
        max_frames = min(len(frame_paths), 20)
        step = max(1, len(frame_paths) // max_frames)
        selected_indices = list(range(0, len(frame_paths), step))[:max_frames]

        # Encode frames
        image_content = []
        frame_info = []

        for idx in selected_indices:
            frame_path = frame_paths[idx]
            timestamp = frame_timestamps[idx]

            image_data, media_type = self._encode_image(frame_path)
            image_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                }
            )
            image_content.append(
                {"type": "text", "text": f"[Frame at {timestamp:.1f}s]"}
            )
            frame_info.append((idx, timestamp))

        prompt = """Analyze these video frames in sequence and identify where scene changes occur.

A scene change happens when there is:
- A cut to a different camera angle
- A change in location/setting
- A significant change in framing (e.g., wide to close-up)
- A transition effect (fade, swipe, etc.)

For each scene boundary you detect, identify:
1. The timestamp where the new scene starts
2. The type of transition (cut, jump_cut, swipe, zoom, fade, whip_pan, match_cut, hand_cover)

Respond in this exact format:
SCENE_BOUNDARIES:
- 0.0|none|First scene starts
- [timestamp]|[transition_type]|[brief description]
...

Be thorough - identify ALL scene changes, even subtle ones like jump cuts within the same location."""

        image_content.append({"type": "text", "text": prompt})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": image_content}],
        )

        # Parse response
        boundaries = [0.0]  # Always start with 0
        response_text = response.content[0].text

        if "SCENE_BOUNDARIES:" in response_text:
            lines = response_text.split("SCENE_BOUNDARIES:")[1].strip().split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("-"):
                    parts = line[1:].strip().split("|")
                    if len(parts) >= 2:
                        try:
                            timestamp = float(parts[0].strip())
                            if timestamp > 0 and timestamp not in boundaries:
                                boundaries.append(timestamp)
                        except ValueError:
                            continue

        return sorted(boundaries)

    def _analyze_scenes(
        self,
        frame_paths: list[Path],
        frame_timestamps: list[float],
        scene_boundaries: list[float],
        transcript_segments: list[dict],
        total_duration: float,
    ) -> list[Scene]:
        """
        Analyze each detected scene in detail.
        """
        scenes = []

        # Create scene time ranges
        scene_ranges = []
        for i, start in enumerate(scene_boundaries):
            end = (
                scene_boundaries[i + 1]
                if i + 1 < len(scene_boundaries)
                else total_duration
            )
            scene_ranges.append((start, end))

        previous_location = None

        for scene_num, (start, end) in enumerate(scene_ranges, 1):
            # Find frames in this scene
            scene_frames = [
                (fp, ts)
                for fp, ts in zip(frame_paths, frame_timestamps)
                if start <= ts < end or (ts == 0 and start == 0)
            ]

            # If no frames in scene, use nearest frame
            if not scene_frames and frame_paths:
                nearest_idx = min(
                    range(len(frame_timestamps)),
                    key=lambda i: abs(frame_timestamps[i] - start),
                )
                scene_frames = [
                    (frame_paths[nearest_idx], frame_timestamps[nearest_idx])
                ]

            # Find transcript for this scene
            scene_transcript = ""
            for seg in transcript_segments:
                seg_start = seg.get("start", 0)
                seg_end = seg.get("end", 0)
                # Check for overlap
                if seg_start < end and seg_end > start:
                    scene_transcript += seg.get("text", "") + " "
            scene_transcript = scene_transcript.strip()

            # Analyze scene with Claude
            scene = self._analyze_single_scene(
                scene_num=scene_num,
                start=start,
                end=end,
                scene_frames=scene_frames,
                scene_transcript=scene_transcript,
                previous_location=previous_location,
            )

            # Update previous location
            if scene.location:
                previous_location = scene.location

            scenes.append(scene)

        return scenes

    def _analyze_single_scene(
        self,
        scene_num: int,
        start: float,
        end: float,
        scene_frames: list[tuple[Path, float]],
        scene_transcript: str,
        previous_location: str | None,
    ) -> Scene:
        """
        Analyze a single scene in detail.
        """
        duration = end - start

        # Prepare image content
        image_content = []

        # Use up to 3 frames per scene
        frames_to_use = scene_frames[:3] if len(scene_frames) > 3 else scene_frames

        for frame_path, timestamp in frames_to_use:
            image_data, media_type = self._encode_image(frame_path)
            image_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                }
            )

        prompt = f"""Analyze this scene from a UGC/TikTok video.

Scene #{scene_num}
Time: {start:.1f}s - {end:.1f}s (Duration: {duration:.1f}s)
Transcript during scene: "{scene_transcript if scene_transcript else "[No speech]"}"
Previous location: {previous_location if previous_location else "Unknown/Start of video"}

Analyze and respond in this EXACT format:

SCENE_TYPE: [one of: talking_head, demonstration, b_roll, product_showcase, before_after, testimonial, lifestyle, unboxing, transition, reaction, text_overlay]

SHOT_TYPE: [one of: extreme_close_up, close_up, medium_close_up, medium_shot, medium_wide, wide_shot, extreme_wide, product_shot, screen_recording, text_card]

LOCATION: [brief description of where this takes place]

LOCATION_CHANGED: [yes/no - compared to previous location]

CAMERA_MOVEMENT: [static, pan_left, pan_right, tilt_up, tilt_down, zoom_in, zoom_out, handheld, tracking, dolly]

PEOPLE_VISIBLE: [number]

SPEAKER: [main, secondary, both, none, voiceover]

FRAMING_NOTES: [detailed framing description]

LIGHTING: [lighting description for this scene]

ACTIONS:
- [timestamp]|[gesture_type]|[description]|[body_parts]|[direction]|[intensity]
(gesture_type: pointing, waving, thumbs_up, holding_product, applying_product, eating_drinking, hand_on_face, counting_fingers, shrugging, clapping, dancing, walking, sitting, standing, leaning_in, looking_away, other)

EXPRESSIONS:
- [timestamp]|[expression_type]|[description]|[eye_contact: yes/no]
(expression_type: neutral, smiling, excited, surprised, skeptical, concerned, thinking, laughing, serious, disappointed, satisfied, other)

PRODUCTS:
- [timestamp]|[duration]|[product_name]|[visibility: full/partial/background]|[interaction]|[position_in_frame]|[is_demo: yes/no]

ON_SCREEN_TEXT:
- [text content]
(or "none" if no text overlays)

RECREATION_INSTRUCTION: [One clear sentence on how to recreate this exact scene]"""

        image_content.append({"type": "text", "text": prompt})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{"role": "user", "content": image_content}],
        )

        return self._parse_scene_response(
            response.content[0].text,
            scene_num=scene_num,
            start=start,
            end=end,
            duration=duration,
            transcript=scene_transcript,
        )

    def _parse_scene_response(
        self,
        response_text: str,
        scene_num: int,
        start: float,
        end: float,
        duration: float,
        transcript: str,
    ) -> Scene:
        """
        Parse Claude's response into a Scene object.
        """
        lines = response_text.strip().split("\n")

        # Default values
        scene_type = SceneType.TALKING_HEAD
        shot_type = ShotType.MEDIUM_SHOT
        location = ""
        setting_change = False
        camera_movement = "static"
        people_visible = 1
        speaker = "main"
        framing_description = ""
        lighting_notes = ""
        actions = []
        expressions = []
        products = []
        on_screen_text = []
        recreation_instruction = ""

        current_section = None

        for line in lines:
            line = line.strip()

            if line.startswith("SCENE_TYPE:"):
                value = line.replace("SCENE_TYPE:", "").strip().lower()
                try:
                    scene_type = SceneType(value)
                except ValueError:
                    scene_type = (
                        SceneType.OTHER
                        if hasattr(SceneType, "OTHER")
                        else SceneType.TALKING_HEAD
                    )

            elif line.startswith("SHOT_TYPE:"):
                value = line.replace("SHOT_TYPE:", "").strip().lower()
                try:
                    shot_type = ShotType(value)
                except ValueError:
                    shot_type = ShotType.MEDIUM_SHOT

            elif line.startswith("LOCATION:"):
                location = line.replace("LOCATION:", "").strip()

            elif line.startswith("LOCATION_CHANGED:"):
                value = line.replace("LOCATION_CHANGED:", "").strip().lower()
                setting_change = value in ["yes", "true", "1"]

            elif line.startswith("CAMERA_MOVEMENT:"):
                camera_movement = line.replace("CAMERA_MOVEMENT:", "").strip()

            elif line.startswith("PEOPLE_VISIBLE:"):
                try:
                    people_visible = int(line.replace("PEOPLE_VISIBLE:", "").strip())
                except ValueError:
                    people_visible = 1

            elif line.startswith("SPEAKER:"):
                speaker = line.replace("SPEAKER:", "").strip().lower()

            elif line.startswith("FRAMING_NOTES:"):
                framing_description = line.replace("FRAMING_NOTES:", "").strip()

            elif line.startswith("LIGHTING:"):
                lighting_notes = line.replace("LIGHTING:", "").strip()

            elif line.startswith("ACTIONS:"):
                current_section = "actions"

            elif line.startswith("EXPRESSIONS:"):
                current_section = "expressions"

            elif line.startswith("PRODUCTS:"):
                current_section = "products"

            elif line.startswith("ON_SCREEN_TEXT:"):
                current_section = "on_screen_text"

            elif line.startswith("RECREATION_INSTRUCTION:"):
                recreation_instruction = line.replace(
                    "RECREATION_INSTRUCTION:", ""
                ).strip()
                current_section = None

            elif line.startswith("-") and current_section:
                content = line[1:].strip()

                if current_section == "actions" and content.lower() != "none":
                    action = self._parse_action(content, start)
                    if action:
                        actions.append(action)

                elif current_section == "expressions" and content.lower() != "none":
                    expression = self._parse_expression(content, start)
                    if expression:
                        expressions.append(expression)

                elif current_section == "products" and content.lower() != "none":
                    product = self._parse_product(content, start)
                    if product:
                        products.append(product)

                elif current_section == "on_screen_text" and content.lower() != "none":
                    on_screen_text.append(content)

        return Scene(
            scene_number=scene_num,
            start=start,
            end=end,
            duration=duration,
            scene_type=scene_type,
            shot_type=shot_type,
            location=location,
            setting_change=setting_change,
            transcript_text=transcript,
            on_screen_text=on_screen_text,
            framing_description=framing_description,
            camera_movement=camera_movement,
            lighting_notes=lighting_notes,
            people_visible=people_visible,
            speaker=speaker,
            actions=actions,
            expressions=expressions,
            product_appearances=products,
            recreation_instruction=recreation_instruction,
        )

    def _parse_action(self, content: str, scene_start: float) -> ActionCue | None:
        """Parse an action line into ActionCue."""
        parts = content.split("|")
        if len(parts) < 3:
            return None

        try:
            # Handle relative or absolute timestamps
            timestamp_str = parts[0].strip()
            try:
                timestamp = float(timestamp_str)
            except ValueError:
                timestamp = scene_start

            gesture_str = parts[1].strip().lower()
            try:
                gesture = GestureType(gesture_str)
            except ValueError:
                gesture = GestureType.OTHER

            description = parts[2].strip()
            body_parts = parts[3].strip().split(",") if len(parts) > 3 else []
            direction = parts[4].strip() if len(parts) > 4 else ""
            intensity = parts[5].strip() if len(parts) > 5 else "medium"

            return ActionCue(
                timestamp=timestamp,
                gesture=gesture,
                description=description,
                body_parts=[bp.strip() for bp in body_parts],
                direction=direction,
                intensity=intensity,
            )
        except Exception:
            return None

    def _parse_expression(
        self, content: str, scene_start: float
    ) -> ExpressionCue | None:
        """Parse an expression line into ExpressionCue."""
        parts = content.split("|")
        if len(parts) < 2:
            return None

        try:
            timestamp_str = parts[0].strip()
            try:
                timestamp = float(timestamp_str)
            except ValueError:
                timestamp = scene_start

            expr_str = parts[1].strip().lower()
            try:
                expression = FacialExpression(expr_str)
            except ValueError:
                expression = FacialExpression.NEUTRAL

            description = parts[2].strip() if len(parts) > 2 else ""
            eye_contact = True
            if len(parts) > 3:
                eye_contact = parts[3].strip().lower() in ["yes", "true", "1"]

            return ExpressionCue(
                timestamp=timestamp,
                expression=expression,
                description=description,
                eye_contact=eye_contact,
            )
        except Exception:
            return None

    def _parse_product(
        self, content: str, scene_start: float
    ) -> ProductAppearance | None:
        """Parse a product line into ProductAppearance."""
        parts = content.split("|")
        if len(parts) < 4:
            return None

        try:
            timestamp_str = parts[0].strip()
            try:
                timestamp = float(timestamp_str)
            except ValueError:
                timestamp = scene_start

            duration_str = parts[1].strip()
            try:
                duration = float(duration_str)
            except ValueError:
                duration = 1.0

            product_name = parts[2].strip()
            visibility = parts[3].strip() if len(parts) > 3 else "full"
            interaction = parts[4].strip() if len(parts) > 4 else "none"
            position = parts[5].strip() if len(parts) > 5 else "center"
            is_demo = False
            if len(parts) > 6:
                is_demo = parts[6].strip().lower() in ["yes", "true", "1"]

            return ProductAppearance(
                timestamp=timestamp,
                duration=duration,
                product_name=product_name,
                visibility=visibility,
                interaction=interaction,
                position_in_frame=position,
                is_demo=is_demo,
            )
        except Exception:
            return None

    def _encode_image(self, image_path: Path) -> tuple[str, str]:
        """
        Encode an image file to base64.

        Returns:
            Tuple of (base64_data, media_type)
        """
        suffix = image_path.suffix.lower()
        media_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_type_map.get(suffix, "image/jpeg")

        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        return image_data, media_type
