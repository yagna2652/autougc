# UGC Ad Generation Pipeline - Product Requirements Document

## 1. Executive Summary

**Product**: Automated UGC-style video ad generation pipeline
**Goal**: Generate 125 video variations per campaign from a single product brief
**Output**: TikTok/Reels/Shorts-ready ads (9:16 vertical, 15-30 seconds)

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INPUT                                      │
│  ┌──────────────┐    ┌──────────────────┐    ┌────────────────────┐        │
│  │ Product Info │    │ Target Audience  │    │ Reference TikToks  │        │
│  │ (JSON)       │    │ (JSON)           │    │ (MP4 files)        │        │
│  └──────┬───────┘    └────────┬─────────┘    └──────────┬─────────┘        │
└─────────┼──────────────────────┼─────────────────────────┼──────────────────┘
          │                      │                         │
          ▼                      ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SCRIPT GENERATION (Claude API)                       │
│                                                                              │
│  Input: product_info + target_audience                                       │
│  Output: 5 hooks + 5 bodies + 5 CTAs (JSON)                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VIDEO GENERATION (Parallel)                          │
│                                                                              │
│  ┌─────────────────────────┐         ┌─────────────────────────┐           │
│  │   HeyGen API            │         │   Kling API             │           │
│  │   (Avatar/Talking Head) │         │   (Product B-Roll)      │           │
│  │                         │         │                         │           │
│  │   - Hooks (5 clips)     │         │   - Demo clips          │           │
│  │   - Body testimonials   │         │   - Product animations  │           │
│  │   - CTAs (5 clips)      │         │   - Motion-controlled   │           │
│  └───────────┬─────────────┘         └───────────┬─────────────┘           │
│              │                                   │                          │
│              └───────────────┬───────────────────┘                          │
│                              ▼                                              │
│                    15 video clips total                                     │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ASSEMBLY (Shotstack API)                             │
│                                                                              │
│  For each combination (5 hooks × 5 bodies × 5 CTAs = 125):                  │
│    1. Concatenate: hook.mp4 + body.mp4 + cta.mp4                            │
│    2. Add background music track                                            │
│    3. Burn in captions (optional)                                           │
│    4. Export as MP4 (9:16, 1080x1920)                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT                                          │
│                                                                              │
│  /output/campaign_YYYYMMDD_HHMMSS/                                          │
│    ├── scripts.json           (generated scripts)                           │
│    ├── clips/                 (15 individual clips)                         │
│    │   ├── hook_0.mp4                                                       │
│    │   ├── hook_1.mp4                                                       │
│    │   ├── ...                                                              │
│    │   ├── body_0.mp4                                                       │
│    │   ├── ...                                                              │
│    │   └── cta_4.mp4                                                        │
│    └── final/                 (125 assembled videos)                        │
│        ├── ad_0_0_0.mp4       (hook_0 + body_0 + cta_0)                     │
│        ├── ad_0_0_1.mp4       (hook_0 + body_0 + cta_1)                     │
│        └── ...                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Input Specifications

### 3.1 Product Info (Required)

**File**: `product_info.json`

