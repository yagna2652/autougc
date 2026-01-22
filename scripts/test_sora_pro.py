"""
Test Sora 2 Pro via Fal.ai for higher quality UGC output.
Cost: ~$0.30/second (3x standard Sora 2)
"""

import os
import time
import urllib.request
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

# Winning prompt from experiments (v6_maximum_real)
ugc_prompt = """
iPhone 13 front facing camera video, filmed vertically for TikTok,
a real young woman not a model, mid-20s, average everyday appearance,
holding a green supplement bottle up to show the camera while talking excitedly,

CRITICAL - MUST LOOK REAL NOT AI:
- skin has visible pores especially on nose, natural sebum shine on t-zone
- slight dark circles under eyes, normal human imperfections
- eyes looking at the phone screen not the lens, that typical selfie video eye line
- natural asymmetrical face, one eye slightly different than other
- real hair with flyaways, not perfectly styled

CAMERA FEEL:
- handheld shake from her arm getting tired holding phone up
- slight focus hunting occasionally
- that iPhone front camera slight distortion
- NO stabilization, raw footage feel

ENVIRONMENT:
- her actual bedroom, not cleaned up for video
- can see edge of unmade bed, maybe some clothes
- mixed lighting: ceiling light on plus some window light
- not aesthetically arranged, real life mess

ENERGY:
- genuinely likes the product, not acting
- talking like she's FaceTiming her best friend
- natural umms and pauses, not scripted delivery
- real smile that reaches her eyes
"""

print("🎬 Testing Sora 2 PRO for higher quality...")
print(f"Prompt: {ugc_prompt.strip()[:100]}...")
print()
print("⚠️  Cost: ~$1.20 for 4 seconds (Pro pricing)")
print()

# Configuration
DURATION = 4  # seconds (4, 8, or 12)
ASPECT_RATIO = "9:16"  # Portrait for TikTok

# Pro supports higher resolution
# Standard: 720x1280 (portrait)
# Pro: 1024x1792 (portrait) for even higher quality

try:
    print("📤 Submitting Sora 2 PRO generation request...")
    start_time = time.time()

    def on_queue_update(update):
        if isinstance(update, fal_client.InProgress):
            for log in update.logs:
                print(f"   {log['message']}")

    result = fal_client.subscribe(
        "fal-ai/sora-2/text-to-video/pro",  # PRO endpoint
        arguments={
            "prompt": ugc_prompt.strip(),
            "duration": DURATION,
            "aspect_ratio": ASPECT_RATIO,
        },
        with_logs=True,
        on_queue_update=on_queue_update,
    )

    elapsed = time.time() - start_time

    print()
    print("🎉 Generation complete!")
    print(f"   Time: {elapsed:.1f}s")

    # Download the video
    if result and "video" in result:
        video_url = result["video"]["url"]
        print(f"📥 Video URL: {video_url}")

        output_dir = Path("output/experiments")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "sora_pro_test.mp4"

        urllib.request.urlretrieve(video_url, output_path)

        print(f"✅ Saved to: {output_path}")
        print()
        print("🔍 Compare this with the standard Sora 2 output!")
        print("   Standard: output/experiments/v6_maximum_real_test.mp4")
        print("   Pro:      output/experiments/sora_pro_test.mp4")
    else:
        print(f"❌ Unexpected result: {result}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
    print()
    print("Possible issues:")
    print("  - Invalid FAL_KEY")
    print("  - Insufficient balance (Pro costs more)")
    print("  - API rate limited")
