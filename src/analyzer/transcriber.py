"""
Audio transcription using OpenAI Whisper.

Supports both local Whisper model and OpenAI API.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

from src.models.blueprint import Transcript, TranscriptSegment


class Transcriber:
    """Transcribes audio using OpenAI Whisper."""

    def __init__(
        self,
        mode: Literal["local", "api"] = "local",
        api_key: str | None = None,
        model: str = "base",
    ):
        """
        Initialize the transcriber.

        Args:
            mode: "local" for local Whisper model, "api" for OpenAI API
            api_key: OpenAI API key (required if mode="api")
            model: Whisper model size for local mode (tiny, base, small, medium, large)
                   or model name for API mode (whisper-1)
        """
        self.mode = mode
        self.api_key = api_key
        self.model = model
        self._whisper_cmd = "whisper"  # Default, will be set by _verify_local_whisper

        if mode == "api" and not api_key:
            raise ValueError("API key is required for API mode")

        if mode == "local":
            self._verify_local_whisper()

    def _verify_local_whisper(self) -> None:
        """Verify that local Whisper is available."""
        import sys
        from pathlib import Path

        # Try to find whisper in venv/bin first
        venv_whisper = Path(sys.executable).parent / "whisper"
        if venv_whisper.exists():
            self._whisper_cmd = str(venv_whisper)
            return

        # Fall back to checking PATH
        try:
            result = subprocess.run(
                ["whisper", "--help"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                self._whisper_cmd = "whisper"
                return
        except FileNotFoundError:
            pass

        raise RuntimeError(
            "Local Whisper not found. Install with: pip install openai-whisper"
        )

    def transcribe(
        self,
        audio_path: str | Path,
        language: str | None = None,
    ) -> Transcript:
        """
        Transcribe an audio file.

        Args:
            audio_path: Path to the audio file
            language: Language code (e.g., "en") or None for auto-detection

        Returns:
            Transcript object with full text and timed segments
        """
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if self.mode == "local":
            return self._transcribe_local(audio_path, language)
        else:
            return self._transcribe_api(audio_path, language)

    def _transcribe_local(
        self,
        audio_path: Path,
        language: str | None = None,
    ) -> Transcript:
        """Transcribe using local Whisper model."""
        # Create a temp directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Build whisper command
            cmd = [
                self._whisper_cmd,
                str(audio_path),
                "--model",
                self.model,
                "--output_format",
                "json",
                "--output_dir",
                temp_dir,
            ]

            if language:
                cmd.extend(["--language", language])

            # Run whisper
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Whisper transcription failed:\n{result.stderr}")

            # Read the JSON output
            json_file = Path(temp_dir) / f"{audio_path.stem}.json"

            if not json_file.exists():
                raise RuntimeError(f"Whisper output not found. STDERR: {result.stderr}")

            with open(json_file, "r") as f:
                whisper_output = json.load(f)

            return self._parse_whisper_output(whisper_output)

    def _transcribe_api(
        self,
        audio_path: Path,
        language: str | None = None,
    ) -> Transcript:
        """Transcribe using OpenAI Whisper API."""
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError(
                "OpenAI package not installed. Install with: pip install openai"
            )

        client = OpenAI(api_key=self.api_key)

        with open(audio_path, "rb") as audio_file:
            # Get verbose JSON output for word timestamps
            kwargs = {
                "model": "whisper-1",
                "file": audio_file,
                "response_format": "verbose_json",
                "timestamp_granularities": ["segment"],
            }
            if language:
                kwargs["language"] = language

            response = client.audio.transcriptions.create(**kwargs)

        return self._parse_api_response(response)

    def _parse_whisper_output(self, whisper_output: dict) -> Transcript:
        """Parse local Whisper JSON output into Transcript model."""
        segments = []

        for seg in whisper_output.get("segments", []):
            segments.append(
                TranscriptSegment(
                    start=seg["start"],
                    end=seg["end"],
                    text=seg["text"].strip(),
                )
            )

        full_text = whisper_output.get("text", "").strip()
        if not full_text and segments:
            full_text = " ".join(s.text for s in segments)

        language = whisper_output.get("language", "en")

        return Transcript(
            full_text=full_text,
            segments=segments,
            language=language,
        )

    def _parse_api_response(self, response) -> Transcript:
        """Parse OpenAI API response into Transcript model."""
        segments = []

        # API response has segments with start/end times
        for seg in getattr(response, "segments", []):
            segments.append(
                TranscriptSegment(
                    start=seg.get("start", 0)
                    if isinstance(seg, dict)
                    else getattr(seg, "start", 0),
                    end=seg.get("end", 0)
                    if isinstance(seg, dict)
                    else getattr(seg, "end", 0),
                    text=(
                        seg.get("text", "")
                        if isinstance(seg, dict)
                        else getattr(seg, "text", "")
                    ).strip(),
                )
            )

        full_text = response.text.strip() if hasattr(response, "text") else ""
        if not full_text and segments:
            full_text = " ".join(s.text for s in segments)

        language = getattr(response, "language", "en")

        return Transcript(
            full_text=full_text,
            segments=segments,
            language=language,
        )
