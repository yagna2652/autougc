"""
Audio extraction from video files using ffmpeg.
"""

import subprocess
import tempfile
from pathlib import Path


class AudioExtractor:
    """Extracts audio from video files using ffmpeg."""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """
        Initialize the audio extractor.

        Args:
            ffmpeg_path: Path to ffmpeg executable (default assumes it's in PATH)
        """
        self.ffmpeg_path = ffmpeg_path
        self._verify_ffmpeg()

    def _verify_ffmpeg(self) -> None:
        """Verify that ffmpeg is available."""
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                check=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"ffmpeg not found at '{self.ffmpeg_path}'. "
                "Please install ffmpeg: https://ffmpeg.org/download.html"
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg check failed: {e}")

    def extract(
        self,
        video_path: str | Path,
        output_path: str | Path | None = None,
        audio_format: str = "wav",
        sample_rate: int = 16000,
        mono: bool = True,
    ) -> Path:
        """
        Extract audio from a video file.

        Args:
            video_path: Path to the input video file
            output_path: Path for the output audio file (optional, creates temp file if not provided)
            audio_format: Output audio format (wav, mp3, m4a, etc.)
            sample_rate: Audio sample rate in Hz (16000 is good for speech recognition)
            mono: Convert to mono channel (recommended for transcription)

        Returns:
            Path to the extracted audio file
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Create output path if not provided
        if output_path is None:
            temp_dir = tempfile.gettempdir()
            output_path = Path(temp_dir) / f"{video_path.stem}_audio.{audio_format}"
        else:
            output_path = Path(output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build ffmpeg command
        cmd = [
            self.ffmpeg_path,
            "-i",
            str(video_path),
            "-vn",  # No video
            "-acodec",
            self._get_codec(audio_format),
            "-ar",
            str(sample_rate),
        ]

        # Add mono conversion if requested
        if mono:
            cmd.extend(["-ac", "1"])

        # Overwrite output file if it exists
        cmd.extend(["-y", str(output_path)])

        # Run ffmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg audio extraction failed:\n{result.stderr}")

        if not output_path.exists():
            raise RuntimeError(
                f"Audio extraction completed but output file not found: {output_path}"
            )

        return output_path

    def _get_codec(self, audio_format: str) -> str:
        """Get the appropriate codec for the audio format."""
        codec_map = {
            "wav": "pcm_s16le",
            "mp3": "libmp3lame",
            "m4a": "aac",
            "aac": "aac",
            "ogg": "libvorbis",
            "flac": "flac",
        }
        return codec_map.get(audio_format.lower(), "pcm_s16le")

    def get_video_duration(self, video_path: str | Path) -> float:
        """
        Get the duration of a video file in seconds.

        Args:
            video_path: Path to the video file

        Returns:
            Duration in seconds
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Could not get video duration: {result.stderr}")

        return float(result.stdout.strip())

    def get_video_info(self, video_path: str | Path) -> dict:
        """
        Get detailed information about a video file.

        Args:
            video_path: Path to the video file

        Returns:
            Dictionary with video metadata (duration, width, height, fps, etc.)
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,duration:format=duration",
            "-of",
            "json",
            str(video_path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Could not get video info: {result.stderr}")

        import json

        data = json.loads(result.stdout)

        info = {}

        # Get format duration
        if "format" in data and "duration" in data["format"]:
            info["duration"] = float(data["format"]["duration"])

        # Get stream info
        if "streams" in data and len(data["streams"]) > 0:
            stream = data["streams"][0]
            if "width" in stream:
                info["width"] = stream["width"]
            if "height" in stream:
                info["height"] = stream["height"]
            if "r_frame_rate" in stream:
                # Parse frame rate (e.g., "30/1" -> 30.0)
                fps_parts = stream["r_frame_rate"].split("/")
                if len(fps_parts) == 2:
                    info["fps"] = float(fps_parts[0]) / float(fps_parts[1])
                else:
                    info["fps"] = float(fps_parts[0])

        return info