```json
{
  "name": "GlowSkin Vitamin C Serum",
  "category": "skincare",
  "price": "$29.99",
  "product_image_url": "https://your-cdn.com/product.jpg",
  "key_benefits": [
    "Brightens skin in 2 weeks",
    "Reduces dark spots",
    "Lightweight, non-greasy formula"
  ],
  "unique_selling_point": "3x more vitamin C than competitors",
  "social_proof": "50,000+ 5-star reviews",
  "competitor_weaknesses": "Most serums are either too weak or too irritating"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Product name |
| `category` | string | Yes | Product category (skincare, tech, fashion, etc.) |
| `price` | string | Yes | Display price |
| `product_image_url` | string | Yes | URL to product image for B-roll generation |
| `key_benefits` | string[] | Yes | 2-5 main benefits |
| `unique_selling_point` | string | Yes | What makes this different |
| `social_proof` | string | No | Reviews, ratings, celebrity mentions |
| `competitor_weaknesses` | string | No | What competitors do wrong |

### 3.2 Target Audience (Required)

**File**: `target_audience.json`

```json
{
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
  ],
  "tone": "friendly, relatable, Gen-Z casual",
  "language_style": {
    "use_slang": true,
    "use_emojis_in_captions": true,
    "formality": "casual"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `age_range` | string | Yes | Target age range |
| `gender` | string | No | Target gender (or "all") |
| `pain_points` | string[] | Yes | Problems they have (2-5) |
| `desires` | string[] | Yes | What they want (2-5) |
| `tone` | string | Yes | Voice/tone for scripts |
| `language_style.use_slang` | boolean | No | Include Gen-Z slang |
| `language_style.formality` | string | No | "casual", "neutral", "professional" |

### 3.3 Reference Videos (Optional but Recommended)

**Directory**: `references/`

```
references/
├── hooks/
│   └── energetic_reveal.mp4      # Reference for hook energy/pacing
├── bodies/
│   └── calm_testimonial.mp4      # Reference for body style
└── ctas/
    └── quick_cta.mp4             # Reference for CTA delivery
```

**Reference Video Requirements**:

| Requirement | Specification |
|-------------|---------------|
| Format | MP4, MOV, or WEBM |
| Max file size | 100 MB |
| Duration | 3-30 seconds |
| Resolution | Min 720p |
| Content | Single person visible, head/shoulders/torso in frame |
| Background | Simple, static preferred |
| Audio | Optional (will be replaced) |

---

## 4. Output Specifications

### 4.1 Generated Scripts

**File**: `output/campaign_*/scripts.json`

```json
{
  "generated_at": "2024-01-15T10:30:00Z",
  "product_name": "GlowSkin Vitamin C Serum",
  "hooks": [
    {
      "id": "hook_0",
      "text": "POV: You finally found a vitamin C serum that actually works",
      "duration_seconds": 3,
      "style": "pov_trend",
      "video_type": "avatar"
    },
    {
      "id": "hook_1",
      "text": "I was today years old when I learned why my skin looked so dull",
      "duration_seconds": 3,
      "style": "revelation",
      "video_type": "avatar"
    },
    {
      "id": "hook_2",
      "text": "Stop scrolling if you have dark spots",
      "duration_seconds": 2,
      "style": "direct_address",
      "video_type": "avatar"
    },
    {
      "id": "hook_3",
      "text": "Nobody talks about this but most vitamin C serums are basically useless",
      "duration_seconds": 4,
      "style": "controversial",
      "video_type": "avatar"
    },
    {
      "id": "hook_4",
      "text": "The difference after 2 weeks is insane",
      "duration_seconds": 3,
      "style": "result_tease",
      "video_type": "avatar"
    }
  ],
  "bodies": [
    {
      "id": "body_0",
      "text": "I've been using this for two weeks and look at the difference. My dark spots are fading, my skin is actually glowing, and it doesn't feel greasy at all.",
      "duration_seconds": 12,
      "framework": "testimonial",
      "video_type": "avatar"
    },
    {
      "id": "body_1",
      "text": "Here's the thing about vitamin C serums - most of them don't have enough vitamin C to actually do anything. This one has 3x more than the leading brands.",
      "duration_seconds": 10,
      "framework": "education",
      "video_type": "avatar"
    },
    {
      "id": "body_2",
      "text": "I used to wake up and my skin just looked tired and dull no matter what I did. I tried everything. Then I found this and honestly I wish I found it sooner.",
      "duration_seconds": 12,
      "framework": "problem_agitation",
      "video_type": "avatar"
    },
    {
      "id": "body_3",
      "text": "Watch how it absorbs - see that? No greasy residue. Just a few drops every morning and you're done.",
      "duration_seconds": 8,
      "framework": "demonstration",
      "video_type": "product_broll"
    },
    {
      "id": "body_4",
      "text": "Over 50,000 five-star reviews and I totally get why. This is the one skincare product I'll never stop using.",
      "duration_seconds": 8,
      "framework": "social_proof",
      "video_type": "avatar"
    }
  ],
  "ctas": [
    {
      "id": "cta_0",
      "text": "Link in bio - they're running 20% off right now",
      "duration_seconds": 3,
      "urgency": "discount",
      "video_type": "avatar"
    },
    {
      "id": "cta_1",
      "text": "Trust me, your skin will thank you. Link below.",
      "duration_seconds": 3,
      "urgency": "soft",
      "video_type": "avatar"
    },
    {
      "id": "cta_2",
      "text": "They sold out twice last month so grab it while you can",
      "duration_seconds": 3,
      "urgency": "scarcity",
      "video_type": "avatar"
    },
    {
      "id": "cta_3",
      "text": "Comment 'GLOW' and I'll send you the link",
      "duration_seconds": 3,
      "urgency": "engagement",
      "video_type": "avatar"
    },
    {
      "id": "cta_4",
      "text": "Tap the link before I change my mind about sharing this",
      "duration_seconds": 3,
      "urgency": "exclusive",
      "video_type": "avatar"
    }
  ]
}
```

### 4.2 Video Clips

**Directory**: `output/campaign_*/clips/`

| Filename Pattern | Count | Duration | Source |
|------------------|-------|----------|--------|
| `hook_0.mp4` - `hook_4.mp4` | 5 | 2-4 sec each | HeyGen |
| `body_0.mp4` - `body_4.mp4` | 5 | 8-15 sec each | HeyGen or Kling |
| `cta_0.mp4` - `cta_4.mp4` | 5 | 3 sec each | HeyGen |

**Video Specifications**:

| Property | Value |
|----------|-------|
| Resolution | 1080 × 1920 (9:16) |
| Frame rate | 30 fps |
| Codec | H.264 |
| Audio | AAC, 44.1kHz |

### 4.3 Final Assembled Videos

**Directory**: `output/campaign_*/final/`

**Naming Convention**: `ad_{hook_index}_{body_index}_{cta_index}.mp4`

| Example | Components |
|---------|------------|
| `ad_0_0_0.mp4` | hook_0 + body_0 + cta_0 |
| `ad_0_0_1.mp4` | hook_0 + body_0 + cta_1 |
| `ad_2_3_1.mp4` | hook_2 + body_3 + cta_1 |
| `ad_4_4_4.mp4` | hook_4 + body_4 + cta_4 |

**Total**: 5 × 5 × 5 = **125 videos**

---

## 5. API Specifications

### 5.1 Claude API (Script Generation)

**Endpoint**: `https://api.anthropic.com/v1/messages`

**Request**:
```http
POST /v1/messages
Authorization: Bearer {ANTHROPIC_API_KEY}
Content-Type: application/json

{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 4096,
  "messages": [
    {
      "role": "user",
      "content": "{SCRIPT_GENERATION_PROMPT}"
    }
  ]
}
```

**Full Prompt Template**:
```
You are a UGC ad copywriter who creates viral TikTok/Reels scripts.

## Product Information
{product_info_json}

## Target Audience
{target_audience_json}

## Your Task
Generate modular script components that can be mixed and matched.
Return ONLY valid JSON with no markdown formatting.

### HOOKS (exactly 5)
Requirements:
- Duration: 2-4 seconds when spoken
- Purpose: Stop the scroll immediately
- Each must use a DIFFERENT pattern from this list:
  1. POV: ... (relatable situation)
  2. "I was today years old when..."
  3. "Nobody talks about this but..."
  4. Direct question or "Stop scrolling if..."
  5. Controversial/surprising statement or result tease

### BODIES (exactly 5)
Requirements:
- Duration: 8-15 seconds when spoken
- Each must use a DIFFERENT framework:
  1. TESTIMONIAL: Personal experience + visible results
  2. EDUCATION: "Here's the thing..." or "Most people don't know..."
  3. PROBLEM-AGITATION: Start with pain point, emotional connection
  4. DEMONSTRATION: Describe showing the product (this will be B-roll)
  5. SOCIAL PROOF: Reviews, numbers, celebrity mentions

### CTAs (exactly 5)
Requirements:
- Duration: 2-4 seconds when spoken
- Each must use a DIFFERENT urgency type:
  1. DISCOUNT: Mention a sale/deal
  2. SOFT: Gentle recommendation
  3. SCARCITY: Limited stock/time
  4. ENGAGEMENT: Ask for comment/follow
  5. EXCLUSIVE: Make viewer feel special

## Output Format
{
  "hooks": [
    {"id": "hook_0", "text": "...", "duration_seconds": N, "style": "...", "video_type": "avatar"},
    ...
  ],
  "bodies": [
    {"id": "body_0", "text": "...", "duration_seconds": N, "framework": "...", "video_type": "avatar|product_broll"},
    ...
  ],
  "ctas": [
    {"id": "cta_0", "text": "...", "duration_seconds": N, "urgency": "...", "video_type": "avatar"},
    ...
  ]
}

## Tone Guidelines
{tone_description}

## Critical Rules
- Write like a real person talking to camera, NOT an ad
- Use contractions (I've, don't, it's)
- Include filler words occasionally (like, honestly, literally)
- Never use corporate language
- Never say "introducing" or "revolutionary"
- The DEMONSTRATION body should describe actions, not be a voiceover
```

**Response Parsing**:
```python
response = client.messages.create(...)
content = response.content[0].text

# Handle potential markdown wrapping
if content.startswith("```"):
    content = content.split("```")[1]
    if content.startswith("json"):
        content = content[4:]

scripts = json.loads(content)
```

---

### 5.2 HeyGen API (Avatar Videos)

**Base URL**: `https://api.heygen.com`

#### 5.2.1 List Avatars

```http
GET /v2/avatars
X-API-KEY: {HEYGEN_API_KEY}
```

**Response**:
```json
{
  "avatars": [
    {
      "avatar_id": "Angela-inblackskirt-20220820",
      "avatar_name": "Angela",
      "gender": "female",
      "preview_image_url": "https://...",
      "preview_video_url": "https://...",
      "tags": ["UGC", "CASUAL"]
    }
  ]
}
```

**Avatar Selection Logic**:
```python
def select_avatar(avatars: list, target_audience: dict) -> str:
    """Select best avatar based on target audience."""

    preferred_tags = ["UGC", "CASUAL", "GEN_Z"]
    gender = target_audience.get("gender", "female")

    candidates = [
        a for a in avatars
        if a["gender"] == gender
        and any(tag in a.get("tags", []) for tag in preferred_tags)
    ]

    if candidates:
        return candidates[0]["avatar_id"]

    # Fallback to first avatar matching gender
    return next(a["avatar_id"] for a in avatars if a["gender"] == gender)
```

#### 5.2.2 Generate Video

```http
POST /v2/video_avatar
X-API-KEY: {HEYGEN_API_KEY}
Content-Type: application/json

{
  "avatar_id": "Angela-inblackskirt-20220820",
  "voice_id": "en-US-JennyNeural",
  "text": "POV: You finally found a vitamin C serum that actually works",
  "video_title": "hook_0",
  "dimension": {
    "width": 1080,
    "height": 1920
  },
  "voice_speed": 1.05,
  "caption": false
}
```

**Response**:
```json
{
  "video_id": "abc123def456",
  "status": "pending"
}
```

#### 5.2.3 Poll Status

```http
GET /v1/video_status.get?video_id=abc123def456
X-API-KEY: {HEYGEN_API_KEY}
```

**Response States**:

| Status | Action |
|--------|--------|
| `pending` | Continue polling (5 sec interval) |
| `processing` | Continue polling (5 sec interval) |
| `completed` | Download from `video_url` |
| `failed` | Log error, retry or skip |

**Completed Response**:
```json
{
  "video_id": "abc123def456",
  "status": "completed",
  "video_url": "https://resource.heygen.ai/video/abc123.mp4",
  "duration": 3.2
}
```

**Polling Logic**:
```python
async def wait_for_heygen_video(video_id: str, timeout: int = 300) -> str:
    """Poll until video is ready or timeout."""

    start = time.time()

    while time.time() - start < timeout:
        response = await heygen_client.get_status(video_id)

        if response["status"] == "completed":
            return response["video_url"]

        if response["status"] == "failed":
            raise VideoGenerationError(f"HeyGen failed: {response.get('error')}")

        await asyncio.sleep(5)

    raise TimeoutError(f"HeyGen video {video_id} timed out after {timeout}s")
```

---

### 5.3 Kling API (Product B-Roll)

**Base URL**: Varies by provider (see options below)

**Provider Options**:

| Provider | Base URL | Notes |
|----------|----------|-------|
| AI/ML API | `https://api.aimlapi.com/v2` | Recommended |
| PiAPI | `https://api.piapi.ai/api/v1` | Alternative |
| Fal.ai | `https://fal.run/fal-ai/kling` | Alternative |

#### 5.3.1 Image-to-Video (Simple B-Roll)

```http
POST /video/generations
Authorization: Bearer {KLING_API_KEY}
Content-Type: application/json

{
  "model": "kling-v1",
  "image_url": "https://your-cdn.com/product.jpg",
  "prompt": "Product bottle rotating slowly, professional studio lighting, white background, droplets visible on bottle, high-end product photography style",
  "negative_prompt": "blurry, low quality, distorted, hands, people",
  "duration": 5,
  "aspect_ratio": "9:16"
}
```

#### 5.3.2 Motion Control (Style Transfer)

```http
POST /video/generations
Authorization: Bearer {KLING_API_KEY}
Content-Type: application/json

{
  "model": "klingai/video-v2-6-pro-motion-control",
  "image_url": "https://your-cdn.com/hand_holding_product.jpg",
  "video_url": "https://your-cdn.com/reference_application.mp4",
  "character_orientation": "video",
  "prompt": "Hand applying skincare product to face, natural bathroom lighting, skincare routine",
  "keep_audio": false
}
```

**Response**:
```json
{
  "generation_id": "gen_abc123",
  "status": "processing"
}
```

#### 5.3.3 Poll Status

```http
GET /video/generations?generation_id=gen_abc123
Authorization: Bearer {KLING_API_KEY}
```

**Completed Response**:
```json
{
  "generation_id": "gen_abc123",
  "status": "completed",
  "video_url": "https://cdn.kling.ai/output/gen_abc123.mp4",
  "duration": 5.0
}
```

---

### 5.4 Shotstack API (Video Assembly)

**Base URL**: `https://api.shotstack.io/v1`

#### 5.4.1 Render Video

```http
POST /render
x-api-key: {SHOTSTACK_API_KEY}
Content-Type: application/json

{
  "timeline": {
    "tracks": [
      {
        "clips": [
          {
            "asset": {
              "type": "video",
              "src": "https://storage.example.com/clips/hook_0.mp4"
            },
            "start": 0,
            "length": 3
          },
          {
            "asset": {
              "type": "video",
              "src": "https://storage.example.com/clips/body_0.mp4"
            },
            "start": 3,
            "length": 12
          },
          {
            "asset": {
              "type": "video",
              "src": "https://storage.example.com/clips/cta_0.mp4"
            },
            "start": 15,
            "length": 3
          }
        ]
      },
      {
        "clips": [
          {
            "asset": {
              "type": "audio",
              "src": "https://storage.example.com/music/trending_sound.mp3",
              "volume": 0.2
            },
            "start": 0,
            "length": 18
          }
        ]
      }
    ]
  },
  "output": {
    "format": "mp4",
    "resolution": "hd",
    "aspectRatio": "9:16",
    "fps": 30
  }
}
```

**Response**:
```json
{
  "success": true,
  "message": "Created",
  "response": {
    "id": "render_abc123",
    "status": "queued"
  }
}
```

#### 5.4.2 Poll Render Status

```http
GET /render/render_abc123
x-api-key: {SHOTSTACK_API_KEY}
```

**Completed Response**:
```json
{
  "success": true,
  "response": {
    "id": "render_abc123",
    "status": "done",
    "url": "https://cdn.shotstack.io/output/render_abc123.mp4"
  }
}
```

---

## 6. Implementation Details

### 6.1 Project Structure

```
ugc_pipeline/
├── __init__.py
├── config.py                 # Configuration and environment variables
├── models.py                 # Pydantic data models
├── main.py                   # CLI entry point
│
├── clients/
│   ├── __init__.py
│   ├── base.py              # Base async HTTP client
│   ├── claude_client.py     # Anthropic Claude API
│   ├── heygen_client.py     # HeyGen avatar API
│   ├── kling_client.py      # Kling video API
│   └── shotstack_client.py  # Shotstack assembly API
│
├── generators/
│   ├── __init__.py
│   ├── script_generator.py  # Script generation logic
│   └── prompts/
│       └── ugc_script.txt   # Prompt template
│
├── pipeline/
│   ├── __init__.py
│   ├── orchestrator.py      # Main pipeline orchestration
│   └── video_generator.py   # Video generation coordination
│
└── utils/
    ├── __init__.py
    ├── storage.py           # File upload/download
    └── logging.py           # Structured logging
```

### 6.2 Data Models

```python
# models.py

from pydantic import BaseModel, Field
from typing import Literal
from enum import Enum

class VideoType(str, Enum):
    AVATAR = "avatar"
    PRODUCT_BROLL = "product_broll"

class HookStyle(str, Enum):
    POV_TREND = "pov_trend"
    REVELATION = "revelation"
    DIRECT_ADDRESS = "direct_address"
    CONTROVERSIAL = "controversial"
    RESULT_TEASE = "result_tease"

class BodyFramework(str, Enum):
    TESTIMONIAL = "testimonial"
    EDUCATION = "education"
    PROBLEM_AGITATION = "problem_agitation"
    DEMONSTRATION = "demonstration"
    SOCIAL_PROOF = "social_proof"

class CtaUrgency(str, Enum):
    DISCOUNT = "discount"
    SOFT = "soft"
    SCARCITY = "scarcity"
    ENGAGEMENT = "engagement"
    EXCLUSIVE = "exclusive"

class Hook(BaseModel):
    id: str
    text: str
    duration_seconds: int = Field(ge=2, le=5)
    style: HookStyle
    video_type: VideoType = VideoType.AVATAR

class Body(BaseModel):
    id: str
    text: str
    duration_seconds: int = Field(ge=8, le=15)
    framework: BodyFramework
    video_type: VideoType

class Cta(BaseModel):
    id: str
    text: str
    duration_seconds: int = Field(ge=2, le=4)
    urgency: CtaUrgency
    video_type: VideoType = VideoType.AVATAR

class GeneratedScripts(BaseModel):
    hooks: list[Hook] = Field(min_length=5, max_length=5)
    bodies: list[Body] = Field(min_length=5, max_length=5)
    ctas: list[Cta] = Field(min_length=5, max_length=5)

class ProductInfo(BaseModel):
    name: str
    category: str
    price: str
    product_image_url: str
    key_benefits: list[str] = Field(min_length=2, max_length=5)
    unique_selling_point: str
    social_proof: str | None = None
    competitor_weaknesses: str | None = None

class TargetAudience(BaseModel):
    age_range: str
    gender: Literal["male", "female", "all"] = "all"
    pain_points: list[str] = Field(min_length=2, max_length=5)
    desires: list[str] = Field(min_length=2, max_length=5)
    tone: str
    language_style: dict | None = None

class CampaignConfig(BaseModel):
    product: ProductInfo
    audience: TargetAudience
    reference_videos: dict[str, str] | None = None  # Optional paths
    avatar_id: str | None = None  # If None, auto-select
    background_music_url: str | None = None
```

### 6.3 Pipeline Orchestrator

```python
# pipeline/orchestrator.py

import asyncio
from pathlib import Path
from datetime import datetime

class UGCPipeline:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.claude = ClaudeClient(config.claude_api_key)
        self.heygen = HeyGenClient(config.heygen_api_key)
        self.kling = KlingClient(config.kling_api_key)
        self.shotstack = ShotstackClient(config.shotstack_api_key)

    async def run(self, campaign: CampaignConfig) -> CampaignResult:
        """Execute full pipeline."""

        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"output/campaign_{timestamp}")
        output_dir.mkdir(parents=True)
        (output_dir / "clips").mkdir()
        (output_dir / "final").mkdir()

        # Step 1: Generate scripts
        scripts = await self._generate_scripts(campaign)
        self._save_scripts(scripts, output_dir / "scripts.json")

        # Step 2: Generate video clips (parallel)
        clips = await self._generate_clips(scripts, campaign)

        # Step 3: Upload clips to cloud storage (for Shotstack)
        clip_urls = await self._upload_clips(clips)

        # Step 4: Assemble all variations (parallel batches)
        final_videos = await self._assemble_variations(clip_urls, campaign)

        return CampaignResult(
            output_dir=output_dir,
            scripts=scripts,
            clip_count=len(clips),
            video_count=len(final_videos)
        )

    async def _generate_scripts(self, campaign: CampaignConfig) -> GeneratedScripts:
        """Generate scripts using Claude."""

        prompt = self._build_prompt(campaign.product, campaign.audience)
        response = await self.claude.generate(prompt)

        # Parse and validate
        scripts = GeneratedScripts.model_validate_json(response)
        return scripts

    async def _generate_clips(
        self,
        scripts: GeneratedScripts,
        campaign: CampaignConfig
    ) -> dict[str, Path]:
        """Generate all video clips in parallel."""

        tasks = []

        # Hooks (all avatar)
        for hook in scripts.hooks:
            tasks.append(self._generate_avatar_clip(hook.id, hook.text, campaign))

        # Bodies (avatar or B-roll)
        for body in scripts.bodies:
            if body.video_type == VideoType.PRODUCT_BROLL:
                tasks.append(self._generate_broll_clip(body.id, body.text, campaign))
            else:
                tasks.append(self._generate_avatar_clip(body.id, body.text, campaign))

        # CTAs (all avatar)
        for cta in scripts.ctas:
            tasks.append(self._generate_avatar_clip(cta.id, cta.text, campaign))

        # Run all in parallel (with semaphore to limit concurrency)
        results = await asyncio.gather(*tasks)

        return {r["id"]: r["path"] for r in results}

    async def _generate_avatar_clip(
        self,
        clip_id: str,
        text: str,
        campaign: CampaignConfig
    ) -> dict:
        """Generate single avatar clip."""

        video_id = await self.heygen.create_video(
            avatar_id=campaign.avatar_id or await self._select_avatar(campaign),
            text=text,
            title=clip_id
        )

        video_url = await self.heygen.wait_for_completion(video_id)
        local_path = await self._download_video(video_url, f"clips/{clip_id}.mp4")

        return {"id": clip_id, "path": local_path}

    async def _generate_broll_clip(
        self,
        clip_id: str,
        description: str,
        campaign: CampaignConfig
    ) -> dict:
        """Generate product B-roll clip."""

        reference_video = campaign.reference_videos.get("body") if campaign.reference_videos else None

        if reference_video:
            # Use motion control
            task_id = await self.kling.create_motion_control(
                image_url=campaign.product.product_image_url,
                video_url=reference_video,
                prompt=f"Product demonstration: {description}"
            )
        else:
            # Simple image-to-video
            task_id = await self.kling.create_image_to_video(
                image_url=campaign.product.product_image_url,
                prompt=f"Product video: {description}, professional lighting, clean background"
            )

        video_url = await self.kling.wait_for_completion(task_id)
        local_path = await self._download_video(video_url, f"clips/{clip_id}.mp4")

        return {"id": clip_id, "path": local_path}

    async def _assemble_variations(
        self,
        clip_urls: dict[str, str],
        campaign: CampaignConfig
    ) -> list[str]:
        """Assemble all 125 variations."""

        tasks = []

        for h in range(5):
            for b in range(5):
                for c in range(5):
                    tasks.append(
                        self._assemble_single(
                            hook_url=clip_urls[f"hook_{h}"],
                            body_url=clip_urls[f"body_{b}"],
                            cta_url=clip_urls[f"cta_{c}"],
                            music_url=campaign.background_music_url,
                            output_name=f"ad_{h}_{b}_{c}"
                        )
                    )

        # Process in batches of 10 to avoid rate limits
        results = []
        for i in range(0, len(tasks), 10):
            batch = tasks[i:i+10]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)
            await asyncio.sleep(1)  # Rate limit buffer

        return results
```

---

## 7. Error Handling

### 7.1 Error Types

| Error | Cause | Recovery |
|-------|-------|----------|
| `ScriptGenerationError` | Claude returns invalid JSON | Retry up to 3 times with stricter prompt |
| `AvatarNotFoundError` | No matching avatar for criteria | Fall back to default avatar |
| `VideoGenerationTimeout` | HeyGen/Kling taking too long | Retry once, then skip clip |
| `VideoGenerationFailed` | API returned error | Log and skip, or retry |
| `AssemblyFailed` | Shotstack render failed | Retry once |
| `RateLimitError` | Too many API requests | Exponential backoff |

### 7.2 Retry Logic

```python
async def with_retry(
    func,
    max_attempts: int = 3,
    base_delay: float = 1.0
) -> Any:
    """Execute function with exponential backoff retry."""

    last_error = None

    for attempt in range(max_attempts):
        try:
            return await func()
        except RateLimitError:
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)
            last_error = e
        except (VideoGenerationFailed, AssemblyFailed) as e:
            if attempt < max_attempts - 1:
                await asyncio.sleep(base_delay)
            last_error = e

    raise last_error
```

---

## 8. Configuration

### 8.1 Environment Variables

```bash
# .env

# Required
ANTHROPIC_API_KEY=sk-ant-api03-...
HEYGEN_API_KEY=...
KLING_API_KEY=...
SHOTSTACK_API_KEY=...

# Optional
KLING_PROVIDER=aimlapi          # or "piapi", "fal"
DEFAULT_AVATAR_ID=Angela-inblackskirt-20220820
DEFAULT_VOICE_ID=en-US-JennyNeural
OUTPUT_DIR=./output
LOG_LEVEL=INFO
```

### 8.2 Config File

```yaml
# config.yaml

pipeline:
  num_hooks: 5
  num_bodies: 5
  num_ctas: 5
  max_concurrent_generations: 5
  generation_timeout_seconds: 300

heygen:
  voice_speed: 1.05
  enable_captions: false

kling:
  default_duration: 5
  quality: "pro"        # "standard" or "pro"

shotstack:
  environment: "stage"  # "stage" or "production"
  output_resolution: "hd"
  output_fps: 30
```

---

## 9. CLI Usage

```bash
# Install
pip install -e .

# Run full pipeline
ugc-pipeline run \
  --product product_info.json \
  --audience target_audience.json \
  --references ./references/ \
  --output ./output/

# Generate scripts only
ugc-pipeline scripts \
  --product product_info.json \
  --audience target_audience.json \
  --output scripts.json

# Generate clips from existing scripts
ugc-pipeline clips \
  --scripts scripts.json \
  --product product_info.json \
  --output ./clips/

# Assemble from existing clips
ugc-pipeline assemble \
  --clips ./clips/ \
  --music ./music/trending.mp3 \
  --output ./final/
```

---

## 10. Testing Plan

### 10.1 Unit Tests

| Test | Description |
|------|-------------|
| `test_script_generation_returns_valid_json` | Claude output parses correctly |
| `test_script_generation_has_required_counts` | Exactly 5 hooks, 5 bodies, 5 CTAs |
| `test_hook_styles_are_unique` | No duplicate styles |
| `test_body_frameworks_are_unique` | No duplicate frameworks |
| `test_cta_urgencies_are_unique` | No duplicate urgencies |

### 10.2 Integration Tests

| Test | Description |
|------|-------------|
| `test_heygen_generates_video` | Single avatar video succeeds |
| `test_kling_image_to_video` | Simple B-roll generation |
| `test_kling_motion_control` | Style transfer works |
| `test_shotstack_assembly` | 3 clips combine correctly |

### 10.3 End-to-End Test

```python
async def test_full_pipeline():
    """Run pipeline with minimal config (1×1×1 = 1 video)."""

    config = PipelineConfig(num_hooks=1, num_bodies=1, num_ctas=1)
    pipeline = UGCPipeline(config)

    result = await pipeline.run(sample_campaign)

    assert result.video_count == 1
    assert (result.output_dir / "final" / "ad_0_0_0.mp4").exists()
```

---

## 11. Cost Estimation

| Component | Unit Cost | Per Campaign (5×5×5) |
|-----------|-----------|---------------------|
| Claude API | ~$0.003/1K tokens | ~$0.50 |
| HeyGen | $0.10/minute | ~$5-10 (15 clips × 10s avg) |
| Kling | $0.07/second | ~$2-5 (5 clips × 5s) |
| Shotstack | $0.05/render | ~$6.25 (125 renders) |
| **Total** | | **~$15-25** |

---

## 12. Limitations & Constraints

1. **HeyGen avatar quality**: Pre-built avatars may look synthetic; custom avatars require separate training
2. **Kling motion control**: Works best with single-person reference videos; complex scenes may fail
3. **Script quality**: Claude may occasionally produce corporate-sounding copy; manual review recommended
4. **Rate limits**: HeyGen allows 3 concurrent jobs (Pro plan); pipeline batches accordingly
5. **Video URLs expire**: HeyGen URLs expire after 7 days; download immediately
6. **No real-time preview**: Full pipeline takes 15-30 minutes to complete
