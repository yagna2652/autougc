# Pipeline Migration: Kling V3 I2V → O3 Reference-to-Video

## Why This Is a Different Model

The current pipeline uses `fal-ai/kling-video/v3/pro/image-to-video`. This is a standard image-to-video model: it takes one starting image, a text prompt, and optional identity elements, then generates video by animating frame 1 according to the text description.

`fal-ai/kling-video/o3/standard/reference-to-video` is architecturally different. It's a **reference-conditioned** model — it can accept up to 7 simultaneous visual inputs (elements, scene images, style references, video motion references) and the prompt orchestrates how they compose together. The key differences:

- **Elements can include video references.** Each element can have a `video_url` — a short clip of that element in motion. The model extracts the motion pattern and applies it while maintaining the element's visual identity. This is the equivalent of AnchorCrafter's "template motion video" concept, but as a single API parameter.
- **Scene images (`@Image1`, `@Image2`...) as composition context.** Separate from elements, these provide scene/style/framing references without identity tracking.
- **Multi-shot storyboarding as first-class feature.** `multi_prompt` breaks the video into discrete shots with individual prompts and durations — formalizes the state-machine prompt structure that worked in manual testing.
- **`@Element1` notation in prompts.** The model uses visual references when it sees `@Element1`, not text descriptions. This tells the model "look at the reference images for what this thing looks like" instead of hallucinating from text.

In short: the current pipeline sends a starting image + a hope (text prompt) + a weak hint (1 reference image). O3 reference-to-video sends a starting image + explicit visual identity references + optional motion reference video + structured multi-shot prompts. It's a fundamentally richer control surface.

---

## Current Pipeline Architecture

```
TikTok URL + Product Images
        │
        ▼
┌─────────────────┐
│  Analyze Video   │  ← extracts style, action patterns
└────────┬────────┘
         ▼
┌─────────────────┐
│  Generate Scene  │  ← Nano Banana Pro: product photo + text → composited frame 1
│  Image (Frame 1) │     (loose product interpretation, often wrong)
└────────┬────────┘
         ▼
┌─────────────────┐
│  Generate Video  │  ← Kling V3 I2V: frame 1 + text prompt + optional 1 reference
│  Prompt (LLM)    │     (text prompt as loose suggestion, no @Element notation)
└────────┬────────┘
         ▼
┌─────────────────┐
│  _call_fal_api() │  ← endpoint: fal-ai/kling-video/v3/pro/image-to-video
│                   │     sends: start_image_url, prompt, duration, aspect_ratio,
│                   │            end_image_url (optional), elements (optional, 1 ref)
└────────┬────────┘
         ▼
      Output Video
```

### What the current `_call_fal_api()` sends:

```python
api_input = {
    "prompt": prompt,                    # free-text, no @Element references
    "start_image_url": image_url,        # Nano Banana composite (often wrong)
    "duration": str(duration),
    "aspect_ratio": aspect_ratio,
}
if tail_image_url:
    api_input["end_image_url"] = tail_image_url

if identity_images:
    frontal = identity_images[0]
    references = identity_images[1:2]     # only 1 reference image max
    if not references:
        references = [frontal]            # duplicates frontal if nothing else
    api_input["elements"] = [{
        "frontal_image_url": frontal,
        "reference_image_urls": references,
    }]
```

### Problems with this approach:
1. **No `@Element1` in prompt** — model doesn't know to use visual reference for identity
2. **Max 1 reference image** — code slices `[1:2]`, loses additional angles
3. **No video motion reference** — elements never include `video_url`
4. **No multi-shot** — single long prompt, not structured beats
5. **No `@Image1` scene references** — no style/framing context
6. **Frame 1 often wrong** — Nano Banana composites product loosely
7. **Identity pack defaults OFF** — zero elements sent in most runs

---

## Target Pipeline Architecture

```
Product Images + Real Photo (hand holding product) + Optional Motion Video
        │
        ▼
┌──────────────────────┐
│  Prepare Product Pack │  ← NEW: background removal, multi-angle preparation
│                        │     outputs: frontal_url, reference_urls[], motion_video_url
└────────┬─────────────┘
         ▼
┌──────────────────────┐
│  Generate Video       │  ← NEW: structured prompt with @Element1 notation
│  Prompt (LLM)         │     outputs: prompt or multi_prompt with state-machine beats
└────────┬─────────────┘
         ▼
┌──────────────────────┐
│  _call_fal_api()      │  ← endpoint: fal-ai/kling-video/o3/standard/reference-to-video
│                        │     sends: prompt (with @Element1), start_image_url (real photo),
│                        │            end_image_url (same real photo), elements (frontal +
│                        │            3+ references + optional video_url), duration
└────────┬─────────────┘
         ▼
      Output Video
```

