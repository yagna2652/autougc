"""
Blueprint generator - orchestrates all analyzer components to generate a complete video blueprint.

This is the main entry point for video analysis.

Enhanced with:
- Scene segmentation
- Pacing analysis
- Product tracking
- Scene-level recreation instructions
"""

import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

from dotenv import load_dotenv

from src.analyzer.audio_extractor import AudioExtractor
from src.analyzer.frame_extractor import FrameExtractor
from src.analyzer.pacing_analyzer import PacingAnalyzer
from src.analyzer.product_tracker import ProductTracker
from src.analyzer.scene_segmenter import SceneSegmenter
from src.analyzer.structure_parser import StructureParser
from src.analyzer.transcriber import Transcriber
from src.analyzer.visual_analyzer import VisualAnalyzer
from src.models.blueprint import VideoBlueprint


class BlueprintGenerator:
    """Orchestrates video analysis to generate a complete blueprint."""

    def __init__(
        self,
        anthropic_api_key: str | None = None,
        openai_api_key: str | None = None,
        whisper_mode: str = "local",
        whisper_model: str = "base",
        claude_model: str = "claude-sonnet-4-20250514",
        enable_enhanced_analysis: bool = True,
    ):
        """
        Initialize the blueprint generator.

        Args:
            anthropic_api_key: Anthropic API key (loads from env if not provided)
            openai_api_key: OpenAI API key for Whisper API mode (loads from env if not provided)
            whisper_mode: "local" or "api"
            whisper_model: Whisper model size for local mode
            claude_model: Claude model to use for analysis
            enable_enhanced_analysis: Whether to run scene segmentation, pacing, and product tracking
        """
        # Load environment variables
        load_dotenv()

        # Get API keys
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        if not self.anthropic_api_key:
            raise ValueError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY env var or pass api_key."
            )

        # Store config
        self.whisper_mode = whisper_mode
        self.whisper_model = whisper_model
        self.claude_model = claude_model
        self.enable_enhanced_analysis = enable_enhanced_analysis

        # Initialize core components
        self.audio_extractor = AudioExtractor()
        self.frame_extractor = FrameExtractor()
        self.transcriber = Transcriber(
            mode=whisper_mode,
            api_key=self.openai_api_key if whisper_mode == "api" else None,
            model=whisper_model,
        )
        self.visual_analyzer = VisualAnalyzer(
            api_key=self.anthropic_api_key,
            model=claude_model,
        )
        self.structure_parser = StructureParser(
            api_key=self.anthropic_api_key,
            model=claude_model,
        )

        # Initialize enhanced analysis components
        if enable_enhanced_analysis:
            self.scene_segmenter = SceneSegmenter(
                anthropic_api_key=self.anthropic_api_key,
                model=claude_model,
            )
            self.pacing_analyzer = PacingAnalyzer()
            self.product_tracker = ProductTracker()

    def generate(
        self,
        video_path: str | Path,
        output_path: str | Path | None = None,
        num_frames: int = 5,
        num_frames_for_scenes: int = 20,
        keep_temp_files: bool = False,
        progress_callback: callable | None = None,
    ) -> VideoBlueprint:
        """
        Generate a complete blueprint from a video file.

        Args:
            video_path: Path to the input video file
            output_path: Optional path to save the blueprint JSON
            num_frames: Number of frames for basic visual analysis
            num_frames_for_scenes: Number of frames for scene segmentation (more = better detection)
            keep_temp_files: Whether to keep temporary audio/frame files
            progress_callback: Optional callback function(step_name: str, step_num: int, total: int)

        Returns:
            VideoBlueprint object with complete analysis
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Create temp directory for intermediate files
        temp_dir = Path(tempfile.mkdtemp(prefix="autougc_"))

        try:
            total_steps = 11 if self.enable_enhanced_analysis else 6

            # Step 1: Get video info
            if progress_callback:
                progress_callback("Getting video info...", 1, total_steps)
            logger.info("Analyzing video: %s", video_path.name)
            video_info = self.audio_extractor.get_video_info(video_path)
            duration = video_info.get("duration", 30.0)
            logger.info("Video duration: %.1fs", duration)

            # Step 2: Extract audio
            if progress_callback:
                progress_callback("Extracting audio...", 2, total_steps)
            logger.info("Extracting audio...")
            audio_path = self.audio_extractor.extract(
                video_path=video_path,
                output_path=temp_dir / "audio.wav",
            )
            logger.debug("Audio saved to: %s", audio_path)

            # Step 3: Transcribe audio
            if progress_callback:
                progress_callback("Transcribing audio...", 3, total_steps)
            logger.info("Transcribing audio...")
            transcript = self.transcriber.transcribe(audio_path)
            logger.debug("Transcript preview: %s...", transcript.full_text[:100])
            logger.info("Transcript segments: %d", len(transcript.segments))

            # Step 4: Extract key frames for basic visual analysis
            if progress_callback:
                progress_callback("Extracting frames...", 4, total_steps)
            logger.info("Extracting frames...")
            frames = self.frame_extractor.extract_key_frames_for_analysis(
                video_path=video_path,
                duration=duration,
                output_dir=temp_dir / "frames",
                num_frames=num_frames,
            )
            logger.info("Extracted %d frames", len(frames))

            # Step 5: Analyze visuals
            if progress_callback:
                progress_callback("Analyzing visuals with Claude Vision...", 5, total_steps)
            logger.info("Analyzing visuals with Claude Vision...")
            visual_style = self.visual_analyzer.analyze_frames(
                frames=frames,
                transcript_summary=transcript.full_text[:200],
            )
            logger.info("Visual style - Setting: %s, Framing: %s", visual_style.setting, visual_style.framing)

            # Step 6: Parse structure
            if progress_callback:
                progress_callback("Parsing video structure...", 6, total_steps)
            logger.info("Parsing video structure...")
            visual_context = (
                f"Setting: {visual_style.setting}, Framing: {visual_style.framing}"
            )
            structure, audio_style, engagement = self.structure_parser.parse_structure(
                transcript=transcript,
                duration=duration,
                visual_context=visual_context,
            )
            logger.info("Structure - Hook: %s, Body: %s, CTA: %s",
                       structure.hook.style.value,
                       structure.body.framework.value,
                       structure.cta.urgency.value)

            # Enhanced analysis (if enabled)
            scene_breakdown = None
            pacing_metrics = None
            product_tracking = None
            recreation_script = []

            if self.enable_enhanced_analysis:
                # Step 7: Extract more frames for scene analysis
                if progress_callback:
                    progress_callback("Extracting frames for scene analysis...", 7, total_steps)
                logger.info("Extracting frames for scene analysis...")
                scene_frames_dir = temp_dir / "scene_frames"
                scene_frames = self.frame_extractor.extract_key_frames_for_analysis(
                    video_path=video_path,
                    duration=duration,
                    output_dir=scene_frames_dir,
                    num_frames=num_frames_for_scenes,
                )
                # scene_frames is a list of (timestamp, path) tuples
                frame_timestamps = [f[0] for f in scene_frames]
                frame_paths = [Path(f[1]) for f in scene_frames]
                logger.info("Extracted %d frames for scene analysis", len(scene_frames))

                # Step 8: Scene segmentation
                if progress_callback:
                    progress_callback("Segmenting scenes...", 8, total_steps)
                logger.info("Segmenting scenes...")
                transcript_segments = [
                    {"start": seg.start, "end": seg.end, "text": seg.text}
                    for seg in transcript.segments
                ]
                scene_breakdown = self.scene_segmenter.segment_video(
                    frame_paths=frame_paths,
                    frame_timestamps=frame_timestamps,
                    transcript_segments=transcript_segments,
                    total_duration=duration,
                )
                logger.info("Detected %d scenes, types: %s, location changes: %d",
                           scene_breakdown.total_scenes,
                           scene_breakdown.scene_types_summary,
                           scene_breakdown.location_changes)

                # Step 9: Pacing analysis
                if progress_callback:
                    progress_callback("Analyzing pacing...", 9, total_steps)
                logger.info("Analyzing pacing...")
                pacing_metrics = self.pacing_analyzer.analyze(
                    transcript_segments=transcript.segments,
                    structure=structure,
                    scene_breakdown=scene_breakdown,
                    total_duration=duration,
                )
                logger.info("Pacing - WPM: %.0f, Speaking ratio: %.1f%%, Cuts/min: %.1f",
                           pacing_metrics.words_per_minute,
                           pacing_metrics.speaking_ratio * 100,
                           pacing_metrics.cuts_per_minute)

                # Step 10: Product tracking
                if progress_callback:
                    progress_callback("Tracking products...", 10, total_steps)
                logger.info("Tracking products...")
                product_tracking = self.product_tracker.track_products(
                    scene_breakdown=scene_breakdown,
                    total_duration=duration,
                )
                if product_tracking.primary_product:
                    logger.info("Product detected - %s, screen time: %.1fs, ratio: %.1f%%",
                               product_tracking.primary_product.name,
                               product_tracking.total_product_screen_time,
                               product_tracking.product_to_content_ratio * 100)
                else:
                    logger.info("No products detected")

                # Step 11: Generate scene-level recreation script
                if progress_callback:
                    progress_callback("Generating recreation script...", 11, total_steps)
                logger.info("Generating recreation script...")
                recreation_script = self._generate_recreation_script(
                    scene_breakdown=scene_breakdown,
                    pacing_metrics=pacing_metrics,
                    audio_style=audio_style,
                )
                logger.info("Generated %d scene instructions", len(recreation_script))

            # Step 12: Build blueprint
            logger.info("Building blueprint...")
            blueprint = VideoBlueprint(
                source_video=str(video_path),
                transcript=transcript,
                structure=structure,
                visual_style=visual_style,
                audio_style=audio_style,
                engagement_analysis=engagement,
                scene_breakdown=scene_breakdown,
                pacing_metrics=pacing_metrics,
                product_tracking=product_tracking,
                recreation_notes=self._generate_recreation_notes(
                    visual_style=visual_style,
                    audio_style=audio_style,
                    structure=structure,
                    engagement=engagement,
                    pacing_metrics=pacing_metrics,
                ),
                recreation_script=recreation_script,
            )

            # Step 13: Save if output path provided
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                blueprint.save(str(output_path))
                logger.info("Blueprint saved to: %s", output_path)

            logger.info("Analysis complete")
            return blueprint

        finally:
            # Clean up temp files
            if not keep_temp_files:
                import shutil

                shutil.rmtree(temp_dir, ignore_errors=True)

    def _generate_recreation_notes(
        self,
        visual_style,
        audio_style,
        structure,
        engagement,
        pacing_metrics=None,
    ) -> list[str]:
        """Generate helpful notes for recreating this video style."""
        notes = []

        # Visual notes
        notes.append(
            f"Film in {visual_style.setting} with {visual_style.lighting} lighting"
        )
        notes.append(f"Use {visual_style.framing} framing")
        if visual_style.camera_movement != "static":
            notes.append(f"Camera movement: {visual_style.camera_movement}")

        # Audio notes
        notes.append(
            f"Speak with {audio_style.voice_tone} tone at {audio_style.pacing} pace"
        )
        notes.append(f"Energy level: {audio_style.energy_level}")
        if audio_style.has_background_music and audio_style.music_description:
            notes.append(f"Add background music: {audio_style.music_description}")

        # Pacing notes (if available)
        if pacing_metrics:
            notes.append(f"Target WPM: {pacing_metrics.words_per_minute:.0f}")
            notes.append(
                f"Speaking ratio: {pacing_metrics.speaking_ratio:.0%} speaking, "
                f"{1 - pacing_metrics.speaking_ratio:.0%} pauses/silence"
            )
            if pacing_metrics.cuts_per_minute > 0:
                notes.append(
                    f"Aim for ~{pacing_metrics.cuts_per_minute:.1f} scene cuts per minute"
                )

        # Structure notes
        notes.append(
            f"Hook style: {structure.hook.style.value} - {structure.hook.style_reasoning}"
        )
        notes.append(f"Body framework: {structure.body.framework.value}")
        notes.append(f"CTA approach: {engagement.cta_approach}")

        # Engagement notes
        if engagement.retention_tactics:
            notes.append(
                f"Key retention tactics: {', '.join(engagement.retention_tactics[:3])}"
            )
        if engagement.emotional_triggers:
            notes.append(
                f"Emotional triggers to use: {', '.join(engagement.emotional_triggers[:3])}"
            )

        return notes

    def _generate_recreation_script(
        self,
        scene_breakdown,
        pacing_metrics,
        audio_style,
    ) -> list[str]:
        """Generate step-by-step scene-level recreation instructions."""
        script = []

        if not scene_breakdown or not scene_breakdown.scenes:
            return script

        for scene in scene_breakdown.scenes:
            # Build instruction for this scene
            instruction_parts = []

            # Scene header
            instruction_parts.append(
                f"SCENE {scene.scene_number} ({scene.start:.1f}s - {scene.end:.1f}s, {scene.duration:.1f}s):"
            )

            # Scene type and shot
            instruction_parts.append(
                f"  Type: {scene.scene_type.value.upper()} | Shot: {scene.shot_type.value}"
            )

            # Location
            if scene.location:
                location_note = f"  Location: {scene.location}"
                if scene.setting_change:
                    location_note += " [NEW LOCATION]"
                instruction_parts.append(location_note)

            # Lighting and framing
            if scene.lighting_notes:
                instruction_parts.append(f"  Lighting: {scene.lighting_notes}")
            if scene.framing_description:
                instruction_parts.append(f"  Framing: {scene.framing_description}")

            # Camera
            if scene.camera_movement and scene.camera_movement != "static":
                instruction_parts.append(f"  Camera: {scene.camera_movement}")

            # Script/dialogue
            if scene.transcript_text:
                instruction_parts.append(f'  Say: "{scene.transcript_text}"')

            # Actions
            if scene.actions:
                action_strs = []
                for action in scene.actions:
                    action_str = f"{action.gesture.value}: {action.description}"
                    if action.intensity != "medium":
                        action_str += f" ({action.intensity})"
                    action_strs.append(action_str)
                instruction_parts.append(f"  Actions: {'; '.join(action_strs)}")

            # Expressions
            if scene.expressions:
                expr_strs = [
                    f"{e.expression.value}"
                    + (" + eye contact" if e.eye_contact else "")
                    for e in scene.expressions
                ]
                instruction_parts.append(f"  Expression: {', '.join(expr_strs)}")

            # Products
            if scene.product_appearances:
                for product in scene.product_appearances:
                    product_note = (
                        f"  Product: {product.product_name or 'Show product'}"
                    )
                    product_note += f" - {product.interaction}"
                    if product.is_demo:
                        product_note += " [DEMO MOMENT]"
                    instruction_parts.append(product_note)

            # On-screen text
            if scene.on_screen_text:
                instruction_parts.append(
                    f'  Text overlay: "{"; ".join(scene.on_screen_text)}"'
                )

            # Transition out
            if scene.transition_out:
                instruction_parts.append(
                    f"  Transition: {scene.transition_out.type.value}"
                )

            # Recreation instruction from Claude
            if scene.recreation_instruction:
                instruction_parts.append(f"  → {scene.recreation_instruction}")

            script.append("\n".join(instruction_parts))

        return script


def analyze_video(
    video_path: str | Path,
    output_path: str | Path | None = None,
    enhanced: bool = True,
    **kwargs,
) -> VideoBlueprint:
    """
    Convenience function to analyze a video and generate a blueprint.

    Args:
        video_path: Path to the video file
        output_path: Optional path to save the blueprint JSON
        enhanced: Whether to enable enhanced analysis (scenes, pacing, products)
        **kwargs: Additional arguments passed to BlueprintGenerator

    Returns:
        VideoBlueprint object
    """
    generator = BlueprintGenerator(enable_enhanced_analysis=enhanced, **kwargs)
    return generator.generate(video_path, output_path)
