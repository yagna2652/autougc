"""
Test Image-to-Video Generation with Sora 2 and Kling via Fal.ai

This script tests the image-to-video pipeline which uses a product image
as the starting frame, ensuring accurate product appearance in generated videos.

Usage:
    python scripts/test_image_to_video.py --image path/to/product.jpg --model sora2
    python scripts/test_image_to_video.py --image path/to/product.jpg --model kling
    python scripts/test_image_to_video.py --image-url https://example.com/product.jpg --model sora2
"""

import argparse
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import fal_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check for API key
fal_key = os.getenv("FAL_KEY")
if not fal_key:
    print("❌ FAL_KEY not found in .env")
    print("Get your key at: https://fal.ai/dashboard/keys")
    print("Add to .env: FAL_KEY=your_key_here")
    sys.exit(1)

os.environ["FAL_KEY"] = fal_key

# Model endpoints
ENDPOINTS = {
    "sora2": "fal-ai/sora-2/image-to-video",
    "sora2pro": "fal-ai/sora-2/image-to-video/pro",
    "kling": "fal-ai/kling-video/v2.5-turbo/pro/image-to-video",
}

# Default UGC prompt for product showcase
DEFAULT_PROMPT = """
A person's hand enters the frame and picks up the product, holding it up to show the camera.
Natural handheld camera movement, slight shake.
The hand rotates the product slightly to show different angles.
Warm natural indoor lighting, casual bedroom or living room environment visible in background.
Real, authentic UGC style - NOT cinematic, NOT polished.
iPhone front camera quality with slight grain.
"""


def upload_image_to_fal(image_path: str) -> str:
    """
    Upload a local image to Fal.ai storage and return the URL.

    Args:
        image_path: Path to the local image file

    Returns:
        Public URL of the uploaded image
    """
    print(f"📤 Uploading image to Fal storage...")
    print(f"   File: {image_path}")

    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Read file and upload
    with open(path, "rb") as f:
        file_data = f.read()

    # Determine content type
    suffix = path.suffix.lower()
    content_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    content_type = content_types.get(suffix, "image/jpeg")

    # Create a file-like object for upload
    from io import BytesIO

    file_obj = BytesIO(file_data)
    file_obj.name = path.name

    # Upload to Fal storage
    url = fal_client.upload(file_data, content_type=content_type)

    print(f"✅ Uploaded successfully!")
    print(f"   URL: {url}")

    return url


def generate_video(
    image_url: str,
    prompt: str,
    model: str = "sora2",
    duration: int = 5,
    aspect_ratio: str = "9:16",
) -> dict:
    """
    Generate a video using image-to-video with the specified model.

    Args:
        image_url: URL of the product image (must be publicly accessible)
        prompt: Text prompt describing the desired video
        model: Model to use (sora2, sora2pro, kling)
        duration: Video duration in seconds
        aspect_ratio: Aspect ratio (9:16 for portrait, 16:9 for landscape)

    Returns:
        Dict with generation results
    """
    if model not in ENDPOINTS:
        raise ValueError(
            f"Invalid model: {model}. Choose from: {list(ENDPOINTS.keys())}"
        )

    endpoint = ENDPOINTS[model]

    print(f"\n🎬 Starting image-to-video generation...")
    print(f"   Model: {model}")
    print(f"   Endpoint: {endpoint}")
    print(f"   Duration: {duration}s")
    print(f"   Aspect Ratio: {aspect_ratio}")
    print(f"   Image URL: {image_url[:80]}...")
    print(f"   Prompt: {prompt.strip()[:100]}...")
    print()

    start_time = time.time()

    def on_queue_update(update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs:
                print(f"   [{model}] {log['message']}")

    # Build arguments based on model
    # Kling uses string duration ("5" or "10"), Sora uses integer (4, 8, or 12)
    if model == "kling":
        kling_duration = "5" if duration <= 5 else "10"
        arguments = {
            "prompt": prompt.strip(),
            "image_url": image_url,
            "duration": kling_duration,
            "aspect_ratio": aspect_ratio,
        }
    else:
        # Sora 2 / Sora 2 Pro
        sora_duration = 4 if duration <= 4 else (8 if duration <= 8 else 12)
        arguments = {
            "prompt": prompt.strip(),
            "image_url": image_url,
            "duration": sora_duration,
            "aspect_ratio": aspect_ratio,
        }

    try:
        result = fal_client.subscribe(
            endpoint,
            arguments=arguments,
            with_logs=True,
            on_queue_update=on_queue_update,
        )

        elapsed = time.time() - start_time

        if result and "video" in result:
            video_url = result["video"]["url"]
            print(f"\n✅ Video generated successfully!")
            print(f"   Time: {elapsed:.1f}s")
            print(f"   URL: {video_url}")

            return {
                "success": True,
                "video_url": video_url,
                "model": model,
                "mode": "image-to-video",
                "duration": duration,
                "elapsed_time": elapsed,
            }
        else:
            print(f"\n❌ Unexpected result: {result}")
            return {
                "success": False,
                "error": "No video in result",
                "result": result,
            }

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n❌ Generation failed after {elapsed:.1f}s")
        print(f"   Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "elapsed_time": elapsed,
        }


def download_video(video_url: str, output_path: str) -> str:
    """Download video from URL to local path."""
    print(f"\n📥 Downloading video...")
    print(f"   URL: {video_url[:80]}...")
    print(f"   Output: {output_path}")

    urllib.request.urlretrieve(video_url, output_path)

    print(f"✅ Downloaded to: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Test image-to-video generation with Sora 2 and Kling"
    )
    parser.add_argument(
        "--image",
        type=str,
        help="Path to local product image file",
    )
    parser.add_argument(
        "--image-url",
        type=str,
        help="URL of product image (already hosted)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="sora2",
        choices=["sora2", "sora2pro", "kling"],
        help="Model to use for generation (default: sora2)",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=DEFAULT_PROMPT,
        help="Custom prompt for video generation",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=5,
        help="Video duration in seconds (default: 5)",
    )
    parser.add_argument(
        "--aspect-ratio",
        type=str,
        default="9:16",
        choices=["9:16", "16:9"],
        help="Aspect ratio (default: 9:16 for portrait)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output/image_to_video",
        help="Output directory for generated videos",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Skip downloading the video (just print URL)",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.image and not args.image_url:
        print("❌ Error: You must provide either --image or --image-url")
        parser.print_help()
        sys.exit(1)

    if args.image and args.image_url:
        print("⚠️  Warning: Both --image and --image-url provided. Using --image-url")

    print("=" * 60)
    print("IMAGE-TO-VIDEO GENERATION TEST")
    print("=" * 60)

    # Get or upload image URL
    if args.image_url:
        image_url = args.image_url
        print(f"\n📷 Using provided image URL: {image_url[:80]}...")
    else:
        image_url = upload_image_to_fal(args.image)

    # Generate video
    result = generate_video(
        image_url=image_url,
        prompt=args.prompt,
        model=args.model,
        duration=args.duration,
        aspect_ratio=args.aspect_ratio,
    )

    # Download if successful
    if result["success"] and not args.no_download:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"i2v_{args.model}_{timestamp}.mp4"
        output_path = output_dir / output_filename

        download_video(result["video_url"], str(output_path))

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Model: {args.model}")
    print(f"Mode: image-to-video")
    print(f"Success: {result['success']}")
    if result["success"]:
        print(f"Generation time: {result['elapsed_time']:.1f}s")
        print(f"Video URL: {result['video_url']}")
        if not args.no_download:
            print(f"Downloaded to: {output_path}")
    else:
        print(f"Error: {result.get('error', 'Unknown')}")

    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
