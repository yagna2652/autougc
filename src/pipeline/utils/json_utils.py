"""
JSON Utilities - Shared JSON parsing helpers for pipeline nodes.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_json_response(response_text: str, context: str = "response") -> dict[str, Any] | None:
    """
    Parse a JSON response from Claude, handling common formats.

    Handles:
    - Clean JSON responses
    - JSON embedded in markdown code blocks
    - JSON with surrounding text

    Args:
        response_text: Raw response text from Claude
        context: Description for logging (e.g., "video analysis", "classification")

    Returns:
        Parsed dict or None if parsing fails
    """
    if not response_text:
        return None

    # Try direct JSON parse first (fastest path)
    try:
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        pass

    # Fallback: extract JSON object from response
    try:
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1

        if json_start != -1 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)

        return None

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse {context} JSON: {e}")
        return None
