import sys
import types

from src.pipeline.nodes.generate_video import _call_fal_api


def test_call_fal_api_includes_kling_v3_elements_and_tail(monkeypatch):
    captured = {}

    def fake_subscribe(endpoint, arguments, with_logs, on_queue_update):
        captured["endpoint"] = endpoint
        captured["arguments"] = arguments
        captured["with_logs"] = with_logs
        captured["on_queue_update"] = on_queue_update
        return {"video": {"url": "https://example.com/video.mp4"}}

    monkeypatch.setitem(
        sys.modules,
        "fal_client",
        types.SimpleNamespace(subscribe=fake_subscribe),
    )

    _call_fal_api(
        fal_key="test-key",
        endpoint="fal-ai/kling-video/v3/pro/image-to-video",
        image_url="https://fal.media/start.png",
        prompt="Product rotates and ends in close-up.",
        duration=2,
        aspect_ratio="9:16",
        tail_image_url="https://fal.media/end.png",
        identity_images=[
            "https://fal.media/front.png",
            "https://fal.media/side.png",
            "https://fal.media/back.png",
        ],
    )

    args = captured["arguments"]
    assert captured["endpoint"] == "fal-ai/kling-video/v3/pro/image-to-video"
    assert args["duration"] == "2"
    assert args["start_image_url"] == "https://fal.media/start.png"
    assert args["end_image_url"] == "https://fal.media/end.png"
    assert len(args["elements"]) == 1
    assert args["elements"][0]["frontal_image_url"] == "https://fal.media/front.png"
    assert args["elements"][0]["reference_image_urls"] == ["https://fal.media/side.png"]


def test_call_fal_api_omits_tail_and_elements_for_sora(monkeypatch):
    captured = {}

    def fake_subscribe(endpoint, arguments, with_logs, on_queue_update):
        captured["endpoint"] = endpoint
        captured["arguments"] = arguments
        return {"video": {"url": "https://example.com/video.mp4"}}

    monkeypatch.setitem(
        sys.modules,
        "fal_client",
        types.SimpleNamespace(subscribe=fake_subscribe),
    )

    _call_fal_api(
        fal_key="test-key",
        endpoint="fal-ai/sora-2/image-to-video/pro",
        image_url="https://fal.media/start.png",
        prompt="Cinematic movement.",
        duration=4,
        aspect_ratio="9:16",
        tail_image_url="https://fal.media/end.png",
        identity_images=["https://fal.media/front.png"],
    )

    args = captured["arguments"]
    assert captured["endpoint"] == "fal-ai/sora-2/image-to-video/pro"
    assert args["duration"] == 4
    assert "tail_image_url" not in args
    assert "start_image_url" not in args
    assert "end_image_url" not in args
    assert "elements" not in args
