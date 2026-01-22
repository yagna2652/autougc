"""
Test Sora 2 via Fal.ai API
Cost: Check fal.ai pricing - typically cheaper than direct OpenAI
"""

import os
import time
from pathlib import Path

import fal_client
from dotenv import load_dotenv

load_dotenv()

# Set FAL API key
fal_key = os.getenv("FAL_KEY")
if not fal_key:
    print("❌ FAL_KEY not found in .env")
    print("Get your key at: https://fal.ai/dashboard/keys")
    print("Add to .env: FAL_KEY=your_key_here")
    exit(1)

os.environ["FAL_KEY"] = fal_key

# UGC-style test prompt
ugc_prompt = """
Smartphone vertical video, young woman in her 20s in a casual bedroom setting,
holding up a small green supplement bottle enthusiastically toward the camera,
natural window lighting, authentic TikTok style, handheld camera with slight shake,
she's smiling and excited, wearing casual clothes, relatable everyday person vibe,
morning routine aesthetic
"""

print("🎬 Testing Sora 2 via Fal.ai...")
print(f"Prompt: {ugc_prompt.strip()[:100]}...")
print()

try:
    print("📤 Submitting generation request...")

    # Use synchronous subscribe method which handles polling automatically
    def on_queue_update(update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs:
                print(f"   {log['message']}")

    result = fal_client.subscribe(
        "fal-ai/sora-2/text-to-video",
        arguments={
            "prompt": ugc_prompt.strip(),
            "duration": 4,  # 4 seconds
            "aspect_ratio": "9:16",  # Portrait for TikTok
        },
        with_logs=True,
        on_queue_update=on_queue_update,
    )

    print()
    print("🎉 Generation complete!")

    # Download the video
    if result and "video" in result:
        video_url = result["video"]["url"]
        print(f"📥 Video URL: {video_url}")

        # Download video
        import urllib.request

        output_path = Path("output/sora_fal_test.mp4")
        output_path.parent.mkdir(exist_ok=True)

        urllib.request.urlretrieve(video_url, output_path)
        print(f"✅ Saved to: {output_path}")
        print()
        print("🔍 Open the file to check if it looks like authentic UGC!")
    else:
        print(f"Result: {result}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
    print()
    print("Possible issues:")
    print("  - Invalid FAL_KEY")
    print("  - Insufficient balance")
    print("  - API rate limited")
