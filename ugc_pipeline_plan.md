# UGC Ad Generation Pipeline - Detailed Implementation Plan

## Overview

A Python pipeline that generates UGC-style ads by:
1. Taking your product info + target audience → generating modular scripts
2. Using reference TikToks → extracting motion/style for authentic feel
3. Generating avatar videos (talking head) + product videos (B-roll)
4. Assembling variations (5 hooks × 5 bodies × 5 CTAs = 125 combinations)

---

## Part 1: Script Generation (Claude API)

### What Goes In

You provide a `ProductInfo` object:

```python
product_info = {
    "name": "GlowSkin Vitamin C Serum",
    "category": "skincare",
    "price": "$29.99",
    "key_benefits": [
        "Brightens skin in 2 weeks",
        "Reduces dark spots",
        "Lightweight, non-greasy formula"
    ],
    "unique_selling_point": "3x more vitamin C than competitors",
    "social_proof": "50,000+ 5-star reviews",
    "target_audience": {
        "age_range": "25-40",
        "gender": "female",
        "pain_points": [
            "Dull, tired-looking skin",
            "Dark spots from sun damage",
            "Products that feel greasy"
        ],
        "desires": [
            "Glowing, radiant skin",
            "Quick results",
            "Simple routine"
        ]
    },
    "tone": "friendly, relatable, Gen-Z casual",
    "competitor_weaknesses": "Most serums are either too weak or too irritating"
}
```

### What Comes Out

The Claude API generates **modular script components**:

```python
scripts = {
    "hooks": [
        {
            "id": "hook_1",
            "text": "POV: You finally found a vitamin C serum that actually works",
            "duration_seconds": 3,
            "style": "pov_trend"
        },
        {
            "id": "hook_2",
            "text": "I was today years old when I learned why my skin looked so dull",
            "duration_seconds": 3,
            "style": "revelation"
        },
        # ... 3 more hooks
    ],
    "bodies": [
        {
            "id": "body_1",
            "text": "I've been using this for two weeks and look at the difference. My dark spots are fading, my skin is actually glowing, and it doesn't feel greasy at all.",
            "duration_seconds": 12,
            "framework": "testimonial"
        },
        {
            "id": "body_2",
            "text": "Here's the thing about vitamin C serums - most of them don't have enough vitamin C to actually do anything. This one has 3x more than the leading brands, and you can literally see the results.",
            "duration_seconds": 15,
            "framework": "education"
        },
        # ... 3 more bodies
    ],
    "ctas": [
        {
            "id": "cta_1",
            "text": "Link in bio - they're running 20% off right now",
            "duration_seconds": 3,
            "urgency": "discount"
        },
        {
            "id": "cta_2",
            "text": "Trust me, your skin will thank you. Link below.",
            "duration_seconds": 3,
            "urgency": "soft"
        },
        # ... 3 more CTAs
    ]
}
```

### How It Works (The Prompt)

```python
SCRIPT_GENERATION_PROMPT = """
You are a UGC ad copywriter who creates viral TikTok/Reels scripts.

## Product Information
{product_info_json}

## Your Task
Generate modular script components that can be mixed and matched:

### HOOKS (5 variations)
- 3 seconds or less
- Must stop the scroll immediately
- Use these proven patterns:
  * POV: ... (relatable situation)
  * "I was today years old when..."
  * "Nobody talks about this but..."
  * Direct question to viewer
  * Controversial/surprising statement

### BODIES (5 variations)
- 10-15 seconds each
- Use these frameworks:
  * TESTIMONIAL: Personal experience + visible results
  * EDUCATION: "Here's what most people don't know..."
  * PROBLEM-AGITATION: Emphasize pain point, then reveal solution
  * DEMONSTRATION: Show the product in action
  * SOCIAL PROOF: Reviews, numbers, celebrity mentions

### CTAs (5 variations)
- 3 seconds or less
- Include: soft sell, urgency, discount, curiosity, FOMO

## Output Format
Return JSON with hooks[], bodies[], ctas[] arrays.
Each item needs: id, text, duration_seconds, and style/framework.

## Tone Guidelines
{tone_guidelines}

## Important
- Write like a real person talking to camera, not an ad
- Use casual language, contractions, filler words
- Reference TikTok/Reels trends when appropriate
- Never sound corporate or salesy
"""
```

### Implementation

```python
class ScriptGenerator:
    def __init__(self, anthropic_api_key: str):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)

    def generate(self, product_info: dict, num_hooks=5, num_bodies=5, num_ctas=5) -> dict:
        """Generate modular script components."""

        prompt = SCRIPT_GENERATION_PROMPT.format(
            product_info_json=json.dumps(product_info, indent=2),
            tone_guidelines=product_info.get("tone", "casual, friendly")
        )

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse JSON from response
        scripts = json.loads(response.content[0].text)
        return scripts
```