---

## What Needs to Change (by component)

### 1. New Node: `prepare_product_pack`

**Purpose:** Takes raw product images from user, produces a clean element pack optimized for O3 reference-to-video.

**Inputs:**
- `product_images[]` — user-uploaded product photos (any angles)
- `product_in_hand_photo` — optional real photo of hand holding product (replaces Nano Banana)
- `product_motion_video` — optional 3-8s clip of someone interacting with the product

**Processing:**
- Run background removal (rembg or SAM2 on fal.ai) on each product image → clean product on transparent/white background
- Select best frontal image (largest face area, most centered)
- Remaining images become reference angles
- If only 1 image provided: optionally use Kling Image 3.0 to generate additional angles (or duplicate frontal as minimum)
- Upload all processed images to fal CDN
- If motion video provided, upload to fal CDN

**Outputs:**
```python
{
    "product_element": {
        "frontal_image_url": "https://fal.media/...",       # clean product, front angle
        "reference_image_urls": [                             # 2-4 additional angles
            "https://fal.media/...",
            "https://fal.media/...",
        ],
        "video_url": "https://fal.media/..." or None,        # motion reference
    },
    "start_image_url": "https://fal.media/...",              # real photo or best composite
    "end_image_url": "https://fal.media/...",                # same as start (loop anchor)
}
```

**Key decision:** If the user provides a real photo of the product being held, use that as `start_image_url` directly. This skips Nano Banana entirely and eliminates the biggest source of error (bad frame 1). If no real photo is available, fall back to Nano Banana for compositing — but this is now the exception, not the default.

---

### 2. Modified Node: `generate_video_prompt`

**Current behavior:** LLM writes a free-text motion description like "The index finger presses down on the top keycap, which sinks 2mm..."

**New behavior:** LLM writes a prompt that:
- References the product as `@Element1` (never describes product appearance in text)
- Uses state-machine structure: one action per beat, explicit stationarity between actions
- Uses mechanical verbs only (presses, sinks, springs, lifts — not "fidgets with" or "plays with")
- Specifies camera behavior (steady, slight pan, etc.)

**Single prompt output example:**
```
Close-up of a hand holding @Element1 vertically against a clean background.
The index finger presses down on one keycap of @Element1, it clicks down and
springs back. The other three keycaps remain raised. The hand grip stays steady
throughout. Steady camera, natural lighting.
```

**Multi-prompt output example:**
```json
{
    "multi_prompt": [
        {
            "prompt": "Close-up of a hand holding @Element1 steady. All four keycaps raised. Hand relaxed, fingers wrapped around body. Steady camera, soft background.",
            "duration": 2
        },
        {
            "prompt": "Index finger presses down firmly on top-right keycap of @Element1. Keycap sinks with visible click and springs back. Finger lifts. Other three keys untouched. Camera holds steady.",
            "duration": 3
        }
    ]
}
```

**Prompt generation rules to enforce:**
- MUST contain `@Element1` at least once
- MUST NOT describe product appearance (color, material, shape) — model gets that from visual references
- MUST describe only motion and camera
- Each beat: one action, one subject (finger), explicit state of everything else
- Camera instruction in every beat

---

### 3. Modified: `_call_fal_api()`

**Current signature:**
```python
def _call_fal_api(
    fal_key, endpoint, image_url, prompt, duration,
    aspect_ratio, tail_image_url=None, identity_images=None
)
```

**New signature:**
```python
def _call_fal_api(
    fal_key, endpoint, prompt, duration, aspect_ratio,
    start_image_url=None,
    end_image_url=None,
    elements=None,          # list of element dicts (frontal + refs + optional video)
    image_urls=None,        # scene/style reference images (@Image1, @Image2)
    multi_prompt=None,      # list of {prompt, duration} for multi-shot
    cfg_scale=0.5,
)
```

**New API call construction for O3 reference-to-video:**
```python
if "o3" in endpoint and "reference-to-video" in endpoint:
    api_input = {
        "duration": str(duration),
        "aspect_ratio": aspect_ratio,
    }

    # Prompt: single or multi-shot
    if multi_prompt:
        api_input["multi_prompt"] = multi_prompt
    else:
        api_input["prompt"] = prompt

    # Frame anchors
    if start_image_url:
        api_input["start_image_url"] = start_image_url
    if end_image_url:
        api_input["end_image_url"] = end_image_url

    # Scene/style references (@Image1, @Image2...)
    if image_urls:
        api_input["image_urls"] = image_urls

    # Elements (@Element1, @Element2...) — each with frontal + refs + optional video
    if elements:
        api_input["elements"] = [
            {
                "frontal_image_url": el["frontal_image_url"],
                "reference_image_urls": el["reference_image_urls"],
                **({"video_url": el["video_url"]} if el.get("video_url") else {}),
            }
            for el in elements
        ]

    if cfg_scale != 0.5:
        api_input["cfg_scale"] = cfg_scale
```

