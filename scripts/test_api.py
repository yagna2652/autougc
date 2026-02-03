#!/usr/bin/env python3
"""
Test the pipeline API end-to-end.

This script tests the new LangGraph pipeline API to verify:
1. Job creation works
2. Prompt generation completes
3. Mechanics prompt is used (the plumbing fix!)

Usage:
    python scripts/test_api.py
"""

import json
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "http://localhost:8000/api/v1"


def make_request(method, endpoint, data=None):
    """Make an HTTP request to the API."""
    url = f"{BASE_URL}{endpoint}"

    if data:
        data = json.dumps(data).encode()
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
    else:
        req = urllib.request.Request(url, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode()}")
        return None
    except urllib.error.URLError as e:
        print(f"Connection Error: {e.reason}")
        print("Make sure the API server is running on localhost:8000")
        return None


def test_health():
    """Test the health endpoint."""
    print("Testing health endpoint...")
    result = make_request("GET", "/pipeline/health")

    if not result:
        return False

    print(f"  Status: {result.get('status')}")
    print(f"  LangGraph Enabled: {result.get('langgraph_enabled')}")
    print(f"  Mechanics Enabled: {result.get('mechanics_enabled')}")
    print(f"  API Keys: {result.get('api_keys_configured')}")
    print()

    return result.get("status") == "ok"


def test_prompt_generation():
    """Test the prompt generation endpoint."""
    print("Testing prompt generation...")

    # Create a test request
    request_data = {
        "blueprint": {
            "source_video": "test.mp4",
            "total_duration": 15.0,
            "transcript": {
                "full_text": "These wireless earbuds are amazing! The sound quality is incredible."
            },
            "structure": {
                "hook": {"style": "casual_share", "text": "OMG you guys"},
                "body": {"framework": "demonstration", "text": "Let me show you"},
                "cta": {"urgency": "soft", "text": "Link in bio"},
            },
        },
        "blueprint_summary": {
            "transcript": "These wireless earbuds are amazing!",
            "hook_style": "casual_share",
            "body_framework": "demonstration",
            "cta_urgency": "soft",
            "setting": "bedroom",
            "lighting": "natural",
            "energy": "medium",
            "duration": 15.0,
        },
        "product_description": "Premium wireless earbuds with active noise cancellation",
        "config": {
            "enable_mechanics": True,
            "product_category": "tech",
            "target_duration": 8.0,
        },
    }

    # Start the job
    result = make_request("POST", "/pipeline/generate-prompt", request_data)

    if not result:
        return False

    job_id = result.get("job_id")
    print(f"  Job started: {job_id}")

    # Poll for completion
    print("  Waiting for completion", end="", flush=True)
    max_attempts = 30
    for i in range(max_attempts):
        time.sleep(1)
        print(".", end="", flush=True)

        status_result = make_request("GET", f"/pipeline/jobs/{job_id}")
        if not status_result:
            continue

        status = status_result.get("status")
        if status == "completed":
            print(" Done!")
            break
        elif status == "failed":
            print(" Failed!")
            print(f"  Error: {status_result.get('error')}")
            return False
    else:
        print(" Timeout!")
        return False

    # Analyze results
    print()
    print("  RESULTS:")
    print("  " + "-" * 50)
    print(f"  Status: {status_result.get('status')}")
    print(f"  Prompt Source: {status_result.get('prompt_source')}")

    base_len = len(status_result.get("base_prompt") or "")
    mech_len = len(status_result.get("mechanics_prompt") or "")
    final_len = len(status_result.get("final_prompt") or "")

    print(f"  Base Prompt: {base_len} chars")
    print(f"  Mechanics Prompt: {mech_len} chars")
    print(f"  Final Prompt: {final_len} chars")
    print()

    # Check the key result
    prompt_source = status_result.get("prompt_source")
    if prompt_source == "mechanics":
        print("  ✅ SUCCESS: Mechanics prompt is being used!")
        print("     The plumbing fix is working correctly!")

        # Show a snippet of the mechanics timeline
        final_prompt = status_result.get("final_prompt") or ""
        timeline_start = final_prompt.find("HUMAN MECHANICS TIMELINE:")
        if timeline_start > 0:
            print()
            print("  HUMAN MECHANICS TIMELINE (excerpt):")
            print("  " + "-" * 50)
            timeline = final_prompt[timeline_start : timeline_start + 500]
            for line in timeline.split("\n")[:15]:
                print(f"  {line}")
            print("  ...")

        return True
    elif prompt_source == "base":
        print("  ⚠️  Base prompt used (mechanics may have failed)")
        return False
    else:
        print(f"  ❓ Unknown prompt source: {prompt_source}")
        return False


def main():
    print("=" * 60)
    print("  LangGraph Pipeline API Test")
    print("=" * 60)
    print()

    results = {}

    # Test health endpoint
    results["health"] = test_health()

    # Test prompt generation
    if results["health"]:
        results["prompt_generation"] = test_prompt_generation()
    else:
        print("Skipping prompt generation test (health check failed)")
        results["prompt_generation"] = False

    # Summary
    print()
    print("=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("All tests passed! The pipeline is working correctly.")
    else:
        print("Some tests failed. Check the output above for details.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
