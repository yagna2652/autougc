"""
Configuration Helpers - Centralized configuration access for pipeline nodes.

Provides helper functions for retrieving configuration values from
pipeline state with consistent defaults and validation.
"""

import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)

# =============================================================================
# Default Configuration Values
# =============================================================================

# Model defaults
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-20250514"
DEFAULT_VIDEO_MODEL: Literal["sora", "kling"] = "sora"

# Frame extraction defaults
DEFAULT_NUM_FRAMES = 5
MAX_FRAMES_FOR_ANALYSIS = 5

# Video generation defaults
DEFAULT_VIDEO_DURATION = 5
DEFAULT_ASPECT_RATIO = "9:16"
DEFAULT_I2V_IMAGE_INDEX = 0

# Image processing defaults
DEFAULT_MAX_IMAGE_SIZE_BYTES = 4 * 1024 * 1024  # 4MB for Claude
MAX_PRODUCT_IMAGES = 4

# API timeouts
DEFAULT_API_TIMEOUT = 120.0
DEFAULT_CONNECT_TIMEOUT = 30.0


# =============================================================================
# Configuration Getters
# =============================================================================


def get_claude_model(state: dict[str, Any]) -> str:
    """
    Get the Claude model to use from state config.

    Args:
        state: Pipeline state dictionary

    Returns:
        Model name string
    """
    return state.get("config", {}).get("claude_model", DEFAULT_CLAUDE_MODEL)


def get_video_model(state: dict[str, Any]) -> Literal["sora", "kling"]:
    """
    Get the video generation model from state config.

    Args:
        state: Pipeline state dictionary

    Returns:
        Video model name ("sora" or "kling")
    """
    model = state.get("config", {}).get("video_model", DEFAULT_VIDEO_MODEL)
    if model not in ("sora", "kling"):
        logger.warning(f"Unknown video model '{model}', defaulting to '{DEFAULT_VIDEO_MODEL}'")
        return DEFAULT_VIDEO_MODEL
    return model


def get_num_frames(state: dict[str, Any]) -> int:
    """
    Get the number of frames to extract from state config.

    Args:
        state: Pipeline state dictionary

    Returns:
        Number of frames to extract
    """
    return state.get("config", {}).get("num_frames", DEFAULT_NUM_FRAMES)


def get_video_duration(state: dict[str, Any]) -> int:
    """
    Get the video duration in seconds from state config.

    Args:
        state: Pipeline state dictionary

    Returns:
        Video duration in seconds
    """
    return state.get("config", {}).get("video_duration", DEFAULT_VIDEO_DURATION)


def get_aspect_ratio(state: dict[str, Any]) -> str:
    """
    Get the aspect ratio from state config.

    Args:
        state: Pipeline state dictionary

    Returns:
        Aspect ratio string (e.g., "9:16")
    """
    return state.get("config", {}).get("aspect_ratio", DEFAULT_ASPECT_RATIO)


def get_i2v_image_index(state: dict[str, Any]) -> int:
    """
    Get the index of the product image to use for I2V from state config.

    Args:
        state: Pipeline state dictionary

    Returns:
        Index of the product image (0-indexed)
    """
    return state.get("config", {}).get("i2v_image_index", DEFAULT_I2V_IMAGE_INDEX)


# =============================================================================
# Product Description Helpers
# =============================================================================


def get_product_description(state: dict[str, Any]) -> str:
    """
    Get the product description from state.

    Args:
        state: Pipeline state dictionary

    Returns:
        Product description string
    """
    return state.get("product_description", "")


def get_product_images(
    state: dict[str, Any],
    max_images: int = MAX_PRODUCT_IMAGES,
) -> list[str]:
    """
    Get product images from state, limited to max count.

    Args:
        state: Pipeline state dictionary
        max_images: Maximum number of images to return

    Returns:
        List of product image strings (base64 or URLs)
    """
    images = state.get("product_images", [])
    return images[:max_images] if len(images) > max_images else images


# =============================================================================
# Config Validation
# =============================================================================


def validate_config(state: dict[str, Any]) -> list[str]:
    """
    Validate the configuration in state and return any warnings.

    Args:
        state: Pipeline state dictionary

    Returns:
        List of warning messages (empty if config is valid)
    """
    warnings = []
    config = state.get("config", {})

    # Check Claude model
    model = config.get("claude_model", DEFAULT_CLAUDE_MODEL)
    if not model.startswith("claude-"):
        warnings.append(f"Unusual Claude model name: {model}")

    # Check video model
    video_model = config.get("video_model", DEFAULT_VIDEO_MODEL)
    if video_model not in ("sora", "kling"):
        warnings.append(f"Unknown video model: {video_model}")

    # Check num_frames
    num_frames = config.get("num_frames", DEFAULT_NUM_FRAMES)
    if num_frames < 1:
        warnings.append(f"Invalid num_frames: {num_frames} (must be >= 1)")
    elif num_frames > 10:
        warnings.append(f"High num_frames: {num_frames} (may increase costs)")

    # Check video duration
    duration = config.get("video_duration", DEFAULT_VIDEO_DURATION)
    if duration < 1:
        warnings.append(f"Invalid video_duration: {duration} (must be >= 1)")
    elif duration > 30:
        warnings.append(f"Long video_duration: {duration}s (may not be supported)")

    return warnings
