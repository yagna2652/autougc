# AutoUGC Web Interface

AI-powered UGC (User-Generated Content) video generation platform. Generate authentic-looking TikTok-style product review videos using Sora 2 and Kling AI models.

## Features

- **TikTok Blueprint Analysis**: Extract structure, style, and pacing from existing TikTok videos
- **UGC Prompt Generation**: Create optimized prompts for realistic UGC-style video output
- **Multi-Model Support**: Generate videos with Sora 2 or Kling 2.5 Turbo Pro
- **Video Preview & Download**: Watch generated videos in-browser and download them

## Getting Started

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Create a `.env.local` file in the `web` directory:

```bash
# Required: Fal.ai API Key for video generation
# Get your key at: https://fal.ai/dashboard/keys
FAL_KEY=your_fal_api_key_here
```

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## API Endpoints

### `GET /api/status`

Check API configuration and available models.

**Response:**
```json
{
  "status": "ok",
  "configured": true,
  "models": {
    "sora2": { "name": "Sora 2", "costPerSecond": 0.10 },
    "kling": { "name": "Kling 2.5 Turbo Pro", "costPerSecond": 0.07 }
  }
}
```

### `POST /api/generate`

Generate a video from a text prompt.

**Request Body:**
```json
{
  "prompt": "Your UGC video prompt...",
  "model": "sora2",
  "duration": 5,
  "aspectRatio": "9:16"
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | Yes | The video generation prompt |
| `model` | string | Yes | `sora2`, `sora2pro`, or `kling` |
| `duration` | number | No | Video length in seconds (default: 4) |
| `aspectRatio` | string | No | `9:16` or `16:9` (default: `9:16`) |

**Response:**
```json
{
  "success": true,
  "videoUrl": "https://...",
  "model": "sora2",
  "duration": 5,
  "aspectRatio": "9:16"
}
```

## Supported Models

| Model | Cost | Durations | Notes |
|-------|------|-----------|-------|
| **Sora 2** | $0.10/sec | 4, 8, 12s | Best quality, realistic UGC style |
| **Sora 2 Pro** | $0.30/sec | 4, 8, 12s | Highest quality, 3x cost |
| **Kling 2.5 Turbo Pro** | $0.07/sec | 5, 10s | Budget option, good quality |

## Workflow

1. **Enter TikTok URL** - Paste a TikTok video URL to analyze its structure
2. **Upload Product Images** - Add images of your product (up to 9)
3. **Generate Prompt** - Create an optimized UGC-style video prompt
4. **Generate Video** - Select a model and generate your video

## Tech Stack

- **Framework**: Next.js 16 with App Router
- **Styling**: Tailwind CSS v4
- **UI Components**: shadcn/ui (Radix UI)
- **Video Generation**: Fal.ai (Sora 2, Kling)

## Project Structure

```
web/
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   ├── generate/    # Video generation endpoint
│   │   │   └── status/      # API status endpoint
│   │   ├── page.tsx         # Main UI
│   │   ├── layout.tsx       # Root layout
│   │   └── globals.css      # Global styles
│   ├── components/
│   │   └── ui/              # shadcn/ui components
│   └── lib/
│       └── utils.ts         # Utility functions
├── .env.local               # Environment variables (create this)
├── env.example              # Example environment file
└── package.json
```

## Troubleshooting

### "FAL_KEY environment variable not configured"
Create a `.env.local` file with your Fal.ai API key.

### "Insufficient Fal.ai balance"
Add credits to your Fal.ai account at [fal.ai/dashboard](https://fal.ai/dashboard).

### Video generation takes too long
Video generation typically takes 1-3 minutes. Longer prompts or higher quality settings may take longer.

### Blank page / styles not loading
Try clearing the `.next` cache:
```bash
rm -rf .next && npm run dev
```

## License

MIT