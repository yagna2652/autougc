"""
Video downloader for TikTok URLs using yt-dlp.

Downloads TikTok videos to a temporary directory for analysis.
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional

import yt_dlp

logger = logging.getLogger(__name__)


class VideoDownloader:
    """Downloads TikTok videos using yt-dlp."""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the video downloader.

        Args:
            output_dir: Directory to save videos. If None, uses system temp directory.
        """
        self.output_dir = (
            output_dir or Path(tempfile.gettempdir()) / "autougc_downloads"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download(self, url: str) -> Path:
        """
        Download a TikTok video from URL.

        Args:
            url: TikTok video URL

        Returns:
            Path to downloaded video file

        Raises:
            Exception: If download fails
        """
        ydl_opts = {
            "format": "best",
            "outtmpl": str(self.output_dir / "%(id)s.%(ext)s"),
            "quiet": False,
            "no_warnings": False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info and download
                info = ydl.extract_info(url, download=True)

                # Get the filename
                filename = ydl.prepare_filename(info)
                video_path = Path(filename)

                if not video_path.exists():
                    raise FileNotFoundError(
                        f"Downloaded video not found at {video_path}"
                    )

                return video_path

        except Exception as e:
            raise Exception(f"Failed to download video from {url}: {str(e)}")

    def cleanup(self, video_path: Path) -> bool:
        """
        Delete a downloaded video file.

        Args:
            video_path: Path to video file to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if video_path.exists():
                video_path.unlink()
                return True
            return False
        except Exception:
            return False


def download_video(url: str) -> dict:
    """
    Convenience function to download a video from URL.

    Args:
        url: Video URL (TikTok, Instagram Reel, etc.)

    Returns:
        Dict with 'success', 'path', and optionally 'error' keys
    """
    logger.info(f"    ↳ URL: {url}")
    logger.info(f"    ↳ Starting yt-dlp download...")

    try:
        downloader = VideoDownloader()
        video_path = downloader.download(url)

        # Get file size for logging
        file_size_mb = Path(video_path).stat().st_size / (1024 * 1024)
        logger.info(f"    ↳ Download complete: {video_path}")
        logger.info(f"    ↳ File size: {file_size_mb:.2f} MB")

        return {
            "success": True,
            "path": str(video_path),
        }
    except Exception as e:
        logger.error(f"    ↳ Download failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
        }
