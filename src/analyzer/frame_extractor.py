"""
Frame extraction from video files using ffmpeg.

Extracts key frames at regular intervals for visual analysis.
"""

import subprocess
import tempfile
from pathlib import Path


class FrameExtractor:
    """Extracts frames from video files using ffmpeg."""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """
        Initialize the frame extractor.

        Args:
            ffmpeg_path: Path to ffmpeg executable (default assumes it's in PATH)
        """
        self.ffmpeg_path = ffmpeg_path

    def extract(
        self,
        video_path: str | Path,
        num_frames: int = 5,
        output_dir: str | Path | None = None,
    ) -> list[Path]:
        """
        Convenience method to extract key frames from a video.

        Automatically gets video duration and extracts frames at strategic points.

        Args:
            video_path: Path to the input video file
            num_frames: Number of frames to extract (default 5)
            output_dir: Directory to save frames (creates temp dir if not provided)

        Returns:
            List of paths to extracted frame images
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Get video duration using ffprobe
        duration = self._get_video_duration(video_path)

        # Extract key frames for analysis
        results = self.extract_key_frames_for_analysis(
            video_path=video_path,
            duration=duration,
            output_dir=output_dir,
            num_frames=num_frames,
        )

        # Return just the paths (not timestamps)
        return [path for _, path in results]

    def _get_video_duration(self, video_path: Path) -> float:
        """
        Get video duration in seconds using ffprobe.

        Args:
            video_path: Path to the video file

        Returns:
            Duration in seconds
        """
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
            raise RuntimeError(f"ffprobe failed to get duration:\n{result.stderr}")

        try:
            return float(result.stdout.strip())
        except ValueError:
            raise RuntimeError(f"Could not parse duration: {result.stdout}")

    def extract_frames(
        self,
        video_path: str | Path,
        output_dir: str | Path | None = None,
        fps: float = 1.0,
        max_frames: int | None = None,
        output_format: str = "jpg",
        quality: int = 2,
    ) -> list[Path]:
        """
        Extract frames from a video at regular intervals.

        Args:
            video_path: Path to the input video file
            output_dir: Directory to save frames (creates temp dir if not provided)
            fps: Frames per second to extract (default 1 = one frame per second)
            max_frames: Maximum number of frames to extract (None for no limit)
            output_format: Output image format (jpg, png)
            quality: JPEG quality (1-31, lower is better, only for jpg)

        Returns:
            List of paths to extracted frame images, sorted by time
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Create output directory
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix="frames_"))
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        # Build ffmpeg command
        output_pattern = str(output_dir / f"frame_%04d.{output_format}")

        cmd = [
            self.ffmpeg_path,
            "-i",
            str(video_path),
            "-vf",
            f"fps={fps}",
        ]

        # Add quality setting for JPEG
        if output_format.lower() in ("jpg", "jpeg"):
            cmd.extend(["-q:v", str(quality)])

        # Add frame limit if specified
        if max_frames is not None:
            cmd.extend(["-frames:v", str(max_frames)])

        cmd.extend(["-y", output_pattern])

        # Run ffmpeg
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg frame extraction failed:\n{result.stderr}")

        # Collect extracted frames
        frames = sorted(output_dir.glob(f"frame_*.{output_format}"))

        return frames

    def extract_frames_at_times(
        self,
        video_path: str | Path,
        timestamps: list[float],
        output_dir: str | Path | None = None,
        output_format: str = "jpg",
        quality: int = 2,
    ) -> list[Path]:
        """
        Extract frames at specific timestamps.

        Args:
            video_path: Path to the input video file
            timestamps: List of timestamps (in seconds) to extract frames at
            output_dir: Directory to save frames (creates temp dir if not provided)
            output_format: Output image format (jpg, png)
            quality: JPEG quality (1-31, lower is better, only for jpg)

        Returns:
            List of paths to extracted frame images
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Create output directory
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix="frames_"))
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        frames = []

        for i, timestamp in enumerate(timestamps):
            output_path = output_dir / f"frame_{i:04d}_{timestamp:.2f}s.{output_format}"

            cmd = [
                self.ffmpeg_path,
                "-ss",
                str(timestamp),
                "-i",
                str(video_path),
                "-frames:v",
                "1",
            ]

            # Add quality setting for JPEG
            if output_format.lower() in ("jpg", "jpeg"):
                cmd.extend(["-q:v", str(quality)])

            cmd.extend(["-y", str(output_path)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and output_path.exists():
                frames.append(output_path)

        return frames

    def extract_key_frames_for_analysis(
        self,
        video_path: str | Path,
        duration: float,
        output_dir: str | Path | None = None,
        num_frames: int = 5,
        output_format: str = "jpg",
    ) -> list[tuple[float, Path]]:
        """
        Extract key frames optimized for video analysis.

        Extracts frames at strategic points:
        - First frame (hook)
        - Evenly distributed middle frames (body)
        - Last frame (CTA)

        Args:
            video_path: Path to the input video file
            duration: Video duration in seconds
            output_dir: Directory to save frames
            num_frames: Number of frames to extract (minimum 3)
            output_format: Output image format

        Returns:
            List of tuples (timestamp, frame_path)
        """
        num_frames = max(3, num_frames)

        # Calculate strategic timestamps
        timestamps = []

        # Always include first frame
        timestamps.append(0.5)  # Slightly offset to avoid black frames

        # Middle frames evenly distributed
        if num_frames > 2:
            middle_count = num_frames - 2
            for i in range(middle_count):
                # Distribute between 10% and 90% of the video
                t = duration * (0.1 + 0.8 * (i + 1) / (middle_count + 1))
                timestamps.append(t)

        # Always include last frame
        timestamps.append(max(0.5, duration - 0.5))  # Slightly offset from end

        # Sort timestamps
        timestamps = sorted(timestamps)

        # Extract frames at these timestamps
        frames = self.extract_frames_at_times(
            video_path=video_path,
            timestamps=timestamps,
            output_dir=output_dir,
            output_format=output_format,
        )

        # Return as (timestamp, path) tuples
        return list(zip(timestamps[: len(frames)], frames))
