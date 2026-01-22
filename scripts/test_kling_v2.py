"""
Kling Video Prompt Experiments - Optimized for Kling's strengths.

Kling tends to:
- Better at realistic human faces and skin
- More cinematic by default (need to counter this)
- Different prompt interpretation than Sora

Testing variations to find the best UGC output.
"""

import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import fal_client
from dotenv import load_dotenv

load_dotenv()

# Set FAL API key
fal_key = os.getenv("FAL_KEY")
if not fal_key:
    print("❌ FAL_KEY not found in .env")
    exit(1)

os.environ["FAL_KEY"] = fal_key

# Kling endpoint
KLING_ENDPOINT = "fal-ai/kling-video/v2.5-turbo/pro/text-to-video"

# =============================================================================
# KLING-OPTIMIZED PROMPTS
# =============================================================================

KLING_PROMPTS = {
    "v1_baseline": """
iPhone selfie video, young woman holding green supplement bottle, bedroom, TikTok style,
handheld camera shake, natural lighting, casual clothes, excited expression
""",
    "v2_anti_cinematic": """
NOT a professional video, NOT cinematic, amateur iPhone footage,
young woman in her 20s recording herself on front camera,
holding up a green vitamin bottle excitedly,
typical TikTok creator in her messy bedroom,
bad lighting from ceiling light, unmade bed visible,
real skin with pores and imperfections,
looking at her phone screen while recording,
genuine casual energy like texting a friend,
slight hand shake, raw unedited phone quality
""",
    "v3_specific_details": """
A 24 year old woman films herself on iPhone front camera in portrait mode.
She holds a green supplement bottle in her right hand, showing it to the camera.
Location: her actual bedroom with messy unmade bed and clothes on a chair.
Lighting: harsh overhead ceiling light mixed with daylight from window, unflattering but real.
Her appearance: no makeup, hair in messy ponytail, wearing oversized grey sweatshirt.
Skin: real texture visible, slight shine on forehead, natural imperfections.
Eyes: looking at phone screen not lens, that typical selfie video eyeline.
Camera: handheld with natural shake, amateur framing slightly off-center.
Expression: genuinely happy about the product, authentic smile.
This looks like a real TikTok not a commercial.
""",
    "v4_ugc_creator_style": """
POV: you're watching a TikTok from a regular girl reviewing her new vitamins.
She's in her bedroom, phone propped up or held at arm's length.
Front facing iPhone camera quality - not 4K, not stabilized.
She picks up a green supplement bottle and shows it excitedly.
Real person vibes: messy room, no ring light, wearing loungewear.
Her skin looks normal - pores visible, maybe a little oily, no filter.
She keeps glancing at herself on the screen while talking.
Authentic energy - she actually likes this product, not acting.
The whole thing feels unscripted and genuine.
Vertical video 9:16 for TikTok.
""",
    "v5_negative_emphasis": """
AMATEUR home video, NOT professional, NOT cinematic, NOT polished.
Real young woman (not actress, not model) in messy bedroom.
iPhone front camera selfie style video.
She holds green vitamin gummies bottle toward camera enthusiastically.

What this is NOT:
- NOT smooth stabilized footage
- NOT perfect lighting
- NOT flawless skin
- NOT a studio
- NOT scripted

What this IS:
- shaky handheld phone footage
- harsh mixed indoor lighting
- real skin texture and pores
- actual messy lived-in bedroom
- genuine unscripted excitement
- eyes focused on phone screen not camera lens
- casual clothes, no styling
""",
    "v6_tiktok_native": """
authentic tiktok video filmed on iphone.
girl in her 20s showing off green supplement bottle in her bedroom.
front camera selfie angle, phone held in one hand.
real bedroom environment - bed unmade, random stuff visible, not staged.
natural unflattering indoor lighting, no ring light.
she has real skin - you can see pores and texture, no beauty filter.
her eyes look at the screen not through the camera.
wearing comfortable casual clothes, hair not done.
handheld camera movement, slight shake, amateur framing.
genuine excitement about the product, talking like to a friend.
raw iphone video quality, not color graded or edited.
vertical format for tiktok.
""",
    "v7_maximum_real": """
iphone 13 front camera video. vertical 9:16. raw footage not edited.

subject: real young woman, early 20s, average looking, NOT a model.
action: excitedly holding up and showing a green supplement bottle.

REALISM REQUIREMENTS:
- face has visible pores, natural skin texture, slight imperfections
- eyes looking slightly down at phone screen, not directly at lens
- natural facial asymmetry
- hair has flyaways, not perfectly styled
- no makeup or very minimal

CAMERA REQUIREMENTS:
- handheld shake from holding phone up with one arm
- occasional subtle refocusing
- slight wide angle distortion typical of front camera
- NOT stabilized, NOT smooth, NOT cinematic

ENVIRONMENT REQUIREMENTS:
- real bedroom, messy and lived-in
- unmade bed or clothes visible
- mixed lighting from ceiling light and window
- not aesthetically arranged

BEHAVIOR REQUIREMENTS:
- genuine enthusiasm, not performed
- casual like facetiming a friend
- natural speech rhythm
- real smile showing in eyes

this should look indistinguishable from a real tiktok video.
""",
}


