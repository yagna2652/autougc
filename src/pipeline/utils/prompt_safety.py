"""
Prompt Safety Utilities.

Sanitizes motion prompts for video generation to reduce moderation failures while
preserving core product-demo intent.
"""

from __future__ import annotations

import re

# Internal clip IDs / tokenized labels (e.g. mkc_closeup_click_loop_01)
_INTERNAL_TOKEN_RE = re.compile(r"\b[a-z]{2,}(?:_[a-z0-9]+){1,}\b", re.IGNORECASE)

# Keep prompt focused on neutral product-demo language.
_SAFE_REPLACEMENTS = {
    "squeeze": "press",
    "squeezes": "presses",
    "flick": "tap",
    "flicks": "taps",
    "snappy": "smooth",
    "rhythmic": "steady",
}

# Sentence-level allowlist keywords (if none match, sentence is dropped).
_ALLOWLIST_TERMS = {
    "product",
    "hand",
    "switch",
    "keyboard",
    "camera",
    "frame",
    "framing",
    "lighting",
    "material",
    "detail",
    "texture",
    "logo",
    "press",
    "release",
    "tap",
    "movement",
    "motion",
    "indoor",
    "neutral",
    "natural",
    "realistic",
    "photoreal",
}


def sanitize_video_prompt(prompt: str, max_words: int = 120) -> str:
    """
    Sanitize a video prompt using conservative, policy-safer transformations.
    """
    if not prompt:
        return "Photoreal product demonstration video with neutral camera movement."

    text = prompt

    # 1) Remove internal clip IDs/tokens.
    text = _INTERNAL_TOKEN_RE.sub("", text)

    # 2) Normalize risky-but-benign wording into neutral alternatives.
    for src, dst in _SAFE_REPLACEMENTS.items():
        text = re.sub(rf"\b{re.escape(src)}\b", dst, text, flags=re.IGNORECASE)

    # 3) Normalize spaces/punctuation.
    text = re.sub(r"[^\w\s.,:;'\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # 4) Allowlist filter at sentence level.
    raw_sentences = re.split(r"(?<=[.!?])\s+", text)
    kept: list[str] = []
    for sentence in raw_sentences:
        lowered = sentence.lower()
        if any(term in lowered for term in _ALLOWLIST_TERMS):
            kept.append(sentence.strip())

    if not kept:
        kept = [text]

    sanitized = " ".join(kept).strip()

    # 5) Clamp to max words to reduce moderation ambiguity.
    words = sanitized.split()
    if len(words) > max_words:
        sanitized = " ".join(words[:max_words]).rstrip(".,:; ")

    # 6) Ensure neutral product-demo anchor.
    if "product" not in sanitized.lower():
        sanitized = (
            "Photoreal product demonstration video. " + sanitized
            if sanitized
            else "Photoreal product demonstration video with neutral camera movement."
        )

    return sanitized
