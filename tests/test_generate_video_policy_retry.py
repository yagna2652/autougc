import contextlib

import src.pipeline.nodes.generate_video as gv


class _DummySpan:
    def set_error(self, _msg):
        return None

    def set_outputs(self, outputs=None, metadata=None):
        return None


@contextlib.contextmanager
def _dummy_trace_span(**kwargs):
    yield _DummySpan()


def test_generate_video_retries_with_safe_prompt_on_content_policy(monkeypatch):
    calls = []

    def fake_call_fal_api(**kwargs):
        calls.append(kwargs["prompt"])
        if len(calls) == 1:
            raise gv.FalApiError("content_policy_violation: blocked by content checker")
        return {"video": {"url": "https://example.com/video.mp4"}}

    monkeypatch.setenv("FAL_KEY", "test-key")
    monkeypatch.setattr(gv, "_call_fal_api", fake_call_fal_api)
    monkeypatch.setattr(gv, "trace_span", _dummy_trace_span)

    state = {
        "video_prompt": (
            "The hand squeezes switch and performs mkc_closeup_click_loop_01 with flick."
        ),
        "product_images": ["data:image/png;base64,abc"],
        "scene_image_url": "https://fal.media/scene.png",
        "config": {"video_model": "sora", "video_duration": 4, "aspect_ratio": "9:16"},
    }

    result = gv.generate_video_node(state)

    assert result["generated_video_url"] == "https://example.com/video.mp4"
    assert len(calls) == 2
    assert "mkc_closeup_click_loop_01" not in calls[0]
    assert calls[0] != calls[1]