---

### 4. Modified: `MODEL_ENDPOINTS`

**Add new entry:**
```python
MODEL_ENDPOINTS = {
    "sora": "fal-ai/sora-2/image-to-video/pro",
    "kling": "fal-ai/kling-video/v2.1/pro/image-to-video",
    "kling-v3": "fal-ai/kling-video/v3/pro/image-to-video",
    "kling-o3-ref": "fal-ai/kling-video/o3/standard/reference-to-video",   # NEW
    "kling-o3-ref-pro": "fal-ai/kling-video/o3/pro/reference-to-video",    # NEW
}
```

Make `kling-o3-ref` the default for product interaction videos.

---

### 5. Scene Image Generation: Demoted, Not Removed

Nano Banana Pro (`generate_scene_image` node) becomes **optional fallback** only used when:
- User doesn't provide a real photo of the product being held
- AND no suitable product-in-hand image can be sourced

When the user provides a real photo of someone holding the product, the pipeline skips scene image generation entirely. The real photo becomes `start_image_url` directly.

This is the single highest-leverage change. Your manual testing already proved this: real photo as frame 1 → O3 reference-to-video with elements → mechanics that are "extremely close to how I want them."

---

### 6. Config Changes

**New config fields:**
```json
{
    "video_model": "kling-o3-ref",
    "use_real_photo_as_start": true,
    "use_multi_shot": true,
    "product_motion_video_url": null,
    "cfg_scale": 0.5,
    "max_reference_images": 4,
    "prompt_must_reference_elements": true
}
```

**Deprecated config fields:**
- `use_identity_pack` → replaced by elements always being sent (they're required for this model)
- `stationary_elements` as free-text → replaced by state-machine prompt structure

---

## Migration Path (ordered by priority)

### Phase 1: Make It Work (immediate)
1. Add `kling-o3-ref` to `MODEL_ENDPOINTS`
2. Modify `_call_fal_api()` to handle O3 reference-to-video schema
3. Ensure elements are always sent (not optional) with frontal + all available references
4. Add `@Element1` to prompt generation template
5. Wire `start_image_url` = `end_image_url` = real product photo when available

### Phase 2: Add Multi-Shot (next)
1. Modify prompt generation LLM to output `multi_prompt` format
2. Add validation: each beat must contain `@Element1`, one action, camera instruction
3. Test 2-shot vs 3-shot vs single prompt on same product

### Phase 3: Add Video Motion Reference (high value)
1. Add `video_url` support to element construction
2. Accept user-uploaded product interaction clips
3. Film 5-10 generic template clips (hand pressing buttons, hand turning object, hand clicking) that can be reused across products
4. Test: same prompt with vs without video reference

### Phase 4: Product Pack Preparation (polish)
1. Build `prepare_product_pack` node with background removal
2. Auto-generate additional angles from single product image
3. Quality validation: reject blurry/cropped/partial product images

---

## What This Means for the User-Facing Workflow

**Current:** User provides TikTok URL + product photos on white background → pipeline does everything.

**New (recommended):** User provides product photos (any angles) + one real photo of someone holding the product + optional 3-second clip of someone interacting with the product → pipeline animates from real starting position with full visual identity.

**New (fallback):** User provides only product photos → pipeline uses Nano Banana to composite frame 1 (lower quality, same as current behavior).

The "recommended" path front-loads 30 seconds of user effort (take a photo holding the product) in exchange for dramatically better output quality. For product companies making ads, this is trivial — they already have these photos.

---

## Summary: What Changed and Why

| Aspect | Current Pipeline | O3 Reference Pipeline |
|--------|-----------------|----------------------|
| **Model** | `kling-video/v3/pro/image-to-video` | `kling-video/o3/standard/reference-to-video` |
| **Frame 1** | Nano Banana composite (often wrong) | Real photo of product in hand (skip generation) |
| **End frame** | Optional, often unused | Same as start frame (loop anchor, always sent) |
| **Elements** | Off by default, max 1 reference | Always on, 3-4 references, optional video |
| **Prompt** | Free-text motion description | `@Element1` notation, state-machine beats |
| **Multi-shot** | Not supported | First-class: 2-3 shots with individual durations |
| **Motion reference** | None | Optional video_url per element |
| **Product identity** | Model guesses from frame 1 alone | Model has frontal + multi-angle + video reference |
| **Scene generation** | Required (Nano Banana) | Optional fallback only |