---

## Part 2: Reference TikToks & Style Transfer (Kling API)

### The Key Insight

Instead of describing "energetic, fast-paced, Gen-Z vibe" in text (which AI interprets poorly), you **show** it:

1. Download a TikTok that has the exact energy/pacing you want
2. Upload it to Kling as a "motion reference"
3. Kling extracts the motion DNA (gestures, timing, camera movement)
4. Your generated video inherits that authentic feel

### How Reference Videos Work

**What Kling Extracts:**
- Body movements and gestures
- Pacing and timing of actions
- Camera movement patterns
- Overall energy/rhythm

**What You Provide:**
- `image_url`: Your product image OR a character/avatar image
- `video_url`: The reference TikTok (motion source)
- `prompt`: Context about the scene (lighting, environment)

**Two Modes:**

| Mode | Use Case | Max Duration |
|------|----------|--------------|
| `image` | Keep character pose, adopt motion timing | 10 seconds |
| `video` | Full motion transfer (dance, complex movement) | 30 seconds |

### Reference Video Requirements

```
Format: MP4, MOV, WEBM (max 100MB)
Duration: 3-30 seconds
Content requirements:
  - Single person clearly visible
  - Head, shoulders, torso visible
  - Simple/static background preferred
  - No jump cuts or rapid scene changes
  - High contrast between person and background
```

### API Request for Style Transfer

```python
# Motion Control Request
request = {
    "model": "klingai/video-v2-6-pro-motion-control",
    "image_url": "https://your-cdn.com/product_photo.jpg",
    "video_url": "https://your-cdn.com/reference_tiktok.mp4",
    "character_orientation": "image",  # or "video" for full motion
    "prompt": "Professional studio lighting, clean white background, 4K quality",
    "keep_audio": False,  # We'll add our own audio
}
```

### Reference Library Structure

```
references/
├── high_energy/
│   ├── fast_cuts_dance.mp4      # Quick movements, high energy
│   ├── excited_reveal.mp4        # Enthusiasm, product reveal
│   └── trending_transition.mp4   # Popular transition effects
├── testimonial/
│   ├── calm_talking.mp4          # Relaxed, conversational
│   ├── before_after.mp4          # Comparison reveal
│   └── sincere_recommendation.mp4
├── demo/
│   ├── product_application.mp4   # Applying/using product
│   ├── unboxing.mp4              # Opening package
│   └── close_up_demo.mp4         # Detailed product view
└── problem_agitation/
    ├── frustrated_start.mp4      # Starting with pain point
    ├── dramatic_reveal.mp4       # Solution reveal
    └── transformation.mp4        # Before/after transformation
```

---

## Part 3: Video Generation

### Two Types of Videos

**Type A: Avatar Videos (Talking Head)**
- Person speaking to camera
- Uses HeyGen API
- Best for: hooks, testimonials, CTAs

**Type B: Product Videos (B-Roll)**
- Product in motion, demos, close-ups
- Uses Kling API
- Best for: body sections, demonstrations

### Avatar Video Generation (HeyGen)

**Step 1: List Available Avatars**
```python
GET https://api.heygen.com/v2/avatars

Response includes:
- avatar_id: "Angela-inblackskirt-20220820"
- avatar_name: "Angela"
- gender: "female"
- preview_image_url: "https://..."
- tags: ["UGC", "GEN_Z"]  # Filter for UGC-style avatars
```

**Step 2: Generate Video**
```python
POST https://api.heygen.com/v2/video_avatar

{
    "avatar_id": "Angela-inblackskirt-20220820",
    "voice_id": "en-US-JennyNeural",
    "text": "POV: You finally found a vitamin C serum that actually works",
    "video_title": "hook_1_avatar",
    "dimension": {"width": 1080, "height": 1920},  # 9:16 vertical
    "voice_speed": 1.1,  # Slightly faster for TikTok energy
    "caption": True
}

Response:
{
    "video_id": "abc123",
    "status": "pending"
}
```

**Step 3: Poll for Completion**
```python
GET https://api.heygen.com/v1/video_status.get?video_id=abc123

# Poll every 5-10 seconds until:
{
    "status": "completed",
    "video_url": "https://...",
    "duration": 3
}
```

### Product Video Generation (Kling)

**For B-Roll (Product in Motion):**
```python
# Image-to-Video: Animate a product photo
POST https://api.klingai.com/v1/videos/image2video

{
    "model": "kling-v1",
    "image": "https://your-cdn.com/serum_bottle.jpg",
    "prompt": "Serum bottle rotating slowly, studio lighting, product photography style, droplets of serum visible, clean white background",
    "duration": 5,
    "aspect_ratio": "9:16"
}
```

