"""
Image Utilities - Shared image processing helpers for pipeline nodes.
"""

import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Supported image content types
ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/webp": "image/webp",
    "image/gif": "image/gif",
}

# File extension to media type mapping
EXTENSION_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# Default limits
DEFAULT_MAX_SIZE_BYTES = 4 * 1024 * 1024  # 4MB (safe for Claude's 5MB limit)
DEFAULT_TIMEOUT_SECONDS = 30.0


def process_image(
    image: str,
    max_size_bytes: int = DEFAULT_MAX_SIZE_BYTES,
    auto_resize: bool = True,
) -> tuple[str | None, str]:
    """
    Process an image string (URL, data URL, file path, or base64) into base64 data.

    Handles:
    - Data URLs (data:image/jpeg;base64,...)
    - HTTP/HTTPS URLs (downloaded)
    - Local file paths
    - Raw base64 strings

    Args:
        image: Image URL, data URL, file path, or base64 data
        max_size_bytes: Maximum allowed size (default 4MB for Claude)
        auto_resize: Whether to auto-resize images exceeding max_size_bytes

    Returns:
        Tuple of (base64_data, media_type) or (None, "") if processing fails
    """
    try:
        image_bytes = None
        media_type = "image/jpeg"

        if image.startswith("data:"):
            # Data URL format: data:image/jpeg;base64,/9j/4AAQ...
            parts = image.split(";base64,")
            if len(parts) == 2:
                media_type = parts[0].replace("data:", "")
                image_bytes = base64.b64decode(parts[1])

        elif image.startswith("http://") or image.startswith("https://"):
            # URL - download the image
            result = download_image(image)
            if result[0] is None:
                return None, ""
            image_bytes, media_type = result

        elif Path(image).exists():
            # Local file path
            path = Path(image)
            media_type = EXTENSION_MEDIA_TYPES.get(path.suffix.lower(), "image/jpeg")
            with open(path, "rb") as f:
                image_bytes = f.read()

        else:
            # Assume raw base64
            return image, "image/jpeg"

        if image_bytes is None:
            return None, ""

        # Check if resizing is needed
        if len(image_bytes) > max_size_bytes:
            if auto_resize:
                logger.info(
                    f"Image too large ({len(image_bytes) / 1024 / 1024:.1f}MB), resizing..."
                )
                image_bytes, media_type = resize_image(image_bytes, max_size_bytes)
            else:
                logger.warning(
                    f"Image too large ({len(image_bytes) / 1024 / 1024:.1f}MB > "
                    f"{max_size_bytes / 1024 / 1024:.1f}MB limit)"
                )
                return None, ""

        image_data = base64.standard_b64encode(image_bytes).decode("utf-8")
        return image_data, media_type

    except Exception as e:
        logger.warning(f"Failed to process image: {e}")
        return None, ""


def download_image(
    url: str,
    max_size_bytes: int = DEFAULT_MAX_SIZE_BYTES,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    validate_size: bool = True,
) -> tuple[bytes | None, str]:
    """
    Download an image from a URL.

    Args:
        url: HTTP/HTTPS URL to download
        max_size_bytes: Maximum allowed size
        timeout_seconds: Request timeout
        validate_size: Whether to reject images exceeding max_size_bytes

    Returns:
        Tuple of (image_bytes, media_type) or (None, "") if download fails
    """
    try:
        logger.debug(f"Downloading image from URL: {url[:80]}...")

        response = httpx.get(
            url,
            timeout=timeout_seconds,
            follow_redirects=True,
        )
        response.raise_for_status()

        # Validate content type
        content_type = (
            response.headers.get("content-type", "").split(";")[0].strip().lower()
        )
        if content_type not in ALLOWED_CONTENT_TYPES:
            logger.warning(
                f"URL is not a valid image type ({content_type}): {url[:80]}"
            )
            return None, ""

        media_type = ALLOWED_CONTENT_TYPES[content_type]

        # Check size
        content_length = len(response.content)
        if validate_size and content_length > max_size_bytes:
            logger.warning(
                f"Image too large ({content_length / 1024 / 1024:.1f}MB > "
                f"{max_size_bytes / 1024 / 1024:.1f}MB limit): {url[:80]}"
            )
            return None, ""

        logger.debug(f"Successfully downloaded image ({content_length / 1024:.1f}KB)")
        return response.content, media_type

    except httpx.TimeoutException:
        logger.warning(f"Timeout downloading image (>{timeout_seconds}s): {url[:80]}")
        return None, ""
    except httpx.HTTPStatusError as e:
        logger.warning(
            f"HTTP error downloading image ({e.response.status_code}): {url[:80]}"
        )
        return None, ""
    except Exception as e:
        logger.warning(f"Failed to download image from URL: {e}")
        return None, ""


def resize_image(
    image_bytes: bytes,
    max_size_bytes: int = DEFAULT_MAX_SIZE_BYTES,
) -> tuple[bytes, str]:
    """
    Resize an image to fit within the max size limit.

    Uses iterative quality reduction and scaling to achieve target size.

    Args:
        image_bytes: Original image bytes
        max_size_bytes: Maximum allowed size in bytes

    Returns:
        Tuple of (resized_bytes, media_type)
    """
    from PIL import Image

    img = Image.open(BytesIO(image_bytes))

    # Convert to RGB if necessary (for PNG with transparency)
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGB")

    # Start with original size and reduce until under limit
    quality = 85
    scale = 1.0

    while True:
        # Resize if needed
        if scale < 1.0:
            new_size = (int(img.width * scale), int(img.height * scale))
            resized = img.resize(new_size, Image.Resampling.LANCZOS)
        else:
            resized = img

        # Save to bytes
        buffer = BytesIO()
        resized.save(buffer, format="JPEG", quality=quality, optimize=True)
        result_bytes = buffer.getvalue()

        if len(result_bytes) <= max_size_bytes:
            logger.info(
                f"Resized to {len(result_bytes) / 1024 / 1024:.2f}MB "
                f"({resized.width}x{resized.height})"
            )
            return result_bytes, "image/jpeg"

        # Reduce quality first, then scale
        if quality > 50:
            quality -= 10
        else:
            scale *= 0.8

        # Safety limit
        if scale < 0.1:
            logger.warning("Could not resize image small enough, using best effort")
            return result_bytes, "image/jpeg"


def encode_image_file(image_path: str) -> tuple[str | None, str]:
    """
    Encode a local image file to base64.

    Args:
        image_path: Path to the image file

    Returns:
        Tuple of (base64_data, media_type) or (None, None) on error
    """
    try:
        path = Path(image_path)
        media_type = EXTENSION_MEDIA_TYPES.get(path.suffix.lower(), "image/jpeg")

        # Check file size first
        file_size = path.stat().st_size
        logger.debug(f"Image file size: {file_size} bytes")

        # Warn if file is very large (> 5MB)
        if file_size > 5 * 1024 * 1024:
            logger.warning(
                f"Large image file ({file_size / 1024 / 1024:.1f}MB): {image_path}"
            )

        # Read and encode
        with open(path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")

        return data, media_type

    except Exception as e:
        logger.error(f"Failed to encode image {image_path}: {e}")
        return None, None
