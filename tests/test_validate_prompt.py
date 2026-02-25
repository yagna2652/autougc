"""
Tests for the validate_prompt node.

All tests monkeypatch the LLM client to avoid real API calls.
Key invariant: the node NEVER sets 'error' in its return dict.
"""

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.pipeline.nodes.validate_prompt import validate_prompt_node


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_choice(content: str):
    """Build a fake OpenAI chat completion choice."""
    return SimpleNamespace(message=SimpleNamespace(content=content))


def _make_response(content: str):
    """Build a fake OpenAI chat completion response."""
    return SimpleNamespace(choices=[_make_choice(content)])


def _base_state(
    video_prompt: str = "Right hand wraps body, thumb braced left edge. Beat 1 (0-3s): index finger plunges top-left keycap downward 2mm into housing, springs back.",
    product_mechanics: str = "Only one key pressed at a time. 4 keys in a row.",
) -> dict[str, Any]:
    """Return a minimal valid pipeline state for testing."""
    return {
        "video_prompt": video_prompt,
        "product_mechanics": product_mechanics,
        "config": {},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@patch("src.pipeline.nodes.validate_prompt.get_openrouter_client")
def test_passes_clean_prompt(mock_client):
    """When LLM says passed=True, video_prompt is unchanged."""
    client = MagicMock()
    client.chat.completions.create.return_value = _make_response(
        json.dumps({"passed": True, "issues": []})
    )
    mock_client.return_value = (client, "openai/gpt-4o-mini", None)

    state = _base_state()
    original_prompt = state["video_prompt"]
    result = validate_prompt_node(state)

    assert "error" not in result
    assert result["prompt_validation"]["passed"] is True
    assert "video_prompt" not in result  # unchanged, so not in update
    assert result["current_step"] == "prompt_validated"


@patch("src.pipeline.nodes.validate_prompt.get_openrouter_client")
def test_rewrites_on_high_severity(mock_client):
    """Phase 1 finds high issues → Phase 2 rewrites → original_prompt preserved."""
    phase1_json = json.dumps({
        "passed": False,
        "issues": [
            {
                "category": "language_register",
                "severity": "high",
                "description": "Poetic verb: 'dance'",
                "location": "fingers dance across keys",
            }
        ],
    })
    rewritten_prompt = "Right hand wraps body, thumb braced left edge. Index finger taps the top-left keycap, keycap plunges downward 2mm, springs back up. This is a sufficiently long rewrite."

    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _make_response(phase1_json),
        _make_response(rewritten_prompt),
    ]
    mock_client.return_value = (client, "openai/gpt-4o-mini", None)

    state = _base_state(
        video_prompt="fingers dance across keys playfully in a flutter of motion that is quite long enough"
    )
    original = state["video_prompt"]
    result = validate_prompt_node(state)

    assert "error" not in result
    assert result["video_prompt"] == rewritten_prompt
    assert result["prompt_validation"]["original_prompt"] == original
    assert result["prompt_validation"]["rewritten"] is True
    assert result["prompt_validation"]["passed"] is False


def test_skips_on_empty_prompt():
    """Empty video_prompt → skip, no error."""
    result = validate_prompt_node({"video_prompt": "", "product_mechanics": "rules"})

    assert "error" not in result
    assert result["prompt_validation"]["status"] == "skipped"
    assert result["prompt_validation"]["reason"] == "empty_video_prompt"


def test_skips_on_empty_mechanics():
    """Empty product_mechanics → skip, no error."""
    result = validate_prompt_node({"video_prompt": "a valid prompt", "product_mechanics": ""})

    assert "error" not in result
    assert result["prompt_validation"]["status"] == "skipped"
    assert result["prompt_validation"]["reason"] == "empty_product_mechanics"


@patch("src.pipeline.nodes.validate_prompt.get_openrouter_client")
def test_skips_on_llm_error(mock_client):
    """Client returns error → skip, no error field."""
    mock_client.return_value = (None, "", "OPENROUTER_API_KEY not set")

    result = validate_prompt_node(_base_state())

    assert "error" not in result
    assert result["prompt_validation"]["status"] == "skipped"
    assert "llm_unavailable" in result["prompt_validation"]["reason"]


@patch("src.pipeline.nodes.validate_prompt.get_openrouter_client")
def test_keeps_original_on_rewrite_failure(mock_client):
    """Phase 2 returns garbage (<50 chars) → original preserved, rewrite_failed=True."""
    phase1_json = json.dumps({
        "passed": False,
        "issues": [
            {
                "category": "spatial_anchoring",
                "severity": "high",
                "description": "No grip geometry",
                "location": "hand interacts with device",
            }
        ],
    })

    client = MagicMock()
    client.chat.completions.create.side_effect = [
        _make_response(phase1_json),
        _make_response("short"),  # too short rewrite
    ]
    mock_client.return_value = (client, "openai/gpt-4o-mini", None)

    state = _base_state()
    original = state["video_prompt"]
    result = validate_prompt_node(state)

    assert "error" not in result
    assert "video_prompt" not in result  # original kept, not overwritten
    assert result["prompt_validation"]["rewrite_failed"] is True
    assert result["prompt_validation"]["original_prompt"] == original


@patch("src.pipeline.nodes.validate_prompt.get_openrouter_client")
def test_never_sets_error(mock_client):
    """Exception during LLM call → no 'error' key in result."""
    client = MagicMock()
    client.chat.completions.create.side_effect = RuntimeError("connection refused")
    mock_client.return_value = (client, "openai/gpt-4o-mini", None)

    result = validate_prompt_node(_base_state())

    assert "error" not in result
    assert result["prompt_validation"]["status"] == "skipped"
    assert "exception" in result["prompt_validation"]["reason"]
