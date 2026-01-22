"""
Quick test to check Sora API access and generate a UGC-style clip.
Cost: ~$0.40 for a 4-second clip
"""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# UGC-style test prompt
ugc_prompt = """
Smartphone vertical video, young woman in her 20s in a casual bedroom setting,
holding up a small green supplement bottle enthusiastically toward the camera,
natural window lighting, authentic TikTok style, handheld camera with slight shake,
she's smiling and excited, wearing casual clothes, relatable everyday person vibe,
morning routine aesthetic
"""

print("🎬 Testing Sora API access...")
print(f"Prompt: {ugc_prompt[:100]}...")
print()

try:
    # Create video generation job
    print("📤 Submitting generation request...")
    video = client.videos.create(
        model="sora-2",
        prompt=ugc_prompt.strip(),
        seconds="4",  # 4 second clip = $0.40
        size="720x1280",  # Portrait for TikTok
    )

    print(f"✅ Job created! ID: {video.id}")
    print(f"   Status: {video.status}")
    print(f"   Model: {video.model}")
    print()

    # Poll for completion
    print("⏳ Waiting for generation (this may take 1-3 minutes)...")
    while video.status in ["queued", "in_progress"]:
        time.sleep(10)
        video = client.videos.retrieve(video.id)
        print(f"   Progress: {video.progress}% - Status: {video.status}")

    if video.status == "completed":
        print()
        print("🎉 Generation complete!")

        # Download the video
        output_path = Path("output/sora_test.mp4")
        output_path.parent.mkdir(exist_ok=True)

        print(f"📥 Downloading video...")
        response = client.videos.download_content(video.id)

        with open(output_path, "wb") as f:
            f.write(response.read())

        print(f"✅ Saved to: {output_path}")
        print()
        print("🔍 Open the file to check if it looks like authentic UGC!")

    else:
        print(f"❌ Generation failed: {video.status}")
        if hasattr(video, "error") and video.error:
            print(f"   Error: {video.error}")

except Exception as e:
    print(f"❌ Error: {e}")
    print()
    print("Possible issues:")
    print("  - API key doesn't have Sora access")
    print("  - Insufficient balance")
    print("  - Rate limited")
