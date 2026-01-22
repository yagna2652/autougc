# AutoUGC - TikTok/Reel Analyzer & UGC Ad Generator

Automated pipeline for analyzing TikTok/Reels videos and generating UGC-style ads.

## Phase 1: Video Analyzer

Extracts a structured "blueprint" from any TikTok/Reel video, capturing everything needed to recreate it:

- **Transcript** with timestamps
- **Structure** (Hook / Body / CTA breakdown)
- **Visual Style** (setting, lighting, framing, avatar, colors)
- **Audio Style** (tone, pacing, music)
- **Engagement Analysis** (what makes it work)

## Installation

### Prerequisites

- Python 3.11+
- ffmpeg (for audio/video processing)

#### Install ffmpeg

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

### Setup

```bash
# Clone the repository
cd autougc

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment variables
cp .env.example .env
# Edit .env and add your API keys
```

### API Keys Required

- **Anthropic API Key** (required): For Claude Vision and text analysis
- **OpenAI API Key** (optional): Only if using Whisper API instead of local

## Usage

```bash
# Analyze a video
python -m src.cli analyze input/video.mp4

# Specify output path
python -m src.cli analyze input/video.mp4 -o output/my_blueprint.json

# Use Whisper API instead of local
python -m src.cli analyze input/video.mp4 --whisper-mode api
```

## Project Structure

```
autougc/
├── src/
│   ├── __init__.py
│   ├── cli.py                    # Command-line interface
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── audio_extractor.py    # Extract audio from video (ffmpeg)
│   │   ├── transcriber.py        # Speech-to-text (Whisper)
│   │   ├── frame_extractor.py    # Extract key frames
│   │   ├── visual_analyzer.py    # Analyze visuals (Claude Vision)
│   │   ├── structure_parser.py   # Parse Hook/Body/CTA
│   │   └── blueprint_generator.py # Orchestrator
│   └── models/
│       ├── __init__.py
│       └── blueprint.py          # Pydantic data models
├── tests/
├── input/                        # Place videos here
├── output/                       # Generated blueprints
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Output: Video Blueprint

The analyzer outputs a JSON blueprint containing:

```json
{
  "source_video": "video.mp4",
  "duration_seconds": 28.5,
  "transcript": {
    "full_text": "...",
    "segments": [{ "start": 0.0, "end": 2.5, "text": "..." }]
  },
  "structure": {
    "hook": { "start": 0.0, "end": 3.0, "text": "...", "style": "pov_trend" },
    "body": { "start": 3.0, "end": 25.0, "text": "...", "framework": "testimonial" },
    "cta": { "start": 25.0, "end": 28.5, "text": "...", "urgency": "soft" }
  },
  "visual_style": { ... },
  "audio_style": { ... },
  "engagement_analysis": { ... }
}
```

## Development

```bash
# Run tests
pytest

# Type checking
mypy src/

# Linting
ruff check src/
```

## License

MIT