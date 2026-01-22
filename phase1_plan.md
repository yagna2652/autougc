# Phase 1: TikTok Analyzer - Planning Document

## Overview

**Goal**: Build a system that takes a downloaded TikTok/Reel video and extracts a structured "blueprint" containing everything needed to recreate a similar video.

**Input**: A downloaded video file (MP4)

**Output**: A structured JSON "Video Blueprint"

---

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                     INPUT: Downloaded TikTok (MP4)              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 1: Audio Extraction                     │
│                                                                 │
│  Tool: ffmpeg                                                   │
│  Input: video.mp4                                               │
│  Output: audio.wav (16kHz, mono - optimized for transcription)  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 2: Transcription                        │
│                                                                 │
│  Tool: OpenAI Whisper (local or API)                            │
│  Input: audio.wav                                               │
│  Output:                                                        │
│    - Full transcript text                                       │
│    - Word/segment-level timestamps                              │
│    - Detected language                                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STEP 3: Visual Analysis                      │
│                                                                 │
│  Tool: Claude Vision API                                        │
│  Input: Key frames extracted from video (every 1-2 seconds)     │
│  Output:                                                        │
│    - Setting/environment description                            │
│    - Lighting analysis                                          │
│    - Camera framing                                             │
│    - Person/avatar description                                  │
│    - Background description                                     │
│    - Text overlays detected                                     │
│    - Visual effects/transitions                                 │
│    - Color palette                                              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 STEP 4: Structure Identification                │
│                                                                 │
│  Tool: Claude API (text analysis)                               │
│  Input: Transcript + Visual analysis + Video duration           │
│  Output:                                                        │
│    - Hook section (start, end, text, style)                     │
│    - Body section (start, end, text, framework)                 │
│    - CTA section (start, end, text, urgency)                    │
│    - Engagement analysis                                        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 OUTPUT: Video Blueprint (JSON)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Video Blueprint Schema

