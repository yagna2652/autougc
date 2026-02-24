# Prompt Engineering

Current state of the prompt strategy for video generation.

## Pipeline Flow

```
config.json → _build_mechanics_text() → {product_mechanics}
                                              ↓
TikTok frames → analyze_video (OpenRouter Vision) → {video_analysis}
                                              ↓
generate_prompt (OpenRouter LLM) ← mechanics + analysis + interaction library
                                              ↓
                                    video_prompt (raw)
                                              ↓
                              sanitize_video_prompt() — strips clip IDs, normalises whitespace
                                              ↓
                              _append_negative_constraints() — adds DO NOT SHOW block
                                              ↓
                                    video_prompt (final) → Kling/Sora via Fal.ai
```

## Key Files

| File | Role |
|---|---|
| `src/pipeline/nodes/generate_prompt.py` | LLM system prompt + response parsing |
| `src/pipeline/utils/prompt_safety.py` | Light sanitization before sending to video model |
| `src/pipeline/product_loader.py` | Assembles mechanics text from config.json |
| `assets/products/keychain/config.json` | Product ground truth |
| `assets/interaction_library/index.json` | Clip library for beat planning |

## LLM Output Format

The LLM returns JSON with 4 fields:
- `video_prompt` — beat-by-beat motion description (this goes to Kling)
- `negative_prompt` — semicolon-separated forbidden motions
- `script` — casual TikTok script (1–3 sentences)
- `scene_description` — photorealistic first-frame prompt for scene image generation

## Sanitization (prompt_safety.py)

As of 2026-02-24, sanitization is minimal:
- Strips internal clip ID tokens (e.g. `mkc_closeup_click_loop_01`)
- Normalises whitespace (preserves newlines for DO NOT SHOW blocks)
- No word cap (was 120 words, now unlimited)
- No verb replacements (was replacing squeeze→press, flick→tap)
- No sentence-level allowlist filtering

## What to Watch For

- **max_tokens on LLM call**: Currently removed (was 2000, caused truncation). If response gets too large, the LLM may still self-truncate. Monitor output length.
- **DO NOT SHOW block**: Must survive sanitization. Check with `test_prompt_only.py`.
- **Fidget verbs**: The LLM tends toward "click/tap/press" instead of "squeeze/plunge/bounce". May need stronger instruction in the system prompt.

## Resolved: Instruction Vocabulary Aligned with Config (2026-02-24)

The system prompt in `generate_prompt.py` now matches the config.json fidget-toy vocabulary.

**What changed in both `_build_prompt_request` and `_build_prompt_request_openrouter`:**

| Section | Before | After |
|---|---|---|
| PHYSICS CONSTRAINTS | "click/press count," "finger choreography" | "keys plunging downward, sinking, springing back up" |
| FOCUS ON MOTION | generic hand verbs (pull, click, flip) | fidget energy, keycap contact points, key physics |
| Motion verb list | pull, click, flip, rotate, press, slide, reveal | squeeze, plunge, crunch, bounce, drum, spring, sink, press |
| CRITICAL REQ #12 | "name the active finger(s)" | "device held VERTICALLY, chain dangling" |
| video_prompt field | "technical manual" framing | "vivid cinematic scene description" |

**Also fixed in config.json:**
- `stationary_elements` — fingers no longer "locked in curled position"; palm/back are the stable parts
- `timing` — "reset the thumb position" → "reset finger position"
