"""
LangSmith Tracing Utilities for AI-Native Observability.

This module provides wrappers and utilities to trace all LLM calls
in the AutoUGC pipeline, giving you full visibility into:
- Every prompt sent to Claude
- Every response received
- Token usage and costs
- Latency metrics
- Full pipeline execution traces

Setup:
    1. Set environment variables:
       - LANGCHAIN_TRACING_V2=true
       - LANGCHAIN_API_KEY=your_langsmith_api_key
       - LANGCHAIN_PROJECT=autougc-pipeline (optional, defaults to "default")

    2. Replace direct Anthropic calls with TracedAnthropicClient:
       ```python
       from src.tracing import TracedAnthropicClient

       client = TracedAnthropicClient(api_key="...")
       response = client.messages.create(...)  # Automatically traced!
       ```

    3. Use decorators for custom function tracing:
       ```python
       from src.tracing import trace_function, trace_chain

       @trace_function(name="my_analysis_step")
       def analyze_something(data):
           ...
       ```

View traces at: https://smith.langchain.com
"""

import functools
import inspect
import os
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, Callable, Optional

import anthropic

# Check if LangSmith is available and enabled
LANGSMITH_ENABLED = os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGCHAIN_PROJECT", "autougc-pipeline")

# Try to import langsmith for native tracing
try:
    from langsmith import Client as LangSmithClient
    from langsmith.run_helpers import trace

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    trace = None  # type: ignore
    LangSmithClient = None  # type: ignore


def is_tracing_enabled() -> bool:
    """Check if LangSmith tracing is enabled and configured."""
    return LANGSMITH_ENABLED and LANGSMITH_AVAILABLE and bool(LANGSMITH_API_KEY)


def get_langsmith_client() -> Optional[Any]:
    """Get a LangSmith client if available and configured."""
    if not is_tracing_enabled() or LangSmithClient is None:
        return None
    return LangSmithClient()


class TracedMessages:
    """
    Wrapper around Anthropic's messages API that adds LangSmith tracing.

    This class intercepts all message creation calls and logs them to LangSmith,
    capturing:
    - Input messages and system prompts
    - Model configuration (model, max_tokens, temperature, etc.)
    - Full response content
    - Token usage statistics
    - Latency measurements
    """

    def __init__(self, client: anthropic.Anthropic, trace_name: str = "anthropic"):
        self._client = client
        self._messages = client.messages
        self._trace_name = trace_name

    def create(
        self,
        *,
        model: str,
        max_tokens: int,
        messages: list[dict],
        system: str | None = None,
        temperature: float | None = None,
        metadata: dict | None = None,
        **kwargs,
    ) -> anthropic.types.Message:
        """
        Create a message with automatic LangSmith tracing.

        All parameters are passed through to the Anthropic API.
        Additional tracing metadata can be provided via the `metadata` parameter.
        """
        # Prepare trace metadata
        trace_metadata = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "provider": "anthropic",
            "trace_name": self._trace_name,
            **(metadata or {}),
        }

        # Build inputs for tracing
        inputs: dict[str, Any] = {
            "messages": messages,
            "model": model,
            "max_tokens": max_tokens,
        }
        if system:
            inputs["system"] = system
        if temperature is not None:
            inputs["temperature"] = temperature

        start_time = time.time()

        if is_tracing_enabled() and trace is not None:
            # Use LangSmith's trace context manager
            with trace(
                name=f"{self._trace_name}.messages.create",
                run_type="llm",
                inputs=inputs,
                metadata=trace_metadata,
            ) as run:
                try:
                    # Make the actual API call
                    response = self._messages.create(
                        model=model,
                        max_tokens=max_tokens,
                        messages=messages,
                        system=system if system else anthropic.NOT_GIVEN,
                        temperature=temperature
                        if temperature is not None
                        else anthropic.NOT_GIVEN,
                        **kwargs,
                    )

                    # Calculate latency
                    latency_ms = (time.time() - start_time) * 1000

                    # Extract response data for tracing
                    outputs = {
                        "content": [
                            {"type": block.type, "text": getattr(block, "text", None)}
                            for block in response.content
                        ],
                        "model": response.model,
                        "stop_reason": response.stop_reason,
                        "usage": {
                            "input_tokens": response.usage.input_tokens,
                            "output_tokens": response.usage.output_tokens,
                        },
                        "latency_ms": latency_ms,
                    }

                    # Update the run with outputs
                    run.end(outputs=outputs)

                    return response

                except Exception as e:
                    run.end(error=str(e))
                    raise
        else:
            # No tracing - just make the API call directly
            return self._messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=messages,
                system=system if system else anthropic.NOT_GIVEN,
                temperature=temperature
                if temperature is not None
                else anthropic.NOT_GIVEN,
                **kwargs,
            )


class TracedAnthropicClient:
    """
    Drop-in replacement for anthropic.Anthropic that adds LangSmith tracing.

    Usage:
        # Instead of:
        client = anthropic.Anthropic(api_key="...")

        # Use:
        client = TracedAnthropicClient(api_key="...", trace_name="my_component")

        # All calls are now traced:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": "Hello!"}]
        )

    View traces at: https://smith.langchain.com
    """

    def __init__(
        self,
        api_key: str | None = None,
        trace_name: str = "anthropic",
        **kwargs,
    ):
        """
        Initialize the traced Anthropic client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            trace_name: Name prefix for traces (helps identify component in LangSmith)
            **kwargs: Additional arguments passed to anthropic.Anthropic
        """
        self._client = anthropic.Anthropic(api_key=api_key, **kwargs)
        self._trace_name = trace_name
        self._messages = TracedMessages(self._client, trace_name)

    @property
    def messages(self) -> TracedMessages:
        """Get the traced messages API."""
        return self._messages

    def __getattr__(self, name: str) -> Any:
        """Forward other attributes to the underlying client."""
        return getattr(self._client, name)