**For Demo (Using Motion Reference):**
```python
# Motion Control: Transfer reference video motion to product scene
POST https://api.klingai.com/v1/videos/motion-control

{
    "model": "kling-v2.6-pro",
    "image_url": "https://your-cdn.com/hand_holding_serum.jpg",
    "video_url": "https://your-cdn.com/reference_application.mp4",
    "character_orientation": "video",
    "prompt": "Hand applying serum to face, natural lighting, skincare routine, clean bathroom setting"
}
```

### Implementation

```python
class VideoGenerator:
    def __init__(self, kling_key: str, heygen_key: str):
        self.kling = KlingClient(kling_key)
        self.heygen = HeyGenClient(heygen_key)

    async def generate_avatar_clip(self, script: str, avatar_id: str) -> str:
        """Generate talking head video with HeyGen."""
        video_id = await self.heygen.create_video(
            avatar_id=avatar_id,
            text=script,
            dimension={"width": 1080, "height": 1920}
        )

        # Poll until complete
        while True:
            status = await self.heygen.get_status(video_id)
            if status["status"] == "completed":
                return status["video_url"]
            await asyncio.sleep(5)

    async def generate_product_clip(
        self,
        product_image: str,
        reference_video: str = None,
        prompt: str = ""
    ) -> str:
        """Generate product B-roll with Kling."""

        if reference_video:
            # Use motion control for style transfer
            task_id = await self.kling.create_motion_control(
                image_url=product_image,
                video_url=reference_video,
                prompt=prompt
            )
        else:
            # Simple image-to-video
            task_id = await self.kling.create_image_to_video(
                image_url=product_image,
                prompt=prompt
            )

        # Poll until complete
        while True:
            result = await self.kling.get_task(task_id)
            if result["status"] == "completed":
                return result["video_url"]
            await asyncio.sleep(5)
```

---

## Part 4: Assembly & Variations (Shotstack)

### The Mix-and-Match Strategy

With 5 hooks × 5 bodies × 5 CTAs, you get 125 unique videos.
Assembly combines them:

```
Final Video = Hook Clip + Body Clip + CTA Clip + Background Music + Captions
```

### Shotstack Timeline Structure

```python
{
    "timeline": {
        "tracks": [
            {
                "clips": [
                    # Hook (0-3 seconds)
                    {
                        "asset": {"type": "video", "src": "hook_1.mp4"},
                        "start": 0,
                        "length": 3
                    },
                    # Body (3-18 seconds)
                    {
                        "asset": {"type": "video", "src": "body_1.mp4"},
                        "start": 3,
                        "length": 15
                    },
                    # CTA (18-21 seconds)
                    {
                        "asset": {"type": "video", "src": "cta_1.mp4"},
                        "start": 18,
                        "length": 3
                    }
                ]
            },
            # Audio track
            {
                "clips": [
                    {
                        "asset": {"type": "audio", "src": "trending_sound.mp3"},
                        "start": 0,
                        "length": 21,
                        "volume": 0.3  # Background level
                    }
                ]
            }
        ]
    },
    "output": {
        "format": "mp4",
        "resolution": "hd",
        "aspectRatio": "9:16"
    }
}
```

### Generating All Variations

```python
class VideoAssembler:
    def __init__(self, shotstack_key: str):
        self.client = ShotstackClient(shotstack_key)

    async def assemble_all_variations(
        self,
        hooks: list[str],      # 5 video URLs
        bodies: list[str],     # 5 video URLs
        ctas: list[str],       # 5 video URLs
        background_music: str
    ) -> list[str]:
        """Generate all hook×body×cta combinations."""

        tasks = []
        for h_idx, hook in enumerate(hooks):
            for b_idx, body in enumerate(bodies):
                for c_idx, cta in enumerate(ctas):
                    task = self.assemble_single(
                        hook=hook,
                        body=body,
                        cta=cta,
                        music=background_music,
                        name=f"ad_{h_idx}_{b_idx}_{c_idx}"
                    )
                    tasks.append(task)

        # Run in parallel batches
        results = await asyncio.gather(*tasks)
        return results
```

---

## Part 5: Complete Pipeline Flow

### End-to-End Example

