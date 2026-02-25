# Video Generation

How the video model (Kling/Sora) receives and interprets prompts.

## Models Available

| Model | Endpoint | Durations | Notes |
|---|---|---|---|
| Sora 2 | `fal-ai/sora-2/image-to-video/pro` | 4, 8, 12s only | Limited duration options |
| Kling 2.1 | `fal-ai/kling-video/v2.1/pro/image-to-video` | Any | Supports tail_image_url |
| Kling 3.0 | `fal-ai/kling-video/v3/pro/image-to-video` | Any | Supports elements (identity pack) |

## I2V Pipeline

1. Scene image (from Nano Banana Pro) or product image uploaded to Fal CDN
2. Sanitized `video_prompt` sent as the motion prompt
3. Video model generates from the starting image + prompt

**File:** `src/pipeline/nodes/generate_video.py`

## How Kling Interprets Prompts

Kling is a video generation model, not a language model. It interprets prompts as **visual scene descriptions**, not technical instructions.

### What works
- Visual, cinematic descriptions ("hand squeezes the device, keys bounce under the fingers")
- Simple, concrete motions
- Short sentences with one action each

### What doesn't work
- Technical anatomy instructions ("index finger moves to click the top keycap")
- Long compound sentences with multiple simultaneous constraints
- Describing things that are already visible in the starting image

## Known Issues

### Horizontal default
Kling defaults to horizontal keyboard orientation because 99.9% of its training data shows keyboards that way. The word "VERTICALLY" must appear prominently in the opening sentence.

### Typing priors
Words like "click" and "tap" trigger typing/button-pressing visual priors. Prefer: "squeeze", "crunch", "bounce", "plunge", "drum".

### Anatomical impossibility
If the prompt describes fingers locked behind the device AND pressing the front, the model compromises with an awkward pinch grip. The new "wrapped fist" grip avoids this.

### Truncation
Previously the prompt was capped at 120 words by `sanitize_video_prompt()`. This has been removed. Full prompt now reaches the model.

## Identity Fidelity Controls

- `use_tail_image` — uses same image as end frame for shape consistency
- `use_identity_pack` — multi-angle reference images (Kling V3 elements)
- `use_anchor_frames` — generates keyframes first, then motion segments

## Content Policy Fallback

If Kling rejects a prompt for content policy violation, the pipeline automatically retries once with a safer fallback prompt (`_build_safety_fallback_prompt`).
