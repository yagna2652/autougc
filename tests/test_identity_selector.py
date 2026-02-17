from src.pipeline.utils.identity_selector import select_identity_references


def test_select_identity_references_uses_motion_closeup_and_material_cues():
    identity_pack = {
        "front": "front-img",
        "side_45": "side-img",
        "back": "back-img",
        "close_up_logo": "logo-img",
        "close_up_material": "material-img",
    }
    video_analysis = {
        "actions": "camera pans around the product and then rotates",
        "lighting": "glossy reflective highlights",
    }
    scene_description = "Cut to close-up where brand logo is sharp and readable."

    selected, reasons = select_identity_references(
        identity_pack=identity_pack,
        video_analysis=video_analysis,
        scene_description=scene_description,
    )

    assert selected == [
        "front-img",
        "side-img",
        "back-img",
        "logo-img",
        "material-img",
    ]
    assert len(reasons) == len(selected)


def test_select_identity_references_fallback_without_front():
    identity_pack = {
        "side_45": "side-img",
        "back": "back-img",
    }

    selected, reasons = select_identity_references(identity_pack=identity_pack)

    assert selected == ["side-img"]
    assert reasons == ["fallback reference"]
