"""
Anthropic Utilities - Shared Claude client initialization for pipeline nodes.
"""

import logging
import os
from typing import Any

import anthropic

from src.tracing import TracedAnthropicClient, is_tracing_enabled

logger = logging.getLogger(__name__)

# Default model to use across all nodes
DEFAULT_MODEL = "claude-sonnet-4-20250514"


def get_anthropic_client(
    state: dict[str, Any],
    trace_name: str,
) -> tuple[anthropic.Anthropic | None, str, str | None]:
    """
    Get an Anthropic client with optional tracing.

    Handles:
    - API key retrieval from environment
    - Tracing setup when enabled
    - Model configuration from state

    Args:
        state: Pipeline state dict (for config)
        trace_name: Name for tracing (e.g., "analyze_video", "generate_prompt")

    Returns:
        Tuple of (client, model, error):
        - client: Anthropic client instance or None if error
        - model: Model name to use
        - error: Error message if client creation failed, None otherwise
    """
    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None, "", "ANTHROPIC_API_KEY not set"

    # Initialize client (with tracing if enabled)
    if is_tracing_enabled():
        client = TracedAnthropicClient(api_key=api_key, trace_name=trace_name)
    else:
        client = anthropic.Anthropic(api_key=api_key)

    # Get model from config
    model = state.get("config", {}).get("claude_model", DEFAULT_MODEL)

    return client, model, None


def get_anthropic_client_with_timeout(
    timeout_seconds: float = 120.0,
    connect_timeout: float = 30.0,
) -> anthropic.Anthropic | None:
    """
    Get an Anthropic client with custom timeout settings.

    Useful for Vision API calls that may take longer.

    Args:
        timeout_seconds: Total request timeout
        connect_timeout: Connection timeout

    Returns:
        Anthropic client instance or None if API key not set
    """
    import httpx

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    http_client = httpx.Client(
        timeout=httpx.Timeout(timeout_seconds, connect=connect_timeout)
    )
    return anthropic.Anthropic(api_key=api_key, http_client=http_client)
