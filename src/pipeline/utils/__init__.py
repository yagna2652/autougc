"""
Pipeline Utilities - Helper functions for pipeline nodes.
"""

from src.pipeline.utils.openrouter_utils import (
    get_openrouter_client,
    get_vision_model,
)
from src.pipeline.utils.config_helpers import (
    DEFAULT_ASPECT_RATIO,
    DEFAULT_VISION_MODEL,
    DEFAULT_VIDEO_DURATION,
    DEFAULT_VIDEO_MODEL,
    get_aspect_ratio,
    get_config_vision_model,
    get_i2v_image_index,
    get_num_frames,
    get_product_description,
    get_product_images,
    get_video_duration,
    get_video_model,
    validate_config,
)
from src.pipeline.utils.error_handling import (
    build_error_result,
    handle_api_error,
    handle_unexpected_error,
    node_error_handler,
    with_error_handling,
)
from src.pipeline.utils.fal_upload import upload_image_to_fal
from src.pipeline.utils.image_utils import (
    download_image,
    encode_image_file,
    process_image,
    resize_image,
)
from src.pipeline.utils.interaction_library import (
    resolve_clip_ids_to_plain_language,
    load_interaction_library,
)
from src.pipeline.utils.identity_selector import (
    select_identity_references,
)
from src.pipeline.utils.json_utils import parse_json_response

__all__ = [
    # OpenRouter utilities
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
    "select_identity_references",
    # FAL upload
    "upload_image_to_fal",
]
