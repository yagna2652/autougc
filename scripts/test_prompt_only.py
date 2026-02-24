"""
Test script: run pipeline through prompt generation only (no video generation).

Prints the full video_prompt and scene_description that would be sent to Kling,
including the sanitized version, so you can inspect exactly what the model receives.

Usage:
    uv run python scripts/test_prompt_only.py <tiktok_url>
"""

import json
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True,
)
# Suppress noisy logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from src.pipeline.state import create_initial_state
from src.pipeline.nodes.download_video import download_video_node
from src.pipeline.nodes.extract_frames import extract_frames_node
from src.pipeline.nodes.analyze_video import analyze_video_node
from src.pipeline.nodes.generate_prompt import generate_prompt_node
from src.pipeline.utils.prompt_safety import sanitize_video_prompt


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/test_prompt_only.py <tiktok_url>")
        sys.exit(1)

    video_url = sys.argv[1]
    print(f"\n{'='*70}")
    print(f"PROMPT-ONLY TEST RUN")
    print(f"{'='*70}")
    print(f"TikTok URL: {video_url}\n")

    # Create initial state (auto-loads product from config.json)
    state = create_initial_state(video_url=video_url)

    # Step 1: Download
    print(f"\n{'—'*50}")
    print("Step 1/4: Downloading video...")
    result = download_video_node(state)
    state.update(result)
    if state.get("error"):
        print(f"FAILED: {state['error']}")
        sys.exit(1)
    print(f"Done: {state.get('video_path')}")

    # Step 2: Extract frames
    print(f"\n{'—'*50}")
    print("Step 2/4: Extracting frames...")
    result = extract_frames_node(state)
    state.update(result)
    if state.get("error"):
        print(f"FAILED: {state['error']}")
        sys.exit(1)
    print(f"Done: {len(state.get('frames', []))} frames")

    # Step 3: Analyze video
    print(f"\n{'—'*50}")
    print("Step 3/4: Analyzing video with vision model...")
    result = analyze_video_node(state)
    state.update(result)
    if state.get("error"):
        print(f"FAILED: {state['error']}")
        sys.exit(1)
    print("Done.")

    # Step 4: Generate prompt
    print(f"\n{'—'*50}")
    print("Step 4/4: Generating video prompt...")
    result = generate_prompt_node(state)
    state.update(result)
    if state.get("error"):
        print(f"FAILED: {state['error']}")
        sys.exit(1)
    print("Done.")

    # ── Print results ──────────────────────────────────────────────
    video_prompt = state.get("video_prompt", "")
    scene_description = state.get("scene_description", "")
    suggested_script = state.get("suggested_script", "")
    sanitized = sanitize_video_prompt(video_prompt)

    print(f"\n{'='*70}")
    print("VIDEO ANALYSIS")
    print(f"{'='*70}")
    print(json.dumps(state.get("video_analysis", {}), indent=2))

    print(f"\n{'='*70}")
    print("RAW VIDEO PROMPT (from LLM)")
    print(f"{'='*70}")
    print(video_prompt)
    print(f"\n[Word count: {len(video_prompt.split())}]")

    print(f"\n{'='*70}")
    print("SANITIZED VIDEO PROMPT (what Kling actually receives)")
    print(f"{'='*70}")
    print(sanitized)
    print(f"\n[Word count: {len(sanitized.split())}]")

    if sanitized != video_prompt:
        print("\n⚠  Sanitization changed the prompt! Diff sections may have been altered.")
    else:
        print("\n✓  Sanitization made no changes — prompt passes through intact.")

    print(f"\n{'='*70}")
    print("SCENE DESCRIPTION (for scene image generation)")
    print(f"{'='*70}")
    print(scene_description or "(none)")

    print(f"\n{'='*70}")
    print("SUGGESTED SCRIPT")
    print(f"{'='*70}")
    print(suggested_script or "(none)")

    # Check for DO NOT SHOW block
    print(f"\n{'='*70}")
    print("CONSTRAINT CHECK")
    print(f"{'='*70}")
    if "DO NOT SHOW" in video_prompt or "DO NOT" in video_prompt:
        print("✓  DO NOT SHOW block found in raw prompt")
    else:
        print("⚠  No DO NOT SHOW block in raw prompt")

    if "DO NOT SHOW" in sanitized or "DO NOT" in sanitized:
        print("✓  DO NOT SHOW block survived sanitization")
    else:
        print("⚠  DO NOT SHOW block was LOST during sanitization")

    # Check for key terms
    key_terms = ["vertical", "squeeze", "fidget", "bounce", "plunge", "spring"]
    found = [t for t in key_terms if t.lower() in sanitized.lower()]
    missing = [t for t in key_terms if t.lower() not in sanitized.lower()]
    if found:
        print(f"✓  Key fidget terms found: {', '.join(found)}")
    if missing:
        print(f"⚠  Missing fidget terms: {', '.join(missing)}")

    print(f"\n{'='*70}")
    print("PRODUCT MECHANICS (what was injected)")
    print(f"{'='*70}")
    print(state.get("product_mechanics", "(none)"))

    print()


if __name__ == "__main__":
    main()