```json
{
  "source_video": "path/to/video.mp4",
  "duration_seconds": 28.5,
  "analysis_version": "1.0",

  "transcript": {
    "full_text": "POV: You finally found a vitamin C serum that actually works. I've been using this for two weeks and look at the difference...",
    "segments": [
      { "start": 0.0, "end": 2.8, "text": "POV: You finally found a vitamin C serum that actually works." },
      { "start": 2.8, "end": 8.2, "text": "I've been using this for two weeks and look at the difference." },
      { "start": 8.2, "end": 15.1, "text": "My dark spots are fading, my skin is actually glowing, and it doesn't feel greasy at all." },
      { "start": 15.1, "end": 22.3, "text": "Most vitamin C serums don't have enough to actually do anything. This one has 3x more." },
      { "start": 22.3, "end": 28.5, "text": "Link in bio, they're running 20% off right now." }
    ],
    "language": "en"
  },

  "structure": {
    "hook": {
      "start": 0.0,
      "end": 2.8,
      "text": "POV: You finally found a vitamin C serum that actually works.",
      "style": "pov_trend",
      "style_reasoning": "Uses the 'POV:' format which is a popular TikTok trend that creates instant relatability"
    },
    "body": {
      "start": 2.8,
      "end": 22.3,
      "text": "I've been using this for two weeks and look at the difference. My dark spots are fading, my skin is actually glowing, and it doesn't feel greasy at all. Most vitamin C serums don't have enough to actually do anything. This one has 3x more.",
      "framework": "testimonial",
      "framework_reasoning": "Personal experience narrative with specific results and comparison to alternatives",
      "key_points": [
        "2 weeks of use",
        "Dark spots fading",
        "Skin is glowing",
        "Non-greasy formula",
        "3x more vitamin C than competitors"
      ]
    },
    "cta": {
      "start": 22.3,
      "end": 28.5,
      "text": "Link in bio, they're running 20% off right now.",
      "urgency": "discount",
      "action_requested": "Click link in bio to purchase"
    },
    "total_duration": 28.5
  },

  "visual_style": {
    "setting": "Bedroom / home environment",
    "lighting": "Natural daylight from window, soft and flattering",
    "framing": "Close-up talking head, shoulders and face visible",
    "avatar_description": "Young woman in her mid-20s, casual style, natural makeup",
    "avatar_appearance": {
      "age_range": "22-28",
      "gender": "female",
      "ethnicity": "Caucasian",
      "hair": "Brown, shoulder-length, slightly wavy",
      "clothing": "Casual white t-shirt",
      "makeup": "Natural, minimal",
      "accessories": "Small gold earrings"
    },
    "background": "Minimalist bedroom, neutral tones, blurred slightly",
    "camera_movement": "Static with slight handheld feel",
    "color_palette": "Warm, neutral tones - beige, white, soft browns",
    "text_overlays": [
      {
        "text": "POV: You finally found a vitamin C serum that actually works",
        "timestamp": 0.0,
        "duration": 2.8,
        "position": "center",
        "style_description": "White text, bold sans-serif font, black outline/shadow for readability"
      },
      {
        "text": "✨ 3x more Vitamin C ✨",
        "timestamp": 18.0,
        "duration": 4.0,
        "position": "bottom-center",
        "style_description": "Yellow/gold text with sparkle emojis, smaller font"
      }
    ],
    "visual_effects": [
      "Slight zoom-in during key points",
      "Quick cut to product shot at 10s"
    ]
  },

  "audio_style": {
    "voice_tone": "Casual, friendly, enthusiastic but not over-the-top",
    "pacing": "Medium-fast, conversational",
    "energy_level": "Medium-high",
    "has_background_music": true,
    "music_description": "Soft lo-fi beat, unobtrusive, trending TikTok sound",
    "has_sound_effects": false,
    "sound_effects": []
  },

  "engagement_analysis": {
    "hook_technique": "POV format creates instant relatability and curiosity - viewer immediately identifies with the 'search' for a good product",
    "retention_tactics": [
      "Direct eye contact with camera",
      "Specific timeframe mentioned (2 weeks)",
      "Visible enthusiasm when describing results",
      "Text reinforcement of key points",
      "Quick pacing keeps attention"
    ],
    "cta_approach": "Soft-sell with discount urgency - doesn't feel pushy, adds value with sale mention",
    "emotional_triggers": [
      "Relatability (searching for products that work)",
      "Aspiration (glowing skin)",
      "Fear of missing out (20% off)",
      "Trust (personal testimonial)"
    ],
    "target_audience_signals": [
      "Young female demographic (avatar appearance)",
      "Skincare-interested (specific product concerns)",
      "Budget-conscious (discount mention)",
      "Gen-Z/Millennial (casual language, TikTok format)"
    ],
    "virality_factors": [
      "Trending POV format",
      "Relatable pain point",
      "Clear before/after implication",
      "Shareable tip/recommendation"
    ]
  },

  "recreation_notes": [
    "Film in natural daylight, near a window",
    "Use casual, at-home setting to maintain authenticity",
    "Keep camera slightly handheld for organic feel",
    "Match text overlay timing with speech",
    "Maintain conversational, friend-telling-friend energy",
    "Include specific numbers/timeframes for credibility",
    "End with soft CTA that adds value (discount, limited time)"
  ]
}
```

---

## Technical Components

### 1. Audio Extractor
**Tool**: ffmpeg
**Purpose**: Extract audio track from video file

```
Input:  video.mp4
Output: audio.wav (16kHz, mono)
```

**Why these settings?**
- 16kHz sample rate is optimal for speech recognition
- Mono channel reduces file size without losing speech quality
- WAV format is universally compatible with transcription tools

---

### 2. Transcriber
**Tool**: OpenAI Whisper (local) or Whisper API
**Purpose**: Convert speech to text with timestamps

**Local Whisper (recommended for development):**
- Free, runs locally
- Models: tiny, base, small, medium, large
- `base` model is good balance of speed/accuracy

**OpenAI API (recommended for production):**
- Faster, no GPU needed
- Costs ~$0.006/minute
- More reliable

**Output format:**
```json
{
  "full_text": "Complete transcript...",
  "segments": [
    { "start": 0.0, "end": 2.5, "text": "First sentence..." },
    { "start": 2.5, "end": 5.2, "text": "Second sentence..." }
  ],
  "language": "en"
}
```

---

### 3. Visual Analyzer
**Tool**: Claude Vision API
**Purpose**: Analyze video frames to extract visual style

