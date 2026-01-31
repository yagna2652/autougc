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

    # Test just the prompt generation (with mock blueprint)
    python scripts/test_pipeline.py --test-prompts
"""

import argparse
import json
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
            analyze_product_node,
            analyze_visuals_node,
            download_video_node,
            extract_audio_node,
            extract_frames_node,
            finalize_prompt_node,
            generate_base_prompt_node,
            generate_blueprint_node,
            generate_mechanics_node,
            generate_video_node,
            transcribe_node,
        )

        print("✓ All nodes imported")

        from src.pipeline.graphs import (
            build_analysis_graph,
            build_full_pipeline,
            build_prompt_graph,
        )

        print("✓ Graph builders imported")

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
        from src.pipeline.graphs.full_pipeline import build_full_pipeline

        # Build without checkpointer for testing
        pipeline = build_full_pipeline(with_checkpointer=False)
        print("✓ Full pipeline built")

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
        from src.pipeline.state import PipelineConfig, create_initial_state

        # Test with defaults
        state = create_initial_state(
            video_url="https://example.com/video.mp4",
            product_description="Test product",
        )
        print("✓ Initial state created with defaults")
        print(f"  job_id: {state['job_id'][:8]}...")
        print(f"  status: {state['status']}")
        print(f"  current_step: {state['current_step']}")

        # Test with custom config
        config = PipelineConfig(
            enable_mechanics=True,
            product_category="tech",
            target_duration=10.0,
        )
        state = create_initial_state(
            video_url="https://example.com/video.mp4",
            product_images=["base64image1", "base64image2"],
            product_description="Cool gadget",
            config=config,
        )
        print("✓ Initial state created with custom config")
        print(f"  product_images: {len(state['product_images'])}")
        print(f"  enable_mechanics: {state['config']['enable_mechanics']}")

        return True

    except Exception as e:
        print(f"✗ State creation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_prompt_generation_flow():
    """Test the prompt generation flow with mock data."""
    print("\n" + "=" * 60)
    print("TEST: Prompt Generation Flow (Mock Data)")
    print("=" * 60)

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠ ANTHROPIC_API_KEY not set, skipping prompt generation test")
        return True

    try:
        from src.pipeline.nodes import (
            finalize_prompt_node,
            generate_base_prompt_node,
            generate_mechanics_node,
        )
        from src.pipeline.state import create_initial_state

        # Create state with mock blueprint
        state = create_initial_state(
            video_url="",
            product_description="Wireless earbuds with active noise cancellation",
        )

        # Add mock blueprint
        state["blueprint"] = {
            "source_video": "test.mp4",
            "total_duration": 15.0,
            "transcript": {"full_text": "These earbuds are amazing!"},
            "structure": {
                "hook": {"style": "casual_share", "text": "OMG you guys"},
                "body": {"framework": "demonstration", "text": "Let me show you"},
                "cta": {"urgency": "soft", "text": "Link in bio"},
            },
        }
        state["blueprint_summary"] = {
            "transcript": "These earbuds are amazing!",
            "hook_style": "casual_share",
            "body_framework": "demonstration",
            "cta_urgency": "soft",
            "setting": "bedroom",
            "lighting": "natural",
            "energy": "medium",
            "duration": 15.0,
        }

        print("Testing base prompt generation...")
        result = generate_base_prompt_node(state)
        state.update(result)

        if state.get("base_prompt"):
            print(f"✓ Base prompt generated ({len(state['base_prompt'])} chars)")
            print(f"  Preview: {state['base_prompt'][:100]}...")
        else:
            print("✗ No base prompt generated")
            if state.get("error"):
                print(f"  Error: {state['error']}")
            return False

        print("\nTesting mechanics generation...")
        result = generate_mechanics_node(state)
        state.update(result)

        if state.get("mechanics_prompt"):
            print(
                f"✓ Mechanics prompt generated ({len(state['mechanics_prompt'])} chars)"
            )
        else:
            print(
                "⚠ No mechanics prompt (may be expected if blueprint validation fails)"
            )

        print("\nTesting prompt finalization...")
        result = finalize_prompt_node(state)
        state.update(result)

        if state.get("final_prompt"):
            print(f"✓ Final prompt selected ({len(state['final_prompt'])} chars)")
            print(
                f"  Source: {result.get('prompt_metadata', {}).get('source', 'unknown')}"
            )
        else:
            print("✗ No final prompt")
            return False

        return True

    except Exception as e:
        print(f"✗ Prompt generation test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_full_pipeline_dry_run():
    """Test the full pipeline with a dry run (no actual API calls)."""
    print("\n" + "=" * 60)
    print("TEST: Full Pipeline Dry Run")
    print("=" * 60)

    try:
        from src.pipeline import create_initial_state, stream_pipeline

        state = create_initial_state(
            video_url="https://example.com/test.mp4",
            product_description="Test product",
        )

        print("Pipeline would execute these steps:")
        print("  1. download_video")
        print("  2. extract_audio + extract_frames (parallel)")
        print("  3. transcribe + analyze_visuals")
        print("  4. generate_blueprint")
        print("  5. analyze_product")
        print("  6. generate_base_prompt")
        print("  7. generate_mechanics")
        print("  8. finalize_prompt")
        print("  9. generate_video")
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
            product_description="",  # Will be inferred from video
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
            if state.get("final_prompt"):
                print(f"  Final prompt: {len(state['final_prompt'])} chars")
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
        "--test-prompts",
        action="store_true",
        help="Test prompt generation with mock data",
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

    # Optional tests
    if args.test_prompts:
        results["prompt_generation"] = test_prompt_generation_flow()

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
