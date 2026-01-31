#!/usr/bin/env python3
"""
Check pipeline job results.

Usage:
    python scripts/check_result.py <job_id>
    python scripts/check_result.py  # Uses most recent job
"""

import json
import sys
import urllib.request


def get_job_result(job_id: str) -> dict:
    """Fetch job result from API."""
    url = f"http://localhost:8000/api/v1/pipeline/jobs/{job_id}"
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode())


def print_result(data: dict) -> None:
    """Print formatted result."""
    print("=" * 60)
    print("PIPELINE RESULT SUMMARY")
    print("=" * 60)
    print()
    print(f"Job ID: {data['job_id']}")
    print(f"Status: {data['status']}")
    print(f"Current Step: {data['current_step']}")
    print()

    if data.get("error"):
        print(f"ERROR: {data['error']}")
        return

    # Prompt info
    print("PROMPT GENERATION:")
    print("-" * 60)
    print(f"Prompt Source: {data.get('prompt_source', 'N/A')}")

    base_len = len(data.get("base_prompt") or "")
    mech_len = len(data.get("mechanics_prompt") or "")
    final_len = len(data.get("final_prompt") or "")

    print(f"Base Prompt Length: {base_len} chars")
    print(f"Mechanics Prompt Length: {mech_len} chars")
    print(f"Final Prompt Length: {final_len} chars")
    print()

    # Check if mechanics is being used
    if data.get("prompt_source") == "mechanics":
        print("✓ SUCCESS: Mechanics prompt is being used!")
    elif data.get("prompt_source") == "base":
        print("⚠ WARNING: Base prompt used (mechanics may have failed)")
    else:
        print(f"? Unknown prompt source: {data.get('prompt_source')}")
    print()

    # Show mechanics timeline if present
    final_prompt = data.get("final_prompt") or ""
    timeline_start = final_prompt.find("HUMAN MECHANICS TIMELINE:")
    if timeline_start > 0:
        print("HUMAN MECHANICS TIMELINE (excerpt):")
        print("-" * 60)
        timeline = final_prompt[timeline_start : timeline_start + 800]
        print(timeline + "...")
    print()

    # Video URL if present
    if data.get("generated_video_url"):
        print(f"Generated Video: {data['generated_video_url']}")
        print()

    # Timestamps
    if data.get("created_at"):
        print(f"Created: {data['created_at']}")
    if data.get("completed_at"):
        print(f"Completed: {data['completed_at']}")


def main():
    if len(sys.argv) > 1:
        job_id = sys.argv[1]
    else:
        # Default job ID from recent test
        job_id = "831ecf46-e971-4c22-813d-04fac6f93b6c"
        print(f"Using default job ID: {job_id}")
        print()

    try:
        data = get_job_result(job_id)
        print_result(data)
    except urllib.error.HTTPError as e:
        print(f"Error: Job {job_id} not found (HTTP {e.code})")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Could not connect to server at localhost:8000")
        print(f"       Make sure the API server is running")
        sys.exit(1)


if __name__ == "__main__":
    main()