**Process:**
1. Extract key frames from video (1 frame per second or at scene changes)
2. Send frames to Claude Vision with analysis prompt
3. Aggregate analysis across frames

**Key frames extraction**: Use ffmpeg to extract frames at regular intervals

**Claude Vision prompt structure:**
```
Analyze this frame from a TikTok video. Describe:
1. Setting/environment
2. Lighting (natural, artificial, style)
3. Camera framing (close-up, medium, wide)
4. Person description (if present)
5. Background details
6. Any text overlays visible
7. Color palette
8. Overall aesthetic/vibe
```

**Multi-frame analysis:**
- First frame: Initial setting, hook visual
- Middle frames: Body content, any product shots
- Last frame: CTA visual, any end cards

---

### 4. Structure Identifier
**Tool**: Claude API (text analysis)
**Purpose**: Parse transcript into Hook/Body/CTA structure and analyze engagement

**Input to Claude:**
- Full transcript with timestamps
- Video duration
- Visual analysis summary

**Claude prompt structure:**
```
Given this TikTok transcript with timestamps and visual analysis, identify:

1. HOOK (first 1-5 seconds):
   - Which segment(s) form the hook?
   - What hook style is used? (POV, question, revelation, etc.)
   - Why is this hook effective?

2. BODY (middle section):
   - Which segments form the body?
   - What content framework is used? (testimonial, education, demo, etc.)
   - What are the key points made?

3. CTA (last 2-5 seconds):
   - Which segment(s) form the CTA?
   - What urgency level? (soft, medium, urgent, FOMO)
   - What action is requested?

4. ENGAGEMENT ANALYSIS:
   - What makes this video work?
   - What emotional triggers are used?
   - What retention tactics are employed?
   - Who is the target audience?

Return as structured JSON.
```

---

## File Structure

```
autougc/
├── src/
│   ├── __init__.py
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── audio_extractor.py    # ffmpeg wrapper for audio extraction
│   │   ├── transcriber.py        # Whisper transcription
│   │   ├── frame_extractor.py    # Extract key frames from video
│   │   ├── visual_analyzer.py    # Claude Vision analysis
│   │   ├── structure_parser.py   # Identify hook/body/cta structure
│   │   └── blueprint_generator.py # Orchestrates all components
│   └── models/
│       ├── __init__.py
│       └── blueprint.py          # Pydantic models for blueprint schema
├── cli.py                        # Command-line interface
├── requirements.txt
├── input/                        # Place input videos here
└── output/                       # Generated blueprints go here
```

---

## Dependencies

```
# Core
pydantic>=2.0           # Data validation and models
anthropic>=0.18.0       # Claude API (vision + text)

# Audio/Video
openai-whisper          # Local transcription (or openai for API)
# Note: ffmpeg must be installed on system

# Utilities
python-dotenv           # Environment variable management
rich                    # CLI output formatting
```

---

## Environment Variables

```
ANTHROPIC_API_KEY=sk-ant-...      # Required for Claude Vision + analysis
OPENAI_API_KEY=sk-...             # Optional, only if using Whisper API
```

---

## Usage Flow

```bash
# 1. Place video in input folder
cp ~/Downloads/viral_tiktok.mp4 input/

# 2. Run analyzer
python cli.py analyze input/viral_tiktok.mp4

# 3. Get blueprint
# Output: output/viral_tiktok_blueprint.json
```

---

## Open Questions

1. **Frame extraction frequency**: 1 frame/second vs. scene change detection?
2. **Whisper model size**: `base` good enough or need `small`/`medium`?
3. **API costs**: Estimate per video analysis (Claude Vision + text calls)?
4. **Batch processing**: Support analyzing multiple videos at once?
5. **Blueprint storage**: Just JSON files or also a database?

---

## Next Steps

1. [ ] Set up project structure and dependencies
2. [ ] Implement audio extractor (ffmpeg wrapper)
3. [ ] Implement transcriber (Whisper local first)
4. [ ] Implement frame extractor
5. [ ] Implement visual analyzer (Claude Vision)
6. [ ] Implement structure parser (Claude text)
7. [ ] Build blueprint generator (orchestrator)
8. [ ] Create CLI
9. [ ] Test with real TikTok videos
10. [ ] Iterate on prompts based on output quality
