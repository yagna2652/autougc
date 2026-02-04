"""
Fal Upload Utility - Upload images to Fal CDN for I2V pipeline.

Supports:
- Local file paths
- HTTP URLs (download then upload)
- Base64 / data URLs
"""

import base64
import logging
import os
import tempfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


def upload_image_to_fal(image_source: str, fal_key: str) -> str | None:
    """
    Upload image to Fal CDN.

    Supports:
    - Local file paths
    - HTTP URLs (download then upload)
    - Base64 / data URLs

    Args:
        image_source: Local path, HTTP URL, or base64/data URL
        fal_key: Fal.ai API key

    Returns:
        Fal CDN URL or None on failure
    """
    try:
        import fal_client

        # Set the API key
        os.environ["FAL_KEY"] = fal_key

        # Determine source type and get image bytes
        if _is_local_path(image_source):
            # Local file path - use upload_file directly
            logger.info(f"Uploading local file to Fal CDN: {image_source}")
            cdn_url = fal_client.upload_file(image_source)
            logger.info(f"Uploaded to Fal CDN: {cdn_url}")
            return cdn_url

        elif image_source.startswith("http://") or image_source.startswith("https://"):
            # HTTP URL - download then upload
            logger.info(f"Downloading image from URL: {image_source[:80]}...")
            image_bytes, media_type = _download_image(image_source)
            if not image_bytes:
                logger.error("Failed to download image from URL")
                return None

            cdn_url = fal_client.upload(image_bytes, media_type)
            logger.info(f"Uploaded to Fal CDN: {cdn_url}")
            return cdn_url

        elif image_source.startswith("data:"):
            # Data URL - extract base64 and upload
            logger.info("Processing data URL for Fal CDN upload")
            image_bytes, media_type = _parse_data_url(image_source)
            if not image_bytes:
                logger.error("Failed to parse data URL")
                return None

            cdn_url = fal_client.upload(image_bytes, media_type)
            logger.info(f"Uploaded to Fal CDN: {cdn_url}")
            return cdn_url

        else:
            # Assume raw base64
            logger.info("Processing raw base64 for Fal CDN upload")
            try:
                image_bytes = base64.b64decode(image_source)
                cdn_url = fal_client.upload(image_bytes, "image/jpeg")
                logger.info(f"Uploaded to Fal CDN: {cdn_url}")
                return cdn_url
            except Exception as e:
                logger.error(f"Failed to decode base64: {e}")
                return None

    except ImportError:
        logger.error("fal_client not installed. Run: pip install fal-client")
        return None
    except Exception as e:
        logger.error(f"Failed to upload image to Fal CDN: {e}")
        return None


def _is_local_path(source: str) -> bool:
    """Check if source is a local file path."""
    # Not a URL or data URL
    if source.startswith("http://") or source.startswith("https://"):
        return False
    if source.startswith("data:"):
        return False

    # Check if it looks like a path and exists
    path = Path(source)
    return path.exists() and path.is_file()


def _download_image(url: str) -> tuple[bytes | None, str]:
    """
    Download an image from URL.

    Args:
        url: HTTP/HTTPS URL to download

    Returns:
        Tuple of (image_bytes, media_type) or (None, "") if download fails
    """
    MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20MB limit for I2V
    TIMEOUT_SECONDS = 30.0
    ALLOWED_CONTENT_TYPES = {
        "image/jpeg": "image/jpeg",
        "image/jpg": "image/jpeg",
        "image/png": "image/png",
        "image/webp": "image/webp",
    }

    try:
        response = httpx.get(
            url,
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
        )
        response.raise_for_status()

        # Validate content type
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type not in ALLOWED_CONTENT_TYPES:
            logger.warning(f"URL is not a valid image type ({content_type}): {url[:80]}")
            return None, ""

        media_type = ALLOWED_CONTENT_TYPES[content_type]

        # Check size
        content_length = len(response.content)
        if content_length > MAX_SIZE_BYTES:
            logger.warning(
                f"Image too large ({content_length / 1024 / 1024:.1f}MB > 20MB limit): {url[:80]}"
            )
            return None, ""

        logger.debug(f"Downloaded image ({content_length / 1024:.1f}KB)")
        return response.content, media_type

    except httpx.TimeoutException:
        logger.warning(f"Timeout downloading image (>{TIMEOUT_SECONDS}s): {url[:80]}")
        return None, ""
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error downloading image ({e.response.status_code}): {url[:80]}")
        return None, ""
    except Exception as e:
        logger.warning(f"Failed to download image from URL: {e}")
        return None, ""


def _parse_data_url(data_url: str) -> tuple[bytes | None, str]:
    """
    Parse a data URL and extract image bytes.

    Args:
        data_url: Data URL in format data:image/jpeg;base64,...

    Returns:
        Tuple of (image_bytes, media_type) or (None, "") if parsing fails
    """
    try:
        # Format: data:image/jpeg;base64,/9j/4AAQ...
        if ";base64," not in data_url:
            logger.warning("Data URL missing base64 encoding")
            return None, ""

        parts = data_url.split(";base64,")
        if len(parts) != 2:
            logger.warning("Invalid data URL format")
            return None, ""

        media_type = parts[0].replace("data:", "")
        base64_data = parts[1]

        image_bytes = base64.b64decode(base64_data)
        return image_bytes, media_type

    except Exception as e:
        logger.warning(f"Failed to parse data URL: {e}")
        return None, ""
