from src.pipeline.utils.prompt_safety import sanitize_video_prompt


def test_sanitize_video_prompt_removes_internal_clip_tokens():
    prompt = (
        "Close-up demo similar to mkc_closeup_click_loop_01. "
        "Hand squeezes and flicks switches in snappy motion."
    )

    sanitized = sanitize_video_prompt(prompt)

    assert "mkc_closeup_click_loop_01" not in sanitized
    assert "squeezes" not in sanitized.lower()
    assert "flicks" not in sanitized.lower()
    assert "presses" in sanitized.lower() or "tap" in sanitized.lower()


def test_sanitize_video_prompt_filters_non_allowlisted_sentences():
    prompt = (
        "This sentence is abstract and unrelated to the scene. "
        "A hand presses a keyboard switch with natural lighting and stable camera."
    )

    sanitized = sanitize_video_prompt(prompt)

    assert "hand presses a keyboard switch" in sanitized.lower()
