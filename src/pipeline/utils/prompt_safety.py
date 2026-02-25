"""
Prompt Safety Utilities.

Light sanitization of motion prompts for video generation — strips internal
token IDs and normalises whitespace while preserving the full prompt text,
fidget verbs, and negative constraints (DO NOT SHOW blocks).
"""

from __future__ import annotations

import re

# Internal clip IDs / tokenized labels (e.g. mkc_closeup_click_loop_01)
_INTERNAL_TOKEN_RE = re.compile(r"\b[a-z]{2,}(?:_[a-z0-9]+){2,}\b", re.IGNORECASE)


def sanitize_video_prompt(prompt: str, max_words: int = 0) -> str:
    """
    Lightly sanitize a video prompt.

    Only removes internal clip-ID tokens and normalises whitespace.
    The full prompt (including DO NOT SHOW blocks) is preserved so the
    video model receives all constraints.

    Args:
        prompt: Raw video prompt text.
        max_words: Optional word cap. 0 means no limit (default).

    Returns:
        Cleaned prompt string.
    """
    if not prompt:
        return "Photoreal product demonstration video with neutral camera movement."

    text = prompt

    # 1) Remove internal clip IDs/tokens.
    text = _INTERNAL_TOKEN_RE.sub("", text)

    # 2) Normalise whitespace (preserve newlines for DO NOT SHOW blocks).
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    # 3) Optional word cap (disabled by default).
    if max_words > 0:
        words = text.split()
        if len(words) > max_words:
            text = " ".join(words[:max_words])

    return text
