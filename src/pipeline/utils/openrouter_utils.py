"""
OpenRouter API utilities for vision and text models.

OpenRouter provides access to multiple AI models through a unified API.
"""

import logging
import os
from typing import Any, Optional, Tuple

from openai import OpenAI

logger = logging.getLogger(__name__)

# Default vision model for OpenRouter
# Using GPT-4o-mini - routes through OpenAI (more reliable than Together AI backend)
DEFAULT_VISION_MODEL = "openai/gpt-4o-mini"

# Default text model for OpenRouter (for prompt generation)
# Using GPT-4o-mini - fast, reliable, handles multimodal well
DEFAULT_TEXT_MODEL = "openai/gpt-4o-mini"

# Available vision models on OpenRouter (you can switch to any of these)
VISION_MODELS = {
    "qwen-7b": "qwen/qwen-2.5-vl-7b-instruct",  # Cheap, good quality
    "qwen-72b": "qwen/qwen-2-vl-72b-instruct",  # More powerful
    "llama-11b": "meta-llama/llama-3.2-11b-vision-instruct",  # Meta's vision model
    "llama-90b": "meta-llama/llama-3.2-90b-vision-instruct",  # Largest Llama vision
    "gpt-4o": "openai/gpt-4o",  # Premium OpenAI (if you want quality)
    "claude": "anthropic/claude-3.5-sonnet",  # Premium Anthropic
}


def get_openrouter_client(
    state: dict[str, Any] = None,
    trace_name: str = "openrouter_call",
    model_type: str = "vision",  # "vision" or "text"
) -> Tuple[Optional[OpenAI], str, Optional[str]]:
    """
    Get OpenRouter client configured for vision tasks.

    Args:
        state: Pipeline state (optional, for future config support)
        trace_name: Name for tracing/logging

    Returns:
        Tuple of (client, model_name, error_message)
    """
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        logger.error("OPENROUTER_API_KEY not set in environment")
        return None, "", "OPENROUTER_API_KEY not set"

    try:
        # Create OpenAI client pointing to OpenRouter with recommended headers
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://autougc.app",  # For rankings on openrouter.ai
                "X-Title": "AutoUGC Video Pipeline",  # For rankings on openrouter.ai
            }
        )

        # Get model from state config or use default based on type
        if model_type == "text":
            model = DEFAULT_TEXT_MODEL
            if state and "config" in state:
                model = state["config"].get("text_model", DEFAULT_TEXT_MODEL)
        else:  # vision
            model = DEFAULT_VISION_MODEL
            if state and "config" in state:
                model = state["config"].get("vision_model", DEFAULT_VISION_MODEL)

        logger.debug(f"OpenRouter client created for model: {model}")
        return client, model, None

    except Exception as e:
        logger.error(f"Failed to create OpenRouter client: {e}")
        return None, "", f"Failed to create OpenRouter client: {str(e)}"


def get_vision_model(model_key: str = "qwen-7b") -> str:
    """
    Get the full model name for a vision model.

    Args:
        model_key: Short key for the model (e.g., "qwen-7b", "gpt-4o")

    Returns:
        Full model name for OpenRouter API
    """
    return VISION_MODELS.get(model_key, DEFAULT_VISION_MODEL)
