"""
Pipeline Utilities - Helper function exports.

Direct imports to avoid __getattr__/importlib deadlocks during test collection.
"""

# OpenRouter utilities
from src.pipeline.utils.openrouter_utils import get_openrouter_client, get_vision_model

# Config helpers
from src.pipeline.utils.config_helpers import (
    get_config_vision_model,
    get_video_model,
    get_num_frames,
    get_video_duration,
    get_aspect_ratio,
    get_i2v_image_index,
    get_product_description,
    get_product_images,
    validate_config,
    DEFAULT_VISION_MODEL,
    DEFAULT_VIDEO_MODEL,
    DEFAULT_VIDEO_DURATION,
    DEFAULT_ASPECT_RATIO,
)

# Error handling
from src.pipeline.utils.error_handling import (
    build_error_result,
    handle_api_error,
    handle_unexpected_error,
    node_error_handler,
    with_error_handling,
)

# Image utilities
from src.pipeline.utils.image_utils import process_image, download_image, resize_image, encode_image_file

# JSON utilities
from src.pipeline.utils.json_utils import parse_json_response

# Interaction library
from src.pipeline.utils.interaction_library import load_interaction_library, resolve_clip_ids_to_plain_language

# Identity selector
from src.pipeline.utils.identity_selector import select_identity_references

# FAL upload
from src.pipeline.utils.fal_upload import upload_image_to_fal

__all__ = [
    # OpenRouter
    "get_openrouter_client",
    "get_vision_model",
    # Config helpers
    "get_config_vision_model",
    "get_video_model",
    "get_num_frames",
    "get_video_duration",
    "get_aspect_ratio",
    "get_i2v_image_index",
    "get_product_description",
    "get_product_images",
    "validate_config",
    "DEFAULT_VISION_MODEL",
    "DEFAULT_VIDEO_MODEL",
    "DEFAULT_VIDEO_DURATION",
    "DEFAULT_ASPECT_RATIO",
    # Error handling
    "build_error_result",
    "handle_api_error",
    "handle_unexpected_error",
    "node_error_handler",
    "with_error_handling",
    # Image utilities
    "process_image",
    "download_image",
    "resize_image",
    "encode_image_file",
    # JSON utilities
    "parse_json_response",
    # Interaction library
    "load_interaction_library",
    "resolve_clip_ids_to_plain_language",
    # Identity selector
    "select_identity_references",
    # FAL upload
    "upload_image_to_fal",
]
