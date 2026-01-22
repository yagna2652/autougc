"""
Blueprint generator - orchestrates all analyzer components to generate a complete video blueprint.

This is the main entry point for video analysis.
"""

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from src.analyzer.audio_extractor import AudioExtractor
from src.analyzer.frame_extractor import FrameExtractor
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
    ):
        """
        Initialize the blueprint generator.

        Args:
            anthropic_api_key: Anthropic API key (loads from env if not provided)
            openai_api_key: OpenAI API key for Whisper API mode (loads from env if not provided)
            whisper_mode: "local" or "api"
            whisper_model: Whisper model size for local mode
            claude_model: Claude model to use for analysis
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

        # Initialize components
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

    def generate(
        self,
        video_path: str | Path,
        output_path: str | Path | None = None,
        num_frames: int = 5,
        keep_temp_files: bool = False,
    ) -> VideoBlueprint:
        """
        Generate a complete blueprint from a video file.

        Args:
            video_path: Path to the input video file
            output_path: Optional path to save the blueprint JSON
            num_frames: Number of frames to extract for visual analysis
            keep_temp_files: Whether to keep temporary audio/frame files

        Returns:
            VideoBlueprint object with complete analysis
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Create temp directory for intermediate files
        temp_dir = Path(tempfile.mkdtemp(prefix="autougc_"))

        try:
            # Step 1: Get video info
            print(f"📹 Analyzing video: {video_path.name}")
            video_info = self.audio_extractor.get_video_info(video_path)
            duration = video_info.get("duration", 30.0)
            print(f"   Duration: {duration:.1f}s")

            # Step 2: Extract audio
            print("🎵 Extracting audio...")
            audio_path = self.audio_extractor.extract(
                video_path=video_path,
                output_path=temp_dir / "audio.wav",
            )
            print(f"   Saved to: {audio_path}")

            # Step 3: Transcribe audio
            print("📝 Transcribing audio...")
            transcript = self.transcriber.transcribe(audio_path)
            print(f"   Transcript: {transcript.full_text[:100]}...")
            print(f"   Segments: {len(transcript.segments)}")

            # Step 4: Extract key frames
            print("🖼️  Extracting frames...")
            frames = self.frame_extractor.extract_key_frames_for_analysis(
                video_path=video_path,
                duration=duration,
                output_dir=temp_dir / "frames",
                num_frames=num_frames,
            )
            print(f"   Extracted {len(frames)} frames")

            # Step 5: Analyze visuals
            print("👁️  Analyzing visuals with Claude Vision...")
            visual_style = self.visual_analyzer.analyze_frames(
                frames=frames,
                transcript_summary=transcript.full_text[:200],
            )
            print(f"   Setting: {visual_style.setting}")
            print(f"   Framing: {visual_style.framing}")

            # Step 6: Parse structure
            print("🔍 Parsing video structure...")
            visual_context = (
                f"Setting: {visual_style.setting}, Framing: {visual_style.framing}"
            )
            structure, audio_style, engagement = self.structure_parser.parse_structure(
                transcript=transcript,
                duration=duration,
                visual_context=visual_context,
            )
            print(f"   Hook style: {structure.hook.style.value}")
            print(f"   Body framework: {structure.body.framework.value}")
            print(f"   CTA urgency: {structure.cta.urgency.value}")

            # Step 7: Build blueprint
            print("📋 Building blueprint...")
            blueprint = VideoBlueprint(
                source_video=str(video_path),
                transcript=transcript,
                structure=structure,
                visual_style=visual_style,
                audio_style=audio_style,
                engagement_analysis=engagement,
                recreation_notes=self._generate_recreation_notes(
                    visual_style=visual_style,
                    audio_style=audio_style,
                    structure=structure,
                    engagement=engagement,
                ),
            )

            # Step 8: Save if output path provided
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                blueprint.save(str(output_path))
                print(f"💾 Blueprint saved to: {output_path}")

            print("✅ Analysis complete!")
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


def analyze_video(
    video_path: str | Path,
    output_path: str | Path | None = None,
    **kwargs,
) -> VideoBlueprint:
    """
    Convenience function to analyze a video and generate a blueprint.

    Args:
        video_path: Path to the video file
        output_path: Optional path to save the blueprint JSON
        **kwargs: Additional arguments passed to BlueprintGenerator

    Returns:
        VideoBlueprint object
    """
    generator = BlueprintGenerator(**kwargs)
    return generator.generate(video_path, output_path)
