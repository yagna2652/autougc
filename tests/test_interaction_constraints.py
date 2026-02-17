from src.pipeline.nodes.generate_prompt import (
    _append_negative_constraints,
    _extract_impossible_interactions,
)
from src.pipeline.state import create_initial_state
from unittest.mock import patch


def test_extract_impossible_interactions_from_mechanics_section():
    mechanics = """
Core behavior text.

Impossible interactions:
- two-handed typing
- pressing outside keycaps
"""

    constraints = _extract_impossible_interactions(mechanics)

    assert constraints == ["two-handed typing", "pressing outside keycaps"]


def test_append_negative_constraints_adds_do_not_block():
    prompt = "Close-up shot. Right index finger presses one key at a time."
    negative = "Do NOT show two-handed typing; Do NOT show product spinning"

    merged = _append_negative_constraints(prompt, negative)

    assert "DO NOT SHOW:" in merged
    assert "- Do NOT show two-handed typing" in merged
    assert "- Do NOT show product spinning" in merged


def test_create_initial_state_autoloads_default_mechanics():
    mocked_product = {
        "description": "Mock product",
        "images": ["mock-image-data"],
        "category": "mechanical_keyboard_keychain",
        "mechanics": "Base mechanics.\n\nImpossible interactions:\n- two-handed typing",
    }
    with patch("src.pipeline.product_loader.load_product", return_value=mocked_product):
        state = create_initial_state(
            video_url="https://example.com/video.mp4",
            product_images=[],
        )

    assert state["product_images"]
    assert state["product_mechanics"]
    assert "Impossible interactions:" in state["product_mechanics"]