def trace_function(
    name: str | None = None,
    run_type: str = "chain",
    metadata: dict[str, Any] | None = None,
) -> Callable[..., Any]:
    """
    Decorator to trace any function with LangSmith.

    Usage:
        @trace_function(name="analyze_video_frames")
        def analyze_frames(frames: list[Path]) -> dict:
            # Your analysis code
            return results

    Args:
        name: Name for the trace (defaults to function name)
        run_type: Type of run ("chain", "tool", "retriever", etc.)
        metadata: Additional metadata to include in the trace
    """

    def decorator(func: Callable) -> Callable:
        trace_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if is_tracing_enabled() and trace is not None:
                with trace(
                    name=trace_name,
                    run_type=run_type,
                    inputs={
                        "args": _serialize_args(args),
                        "kwargs": _serialize_args(kwargs),
                    },
                    metadata=metadata or {},
                ) as run:
                    try:
                        result = func(*args, **kwargs)
                        run.end(outputs={"result": _serialize_args(result)})
                        return result
                    except Exception as e:
                        run.end(error=str(e))
                        raise
            else:
                return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if is_tracing_enabled() and trace is not None:
                with trace(
                    name=trace_name,
                    run_type=run_type,
                    inputs={
                        "args": _serialize_args(args),
                        "kwargs": _serialize_args(kwargs),
                    },
                    metadata=metadata or {},
                ) as run:
                    try:
                        result = await func(*args, **kwargs)
                        run.end(outputs={"result": _serialize_args(result)})
                        return result
                    except Exception as e:
                        run.end(error=str(e))
                        raise
            else:
                return await func(*args, **kwargs)

        # Return appropriate wrapper based on whether function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


def trace_chain(
    name: str, metadata: dict[str, Any] | None = None
) -> Callable[..., Any]:
    """Convenience decorator for tracing chain-like operations."""
    return trace_function(name=name, run_type="chain", metadata=metadata)


def trace_tool(name: str, metadata: dict[str, Any] | None = None) -> Callable[..., Any]:
    """Convenience decorator for tracing tool operations."""
    return trace_function(name=name, run_type="tool", metadata=metadata)


@contextmanager
def trace_span(
    name: str,
    run_type: str = "chain",
    inputs: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
):
    """
    Context manager for tracing a block of code.

    Usage:
        with trace_span("process_video", inputs={"url": video_url}) as span:
            # Your code here
            result = process_video(video_url)
            span.set_outputs({"frames": len(result.frames)})
    """
    if is_tracing_enabled() and trace is not None:
        with trace(
            name=name,
            run_type=run_type,
            inputs=inputs or {},
            metadata=metadata or {},
        ) as run:
            # Create a simple wrapper to allow setting outputs
            class SpanWrapper:
                def set_outputs(self, outputs: dict[str, Any]) -> None:
                    run.end(outputs=outputs)

                def set_error(self, error: str) -> None:
                    run.end(error=error)

            yield SpanWrapper()
    else:
        # No-op wrapper when tracing is disabled
        class NoOpSpan:
            def set_outputs(self, outputs: dict[str, Any]) -> None:
                pass

            def set_error(self, error: str) -> None:
                pass

        yield NoOpSpan()


def _serialize_args(obj: Any) -> Any:
    """
    Serialize arguments for tracing, handling non-JSON-serializable types.
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_serialize_args(item) for item in obj]
    if isinstance(obj, dict):
        return {str(k): _serialize_args(v) for k, v in obj.items()}
    if hasattr(obj, "__dict__"):
        return {
            "__class__": obj.__class__.__name__,
            **{
                k: _serialize_args(v)
                for k, v in obj.__dict__.items()
                if not k.startswith("_")
            },
        }
    # For paths, bytes, and other types
    return str(obj)


def log_prompt_to_console(
    prompt: str,
    response: str | None = None,
    model: str = "unknown",
    component: str = "unknown",
):
    """
    Simple console logging for prompts when LangSmith is not available.

    Useful for local development and debugging.
    """
    timestamp = datetime.now(UTC).isoformat()
    print(f"\n{'=' * 80}")
    print(f"[{timestamp}] LLM Call - {component} ({model})")
    print(f"{'=' * 80}")
    print(f"PROMPT:\n{prompt[:500]}{'...' if len(prompt) > 500 else ''}")
    if response:
        print(f"\nRESPONSE:\n{response[:500]}{'...' if len(response) > 500 else ''}")
    print(f"{'=' * 80}\n")


# Export convenience functions
__all__ = [
    "TracedAnthropicClient",
    "TracedMessages",
    "trace_function",
    "trace_chain",
    "trace_tool",
    "trace_span",
    "is_tracing_enabled",
    "get_langsmith_client",
    "log_prompt_to_console",
    "LANGSMITH_ENABLED",
    "LANGSMITH_PROJECT",
]
