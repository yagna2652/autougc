# AutoUGC Web Interface

AI-powered UGC (User-Generated Content) video generation platform. Generate authentic-looking TikTok-style product review videos using Sora 2 and Kling AI models.

## Features

- **TikTok Blueprint Analysis**: Extract structure, style, and pacing from existing TikTok videos
- **Smart Product Analysis**: AI-powered product image analysis for optimized prompts
- **Image-to-Video Generation**: Use product images as starting frames for accurate product appearance
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

# Optional: Anthropic API Key for smart product analysis
# Get your key at: https://console.anthropic.com/
ANTHROPIC_API_KEY=your_anthropic_api_key_here
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
  "models": ["sora2", "sora2pro", "kling"],
  "capabilities": {
    "textToVideo": true,
    "imageToVideo": true
  }
}
```

### `POST /api/generate`

Generate a video from a text prompt, optionally using a product image.

**Request Body:**
```json
{
  "prompt": "Your UGC video prompt...",
  "model": "sora2",
  "duration": 5,
  "aspectRatio": "9:16",
  "imageUrl": "https://fal.ai/storage/your-product-image.jpg"
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | Yes | The video generation prompt |
| `model` | string | Yes | `sora2`, `sora2pro`, or `kling` |
| `duration` | number | No | Video length in seconds (default: 4) |
| `aspectRatio` | string | No | `9:16` or `16:9` (default: `9:16`) |
| `imageUrl` | string | No | Product image URL for image-to-video mode |

**Response:**
```json
{
  "success": true,
  "videoUrl": "https://...",
  "model": "sora2",
  "mode": "image-to-video",
  "duration": 5,
  "aspectRatio": "9:16",
  "usedProductImage": true
}
```

### `POST /api/upload`

Upload a product image to Fal.ai storage for use with image-to-video generation.

**Request Body (JSON):**
```json
{
  "base64Image": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

**Or Form Data:**
- `image`: File upload

**Response:**
```json
{
  "success": true,
  "url": "https://fal.ai/storage/...",
  "fileName": "product-1234567890.jpg",
  "size": 102400
}
```

### `POST /api/analyze`

Analyze product images using Claude Vision to generate optimized prompts.

**Request Body:**
```json
{
  "productImages": ["data:image/jpeg;base64,..."],
  "productDescription": "Green supplement gummies",
  "blueprintData": {
    "hookStyle": "curiosity_gap",
    "bodyFramework": "demonstration",
    "setting": "bedroom",
    "lighting": "natural daylight",
    "energy": "high"
  }
}
```

## Image-to-Video Mode

The image-to-video feature ensures **accurate product appearance** in generated videos by using your product photo as the starting frame.

### How It Works

1. **Upload Product Image**: Add a product photo in Step 2
2. **Enable Image-to-Video**: Toggle is ON by default in Step 4
3. **Generate**: The AI uses your image as the first frame and animates from there

### Benefits

| Feature | Text-to-Video | Image-to-Video |
|---------|---------------|----------------|
| Product accuracy | AI imagines product | Exact product appearance |
| Brand colors | May vary | Preserved from image |
| Product details | Approximate | Accurate |
| Consistency | Variable | High |

### Supported by Both Models

| Model | Text-to-Video | Image-to-Video |
|-------|---------------|----------------|
| Sora 2 | ✅ | ✅ |
| Sora 2 Pro | ✅ | ✅ |
| Kling 2.5 Turbo Pro | ✅ | ✅ |

## Supported Models

| Model | Cost | Durations | Best For |
|-------|------|-----------|----------|
| **Sora 2** | $0.10/sec | 4, 8, 12s | Best quality, realistic UGC style |
| **Sora 2 Pro** | $0.30/sec | 4, 8, 12s | Highest quality, 3x cost |
| **Kling 2.5 Turbo Pro** | $0.07/sec | 5, 10s | Budget option, good quality |

## Workflow

1. **Enter TikTok URL** - Paste a TikTok video URL to analyze its structure
2. **Upload Product Images** - Add images of your product (up to 9)
3. **Generate Prompt** - Create an optimized UGC-style video prompt (uses Claude if API key set)
4. **Generate Video** - Select a model, enable/disable image-to-video, and generate

## Tech Stack

- **Framework**: Next.js 16 with App Router
- **Styling**: Tailwind CSS v4
- **UI Components**: shadcn/ui (Radix UI)
- **Video Generation**: Fal.ai (Sora 2, Kling)
- **Product Analysis**: Anthropic Claude (optional)

## Project Structure

```
web/
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   ├── generate/    # Video generation endpoint
│   │   │   ├── upload/      # Image upload endpoint
│   │   │   ├── analyze/     # Product analysis endpoint
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

### Product doesn't look right in video
- Make sure **Image-to-Video mode is enabled** (toggle in Step 4)
- Use a clear, well-lit product photo
- The product should be clearly visible and centered in the image

### Video generation takes too long
Video generation typically takes 1-3 minutes. Longer prompts or higher quality settings may take longer.

### Image upload fails
- Check that your image is under 10MB
- Supported formats: JPEG, PNG, WebP, GIF
- Ensure FAL_KEY has storage permissions

### Blank page / styles not loading
Try clearing the `.next` cache:
```bash
rm -rf .next && npm run dev
```

## CLI Testing

You can also test image-to-video generation from the command line:

```bash
# Test with a local image
python scripts/test_image_to_video.py --image path/to/product.jpg --model sora2

# Test with an image URL
python scripts/test_image_to_video.py --image-url https://example.com/product.jpg --model kling

# Custom prompt
python scripts/test_image_to_video.py --image product.jpg --model sora2 --prompt "Hand picking up the product..."
```

## License

MIT