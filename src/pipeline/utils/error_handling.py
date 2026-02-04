"""
Error Handling Utilities - Consistent error handling for pipeline nodes.

Provides helper functions and a context manager for handling errors
in pipeline nodes with consistent logging and return value formatting.
"""

import logging
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, TypeVar

import anthropic

logger = logging.getLogger(__name__)

# Type variable for generic function signatures
F = TypeVar("F", bound=Callable[..., dict[str, Any]])


def build_error_result(
    error: Exception | str,
    output_fields: dict[str, Any],
    current_step: str | None = None,
    include_error_field: bool = True,
    context: str = "operation",
) -> dict[str, Any]:
    """
    Build a consistent error result dictionary for node returns.

    Args:
        error: The exception or error message
        output_fields: Default values for output fields (e.g., {"video_analysis": {}})
        current_step: Optional step name to include
        include_error_field: Whether to include 'error' field in result
        context: Description for logging (e.g., "video analysis", "classification")

    Returns:
        Dictionary with error information and default output values
    """
    error_msg = str(error) if isinstance(error, Exception) else error

    result = dict(output_fields)

    if include_error_field:
        result["error"] = error_msg

    if current_step:
        result["current_step"] = current_step

    return result


def handle_api_error(
    error: anthropic.APIError,
    output_fields: dict[str, Any],
    current_step: str | None = None,
    context: str = "API call",
) -> dict[str, Any]:
    """
    Handle Anthropic API errors with consistent logging and return format.

    Args:
        error: The Anthropic API error
        output_fields: Default values for output fields
        current_step: Optional step name
        context: Description for logging

    Returns:
        Error result dictionary
    """
    logger.error(f"Claude API error during {context}: {error}")
    return build_error_result(
        error=f"Claude API error: {str(error)}",
        output_fields=output_fields,
        current_step=current_step,
        context=context,
    )


def handle_unexpected_error(
    error: Exception,
    output_fields: dict[str, Any],
    current_step: str | None = None,
    context: str = "operation",
) -> dict[str, Any]:
    """
    Handle unexpected errors with consistent logging and return format.

    Args:
        error: The unexpected exception
        output_fields: Default values for output fields
        current_step: Optional step name
        context: Description for logging

    Returns:
        Error result dictionary
    """
    logger.exception(f"Unexpected error during {context}")
    return build_error_result(
        error=str(error),
        output_fields=output_fields,
        current_step=current_step,
        context=context,
    )


@contextmanager
def node_error_handler(
    output_fields: dict[str, Any],
    current_step: str | None = None,
    context: str = "operation",
):
    """
    Context manager for handling errors in pipeline nodes.

    Usage:
        with node_error_handler(
            output_fields={"video_analysis": {}},
            current_step="analysis_failed",
            context="video analysis"
        ) as error_result:
            # ... do work ...
            # If an exception occurs, error_result.value will be set

    Args:
        output_fields: Default values for output fields on error
        current_step: Step name to set on error
        context: Description for logging

    Yields:
        ErrorResult container that will hold the error result if an exception occurs
    """

    class ErrorResult:
        def __init__(self):
            self.value: dict[str, Any] | None = None
            self.had_error = False

    result = ErrorResult()

    try:
        yield result
    except anthropic.APIError as e:
        result.value = handle_api_error(e, output_fields, current_step, context)
        result.had_error = True
    except Exception as e:
        result.value = handle_unexpected_error(e, output_fields, current_step, context)
        result.had_error = True


def with_error_handling(
    output_fields: dict[str, Any],
    current_step: str | None = None,
    context: str = "operation",
) -> Callable[[F], F]:
    """
    Decorator for adding error handling to pipeline node functions.

    Note: This decorator catches errors and returns a default result.
    Use only when you want automatic error handling with fixed defaults.

    For nodes with dynamic fallbacks (like analyze_product which uses
    existing_description), use the context manager or try/except instead.

    Usage:
        @with_error_handling(
            output_fields={"video_prompt": "", "suggested_script": ""},
            current_step="prompt_failed",
            context="prompt generation"
        )
        def generate_prompt_node(state: dict[str, Any]) -> dict[str, Any]:
            ...

    Args:
        output_fields: Default values for output fields on error
        current_step: Step name to set on error
        context: Description for logging

    Returns:
        Decorated function with error handling
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs) -> dict[str, Any]:
            try:
                return func(*args, **kwargs)
            except anthropic.APIError as e:
                return handle_api_error(e, output_fields, current_step, context)
            except Exception as e:
                return handle_unexpected_error(e, output_fields, current_step, context)

        return wrapper  # type: ignore

    return decorator
