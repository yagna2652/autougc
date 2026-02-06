#!/usr/bin/env python3
"""
Test script for the LangGraph UGC pipeline.

This script tests the pipeline components individually and as a whole
to verify everything is wired correctly.

Usage:
    # Test just the imports and graph building
    python scripts/test_pipeline.py

    # Test with a real video URL (requires API keys)
    python scripts/test_pipeline.py --video-url "https://www.tiktok.com/..."
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all pipeline modules can be imported."""
    # Note: These imports are intentionally "unused" - we're testing that they work
    # ruff: noqa: F401
    print("\n" + "=" * 60)
    print("TEST: Imports")
    print("=" * 60)

    try:
        from src.pipeline.state import (
            PipelineConfig,
            PipelineState,
            create_initial_state,
        )

        print("✓ State module imported")

        from src.pipeline.nodes import (
            analyze_video_node,
            download_video_node,
            extract_frames_node,
            generate_prompt_node,
            generate_video_node,
        )

        print("✓ All nodes imported")

        from src.pipeline.graphs.simple_pipeline import build_pipeline

        print("✓ Graph builder imported")

        from langgraph.graph import END, START, StateGraph

        print("✓ LangGraph imported")

        return True

    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


def test_graph_building():
    """Test that graphs can be built without errors."""
    print("\n" + "=" * 60)
    print("TEST: Graph Building")
    print("=" * 60)

    try:
        from src.pipeline.graphs.simple_pipeline import build_pipeline

        pipeline = build_pipeline()
        print("✓ Pipeline built")

        # Check nodes
        nodes = list(pipeline.nodes.keys())
        print(f"  Nodes: {len(nodes)}")
        for node in nodes:
            if node not in ("__start__", "__end__"):
                print(f"    - {node}")

        return True

    except Exception as e:
        print(f"✗ Graph building failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_state_creation():
    """Test that initial state can be created correctly."""
    print("\n" + "=" * 60)
    print("TEST: State Creation")
    print("=" * 60)

    try:
        from src.pipeline.state import create_initial_state

        # Test with required product images
        state = create_initial_state(
            video_url="https://example.com/video.mp4",
            product_description="Test product",
            product_images=["base64image1"],
            product_mechanics="Test mechanics rules",
        )
        print("✓ Initial state created with defaults")
        print(f"  job_id: {state['job_id'][:8]}...")
        print(f"  status: {state['status']}")
        print(f"  current_step: {state['current_step']}")
        print(f"  product_mechanics: {state['product_mechanics'][:40]}...")

        return True

    except Exception as e:
        print(f"✗ State creation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_full_pipeline_dry_run():
    """Test the full pipeline with a dry run (no actual API calls)."""
    print("\n" + "=" * 60)
    print("TEST: Full Pipeline Dry Run")
    print("=" * 60)

    try:
        from src.pipeline import create_initial_state

        create_initial_state(
            video_url="https://example.com/test.mp4",
            product_description="Test product",
            product_images=["base64image1"],
        )

        print("Pipeline would execute these steps:")
        print("  1. download_video")
        print("  2. extract_frames")
        print("  3. analyze_video")
        print("  4. generate_prompt")
        print("  5. generate_video")
        print("")
        print("✓ Dry run complete (no actual execution)")

        return True

    except Exception as e:
        print(f"✗ Dry run failed: {e}")
        return False


def run_full_pipeline(video_url: str):
    """Run the full pipeline with a real video URL."""
    print("\n" + "=" * 60)
    print("TEST: Full Pipeline Execution")
    print("=" * 60)

    # Check required environment variables
    missing_keys = []
    if not os.getenv("ANTHROPIC_API_KEY"):
        missing_keys.append("ANTHROPIC_API_KEY")

    if missing_keys:
        print(f"✗ Missing required environment variables: {', '.join(missing_keys)}")
        return False

    try:
        from src.pipeline import create_initial_state, stream_pipeline

        print(f"Running pipeline with video: {video_url}")
        print("")

        state = create_initial_state(
            video_url=video_url,
            product_description="",  # Will use auto-loaded product
            product_images=["placeholder"],  # Will be replaced by product loader
        )

        # Stream execution
        for node_name, update in stream_pipeline(state):
            status = update.get("current_step", "")
            error = update.get("error", "")

            if error:
                print(f"  [{node_name}] ✗ Error: {error}")
            else:
                print(f"  [{node_name}] ✓ {status}")

            # Update state
            state.update(update)

        # Check final result
        print("")
        if state.get("status") == "completed":
            print("✓ Pipeline completed successfully!")
            if state.get("generated_video_url"):
                print(f"  Video URL: {state['generated_video_url']}")
            if state.get("video_prompt"):
                print(f"  Video prompt: {len(state['video_prompt'])} chars")
            return True
        else:
            print(f"✗ Pipeline failed: {state.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"✗ Pipeline execution failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description="Test the LangGraph UGC pipeline")
    parser.add_argument(
        "--video-url",
        help="TikTok/Reel URL to test with (requires API keys)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("=" * 60)
    print("  LangGraph UGC Pipeline Test Suite")
    print("=" * 60)

    results = {}

    # Always run basic tests
    results["imports"] = test_imports()
    results["graph_building"] = test_graph_building()
    results["state_creation"] = test_state_creation()
    results["dry_run"] = test_full_pipeline_dry_run()

    # Full pipeline test if URL provided
    if args.video_url:
        results["full_pipeline"] = run_full_pipeline(args.video_url)

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1

    print("")
    print(f"Total: {passed} passed, {failed} failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