```python
async def generate_campaign(product_info: dict, reference_videos: dict):
    """
    Complete pipeline from product info to 125 video variations.

    Args:
        product_info: Product details, audience, tone
        reference_videos: {
            "hook_style": "references/high_energy/excited_reveal.mp4",
            "body_style": "references/testimonial/sincere_recommendation.mp4",
            "cta_style": "references/high_energy/fast_cuts_dance.mp4"
        }
    """

    # STEP 1: Generate Scripts
    print("Generating scripts...")
    script_gen = ScriptGenerator(ANTHROPIC_KEY)
    scripts = script_gen.generate(product_info)
    # Output: 5 hooks, 5 bodies, 5 CTAs (text)

    # STEP 2: Generate Avatar Videos for Each Script
    print("Generating avatar videos...")
    video_gen = VideoGenerator(KLING_KEY, HEYGEN_KEY)

    hook_videos = []
    for hook in scripts["hooks"]:
        # Avatar speaking the hook, with reference style
        url = await video_gen.generate_avatar_clip(
            script=hook["text"],
            avatar_id="ugc_female_25"
        )
        hook_videos.append(url)

    body_videos = []
    for body in scripts["bodies"]:
        if body["framework"] == "demonstration":
            # Product B-roll with motion reference
            url = await video_gen.generate_product_clip(
                product_image=product_info["product_image"],
                reference_video=reference_videos["body_style"],
                prompt="Product demonstration, natural lighting"
            )
        else:
            # Avatar testimonial
            url = await video_gen.generate_avatar_clip(
                script=body["text"],
                avatar_id="ugc_female_25"
            )
        body_videos.append(url)

    cta_videos = []
    for cta in scripts["ctas"]:
        url = await video_gen.generate_avatar_clip(
            script=cta["text"],
            avatar_id="ugc_female_25"
        )
        cta_videos.append(url)

    # STEP 3: Assemble All Variations
    print("Assembling 125 variations...")
    assembler = VideoAssembler(SHOTSTACK_KEY)
    final_videos = await assembler.assemble_all_variations(
        hooks=hook_videos,
        bodies=body_videos,
        ctas=cta_videos,
        background_music="trending_sound.mp3"
    )

    # STEP 4: Export for Each Platform
    print("Exporting for platforms...")
    exports = {
        "tiktok": final_videos,  # Already 9:16
        "reels": final_videos,   # Same 9:16
        "youtube_shorts": final_videos  # Same 9:16
    }

    return exports
```

---

## Project Structure

```
ugc_pipeline/
├── __init__.py
├── config.py              # API keys, settings
├── models.py              # Data classes (ProductInfo, Script, etc.)
│
├── generators/
│   ├── __init__.py
│   ├── script_generator.py    # Claude API for scripts
│   └── prompts/
│       ├── aida.txt           # AIDA framework prompt
│       ├── pas.txt            # PAS framework prompt
│       └── ugc_hooks.txt      # Hook patterns
│
├── clients/
│   ├── __init__.py
│   ├── kling_client.py        # Kling API wrapper
│   ├── heygen_client.py       # HeyGen API wrapper
│   └── shotstack_client.py    # Shotstack API wrapper
│
├── pipeline/
│   ├── __init__.py
│   ├── orchestrator.py        # Main pipeline class
│   └── job_queue.py           # Async job management
│
├── references/                 # Your reference TikToks
│   ├── high_energy/
│   ├── testimonial/
│   └── demo/
│
└── cli.py                     # Command-line interface
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `config.py` | Load API keys from .env, define settings |
| `models.py` | Pydantic models for ProductInfo, Script, VideoClip |
| `script_generator.py` | Claude integration for script generation |
| `kling_client.py` | Async Kling API client with retry logic |
| `heygen_client.py` | Async HeyGen API client with polling |
| `shotstack_client.py` | Video assembly and export |
| `orchestrator.py` | Main pipeline that ties everything together |
| `cli.py` | CLI for running campaigns |

---

## Verification Plan

1. **Script Generation Test**
   - Run with sample product info
   - Verify output has 5 hooks, 5 bodies, 5 CTAs
   - Check scripts sound natural, not corporate

2. **HeyGen Integration Test**
   - Generate single avatar video
   - Verify polling works, video downloads successfully

3. **Kling Integration Test**
   - Generate image-to-video (no reference)
   - Generate motion-control video (with reference)
   - Verify style transfer is visible

4. **Assembly Test**
   - Combine 3 clips into one video
   - Verify transitions, audio mixing

5. **Full Pipeline Test**
   - Run complete campaign with 1 hook × 1 body × 1 CTA
   - Verify end-to-end flow before scaling to 125

---

## API Keys Needed

```env
ANTHROPIC_API_KEY=sk-ant-...      # For Claude script generation
KLING_API_KEY=...                  # For video generation
HEYGEN_API_KEY=...                 # For avatar generation
SHOTSTACK_API_KEY=...              # For video assembly
```

---

## Cost Estimate (per campaign)

| Component | Cost |
|-----------|------|
| Claude (scripts) | ~$0.50 |
| HeyGen (15 avatar clips × 10 sec avg) | ~$5-10 |
| Kling (5 product clips × 5 sec) | ~$2-5 |
| Shotstack (125 renders) | ~$10-20 |
| **Total per campaign** | **~$20-40** |

For 10-50 videos/month: **$200-2000/month** (scales with volume)
