"""
Pipeline Utilities - Helper function exports with lazy loading.

This module intentionally avoids eager imports so lightweight callers
(including tests) don't pull in the full pipeline dependency graph.
"""

from importlib import import_module
from typing import Any

_EXPORT_MAP = {
    # OpenRouter utilities
    "get_openrouter_client": ("src.pipeline.utils.openrouter_utils", "get_openrouter_client"),
    "get_vision_model": ("src.pipeline.utils.openrouter_utils", "get_vision_model"),
    # Config helpers
    "get_config_vision_model": ("src.pipeline.utils.config_helpers", "get_config_vision_model"),
    "get_video_model": ("src.pipeline.utils.config_helpers", "get_video_model"),
    "get_num_frames": ("src.pipeline.utils.config_helpers", "get_num_frames"),
    "get_video_duration": ("src.pipeline.utils.config_helpers", "get_video_duration"),
    "get_aspect_ratio": ("src.pipeline.utils.config_helpers", "get_aspect_ratio"),
    "get_i2v_image_index": ("src.pipeline.utils.config_helpers", "get_i2v_image_index"),
    "get_product_description": ("src.pipeline.utils.config_helpers", "get_product_description"),
    "get_product_images": ("src.pipeline.utils.config_helpers", "get_product_images"),
    "validate_config": ("src.pipeline.utils.config_helpers", "validate_config"),
    "DEFAULT_VISION_MODEL": ("src.pipeline.utils.config_helpers", "DEFAULT_VISION_MODEL"),
    "DEFAULT_VIDEO_MODEL": ("src.pipeline.utils.config_helpers", "DEFAULT_VIDEO_MODEL"),
    "DEFAULT_VIDEO_DURATION": ("src.pipeline.utils.config_helpers", "DEFAULT_VIDEO_DURATION"),
    "DEFAULT_ASPECT_RATIO": ("src.pipeline.utils.config_helpers", "DEFAULT_ASPECT_RATIO"),
    # Error handling
    "build_error_result": ("src.pipeline.utils.error_handling", "build_error_result"),
    "handle_api_error": ("src.pipeline.utils.error_handling", "handle_api_error"),
    "handle_unexpected_error": ("src.pipeline.utils.error_handling", "handle_unexpected_error"),
    "node_error_handler": ("src.pipeline.utils.error_handling", "node_error_handler"),
    "with_error_handling": ("src.pipeline.utils.error_handling", "with_error_handling"),
    # Image utilities
    "process_image": ("src.pipeline.utils.image_utils", "process_image"),
    "download_image": ("src.pipeline.utils.image_utils", "download_image"),
    "resize_image": ("src.pipeline.utils.image_utils", "resize_image"),
    "encode_image_file": ("src.pipeline.utils.image_utils", "encode_image_file"),
    # JSON utilities
    "parse_json_response": ("src.pipeline.utils.json_utils", "parse_json_response"),
    # Interaction library
    "load_interaction_library": ("src.pipeline.utils.interaction_library", "load_interaction_library"),
    "resolve_clip_ids_to_plain_language": ("src.pipeline.utils.interaction_library", "resolve_clip_ids_to_plain_language"),
    "select_identity_references": ("src.pipeline.utils.identity_selector", "select_identity_references"),
    # FAL upload
    "upload_image_to_fal": ("src.pipeline.utils.fal_upload", "upload_image_to_fal"),
}


def __getattr__(name: str) -> Any:
    try:
        module_path, attr_name = _EXPORT_MAP[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = import_module(module_path)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


__all__ = list(_EXPORT_MAP.keys())