def generate_kling_video(prompt: str, output_name: str, duration: str = "5") -> dict:
    """Generate a video using Kling via Fal.ai"""

    print(f"🎬 Generating: {output_name}")
    print(f"   Prompt: {prompt.strip()[:80]}...")
    print()

    start_time = time.time()

    try:

        def on_queue_update(update):
            if isinstance(update, fal_client.InProgress):
                for log in update.logs:
                    print(f"   {log['message']}")

        result = fal_client.subscribe(
            KLING_ENDPOINT,
            arguments={
                "prompt": prompt.strip(),
                "duration": duration,
                "aspect_ratio": "9:16",
            },
            with_logs=True,
            on_queue_update=on_queue_update,
        )

        elapsed = time.time() - start_time

        if result and "video" in result:
            video_url = result["video"]["url"]

            output_dir = Path("output/kling_experiments")
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{output_name}.mp4"

            urllib.request.urlretrieve(video_url, output_path)

            print(f"✅ Saved to: {output_path}")
            print(f"   Time: {elapsed:.1f}s")
            print()

            return {
                "success": True,
                "path": str(output_path),
                "url": video_url,
                "time": elapsed,
            }
        else:
            return {"error": "No video in result", "result": result}

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}


def run_single_experiment(name: str) -> dict:
    """Run a single experiment by name."""
    if name not in KLING_PROMPTS:
        print(f"❌ Unknown experiment: {name}")
        print(f"   Available: {list(KLING_PROMPTS.keys())}")
        return {"error": "Unknown experiment"}

    prompt = KLING_PROMPTS[name]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = f"{name}_{timestamp}"

    return generate_kling_video(prompt, output_name)


def run_all_experiments():
    """Run all experiments."""
    results = {}

    print("=" * 60)
    print("RUNNING ALL KLING EXPERIMENTS")
    print("=" * 60)
    print()

    for name in KLING_PROMPTS:
        print(f"{'=' * 60}")
        print(f"EXPERIMENT: {name}")
        print(f"{'=' * 60}")

        result = run_single_experiment(name)
        results[name] = result

        print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, result in results.items():
        status = "✅" if result.get("success") else "❌"
        path = result.get("path", result.get("error", "unknown"))
        print(f"{status} {name}: {path}")

    return results


if __name__ == "__main__":
    import sys

    print("🎬 Kling Video Prompt Experiments")
    print("=" * 50)
    print()
    print("Available experiments:")
    for i, name in enumerate(KLING_PROMPTS.keys(), 1):
        print(f"  {i}. {name}")
    print()
    print("Options:")
    print("  - Enter number (1-7) to run single experiment")
    print("  - Enter 'all' to run all experiments")
    print("  - Enter experiment name directly")
    print()

    choice = input("Choice: ").strip().lower()

    if choice == "all":
        run_all_experiments()
    elif choice.isdigit():
        idx = int(choice) - 1
        names = list(KLING_PROMPTS.keys())
        if 0 <= idx < len(names):
            run_single_experiment(names[idx])
        else:
            print("Invalid selection")
    elif choice in KLING_PROMPTS:
        run_single_experiment(choice)
    else:
        print("Invalid choice")
