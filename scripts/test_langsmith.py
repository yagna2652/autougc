#!/usr/bin/env python3
"""
Test script to verify LangSmith connection is working.

Run this from the autougc directory:
    python scripts/test_langsmith.py
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()


def test_langsmith_connection():
    """Test that LangSmith is properly configured and working."""

    print("=" * 60)
    print("LangSmith Connection Test")
    print("=" * 60)

    # Check environment variables
    tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"
    api_key = os.getenv("LANGCHAIN_API_KEY", "")
    project = os.getenv("LANGCHAIN_PROJECT", "default")

    print("\n1. Checking environment variables...")
    print(
        f"   LANGCHAIN_TRACING_V2: {'✓ true' if tracing_enabled else '✗ not set or false'}"
    )
    print(
        f"   LANGCHAIN_API_KEY: {'✓ set (' + api_key[:10] + '...)' if api_key else '✗ not set'}"
    )
    print(f"   LANGCHAIN_PROJECT: {project}")

    if not tracing_enabled:
        print("\n❌ LANGCHAIN_TRACING_V2 is not set to 'true'")
        print("   Add this to your .env file: LANGCHAIN_TRACING_V2=true")
        return False

    if not api_key:
        print("\n❌ LANGCHAIN_API_KEY is not set")
        print("   Get your API key from https://smith.langchain.com")
        return False

    # Try to import langsmith
    print("\n2. Checking langsmith package...")
    try:
        from langsmith import Client

        print("   ✓ langsmith package is installed")
    except ImportError:
        print("   ✗ langsmith package not found")
        print("   Run: pip install langsmith")
        return False

    # Try to connect to LangSmith
    print("\n3. Testing connection to LangSmith...")
    try:
        client = Client()
        # Try to list projects (this will fail if API key is invalid)
        list(client.list_projects(limit=1))
        print("   ✓ Successfully connected to LangSmith!")
        print(f"   ✓ API key is valid")
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        print("   Check that your API key is correct")
        return False

    # Test our tracing module
    print("\n4. Testing AutoUGC tracing module...")
    try:
        from src.tracing import is_tracing_enabled

        if is_tracing_enabled():
            print("   ✓ Tracing is enabled")
        else:
            print("   ✗ Tracing module says tracing is disabled")
            return False
    except ImportError as e:
        print(f"   ✗ Could not import tracing module: {e}")
        return False

    # Make a test trace
    print("\n5. Creating a test trace...")
    try:
        from langsmith.run_helpers import trace

        with trace(
            name="test_connection",
            run_type="chain",
            inputs={"test": "hello from AutoUGC"},
            metadata={"purpose": "connection_test"},
        ) as run:
            run.end(outputs={"status": "success", "message": "LangSmith is working!"})

        print("   ✓ Test trace created successfully!")
        print(
            f"\n   View your trace at: https://smith.langchain.com/o/default/projects/p/{project}"
        )
    except Exception as e:
        print(f"   ✗ Failed to create test trace: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ All tests passed! LangSmith is ready to use.")
    print("=" * 60)
    print(f"\nView your traces at: https://smith.langchain.com")
    print(f"Project: {project}")

    return True


def test_traced_llm_call():
    """Optional: Test an actual traced LLM call (requires ANTHROPIC_API_KEY)."""

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        print("\nSkipping LLM test (ANTHROPIC_API_KEY not set)")
        return

    print("\n" + "-" * 60)
    print("Bonus: Testing traced LLM call...")
    print("-" * 60)

    try:
        from src.tracing import TracedAnthropicClient

        client = TracedAnthropicClient(api_key=anthropic_key, trace_name="test")

        response = client.messages.create(
            model="claude-3-5-haiku-20241022",  # Using cheapest model for test
            max_tokens=50,
            messages=[
                {
                    "role": "user",
                    "content": "Say 'LangSmith test successful!' in exactly 5 words.",
                }
            ],
        )

        result = response.content[0].text
        print(f"   ✓ LLM Response: {result}")
        print("   ✓ This call was traced to LangSmith!")
        print("\n   Check LangSmith to see the full prompt and response logged.")

    except Exception as e:
        print(f"   ✗ LLM test failed: {e}")


if __name__ == "__main__":
    success = test_langsmith_connection()

    if success:
        test_traced_llm_call()

    sys.exit(0 if success else 1)
