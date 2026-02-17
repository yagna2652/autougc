"""
Identity Reference Selector - Rule-based selection for product identity packs.

Chooses the smallest useful subset of references for a shot based on
scene/prompt context to improve product form-factor consistency.
"""

from typing import Any


def select_identity_references(
    identity_pack: dict[str, str] | None,
    video_analysis: dict[str, Any] | None = None,
    scene_description: str = "",
) -> tuple[list[str], list[str]]:
    """
    Select identity reference images from a SKU identity pack.

    Rules:
    - Always include front view when available.
    - Include side/back for rotation/pan/yaw style cues.
    - Include logo close-up for close-up/logo readability cues.
    - Include material close-up for reflective/material-detail cues.

    Returns:
        Tuple of (selected_sources, reasons).
    """
    if not identity_pack:
        return [], []

    analysis_text = " ".join(
        [
            str(video_analysis.get("actions", "")) if video_analysis else "",
            str(video_analysis.get("style", "")) if video_analysis else "",
            str(video_analysis.get("setting", "")) if video_analysis else "",
            str(video_analysis.get("mood", "")) if video_analysis else "",
            str(video_analysis.get("lighting", "")) if video_analysis else "",
            str(video_analysis.get("text_overlays", "")) if video_analysis else "",
            str(video_analysis.get("what_makes_it_work", "")) if video_analysis else "",
            scene_description or "",
        ]
    ).lower()

    selected: list[str] = []
    reasons: list[str] = []

    def add_if_present(key: str, reason: str) -> None:
        value = identity_pack.get(key, "")
        if value and value not in selected:
            selected.append(value)
            reasons.append(reason)

    # Default anchor for overall product geometry.
    add_if_present("front", "front anchor")

    rotation_keywords = (
        "pan",
        "rotate",
        "rotation",
        "orbit",
        "spin",
        "turn",
        "angle",
        "yaw",
        "around",
    )
    if any(word in analysis_text for word in rotation_keywords):
        add_if_present("side_45", "rotation cue")
        add_if_present("back", "rotation cue")

    closeup_keywords = (
        "close-up",
        "close up",
        "macro",
        "detail",
        "logo",
        "brand",
        "text",
        "label",
        "marking",
    )
    if any(word in analysis_text for word in closeup_keywords):
        add_if_present("close_up_logo", "close-up/logo cue")

    material_keywords = (
        "material",
        "texture",
        "finish",
        "metal",
        "metallic",
        "gloss",
        "glossy",
        "reflective",
        "specular",
    )
    if any(word in analysis_text for word in material_keywords):
        add_if_present("close_up_material", "material/detail cue")

    # Fallback if front is not provided.
    if not selected:
        for key in ("side_45", "back", "close_up_logo", "close_up_material", "top"):
            value = identity_pack.get(key, "")
            if value:
                selected.append(value)
                reasons.append("fallback reference")
                break

    return selected, reasons
