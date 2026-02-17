from src.pipeline.utils.interaction_library import resolve_clip_ids_to_plain_language


def test_resolve_clip_ids_to_plain_language_replaces_ids():
    library = {
        "clips": [
            {
                "id": "mkc_closeup_click_loop_01",
                "primitive": "closeup_click_loop",
                "framing": "macro_closeup",
                "tags": ["asmr", "tactile"],
            }
        ],
        "primitives_registry": {
            "closeup_click_loop": {
                "description": "Macro shot of fingers clicking in loop"
            }
        },
    }

    prompt = (
        "Use mkc_closeup_click_loop_01, then continue motion smoothly."
    )
    resolved = resolve_clip_ids_to_plain_language(prompt, library)

    assert "mkc_closeup_click_loop_01" not in resolved
    assert "macro closeup sequence" in resolved.lower()
    assert "macro shot of fingers clicking in loop" in resolved.lower()


def test_resolve_clip_ids_to_plain_language_noop_without_clips():
    prompt = "No clip ids here."
    assert resolve_clip_ids_to_plain_language(prompt, {"clips": []}) == prompt
