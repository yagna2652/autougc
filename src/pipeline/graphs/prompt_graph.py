"""
Prompt Graph - LangGraph workflow for prompt generation.

This graph orchestrates the prompt generation pipeline:
1. Analyze product (if product images provided)
2. Generate base prompt (using Claude)
3. Generate mechanics-enhanced prompt (using MechanicsEngine)
4. Finalize prompt (select best prompt for video generation)

The graph ensures that the mechanics-enhanced prompt is properly generated
and selected, fixing the plumbing issue where it was being ignored.
"""

import logging
from typing import Literal

from langgraph.graph import END, START, StateGraph

from src.pipeline.state import PipelineState

logger = logging.getLogger(__name__)


def should_analyze_product(
    state: PipelineState,
) -> Literal["analyze_product", "generate_base_prompt"]:
    """
    Check if product analysis is needed.

    Product analysis is run if product images are provided.

    Args:
        state: Current pipeline state

    Returns:
        Next node to execute
    """
    product_images = state.get("product_images", [])

    if product_images:
        logger.info(f"Product images found ({len(product_images)}), analyzing product")
        return "analyze_product"

    logger.info("No product images, skipping product analysis")
    return "generate_base_prompt"


def should_generate_mechanics(
    state: PipelineState,
) -> Literal["generate_mechanics", "finalize_prompt"]:
    """
    Check if mechanics generation should be run.

    Mechanics generation requires:
    - enable_mechanics config set to True
    - A valid blueprint from analysis

    Args:
        state: Current pipeline state

    Returns:
        Next node to execute
    """
    config = state.get("config", {})
    enable_mechanics = config.get("enable_mechanics", True)
    has_blueprint = bool(state.get("blueprint"))

    if enable_mechanics and has_blueprint:
        logger.info("Mechanics enabled and blueprint available, generating mechanics")
        return "generate_mechanics"

    if not enable_mechanics:
        logger.info("Mechanics generation disabled by config")
    elif not has_blueprint:
        logger.warning("No blueprint available for mechanics generation")

    return "finalize_prompt"


def check_base_prompt(
    state: PipelineState,
) -> Literal["check_mechanics", "finalize_prompt"]:
    """
    Check if base prompt was generated successfully.

    Args:
        state: Current pipeline state

    Returns:
        Next node to execute
    """
    base_prompt = state.get("base_prompt", "")

    if base_prompt and base_prompt.strip():
        return "check_mechanics"

    logger.warning("No base prompt generated, going to finalize")
    return "finalize_prompt"


def build_prompt_graph() -> StateGraph:
    """
    Build the prompt generation LangGraph workflow.

    The graph structure:
    ```
    START
      │
      ▼
    [should_analyze_product?]
      │
      ├── yes ──► analyze_product ──┐
      │                              │
      └── no ───────────────────────┤
                                     │
                                     ▼
                            generate_base_prompt
                                     │
                                     ▼
                           [should_generate_mechanics?]
                                     │
                      ├── yes ──► generate_mechanics ──┐
                      │                                 │
                      └── no ──────────────────────────┤
                                                        │
                                                        ▼
                                                 finalize_prompt
                                                        │
                                                        ▼
                                                       END
    ```

    Returns:
        Compiled LangGraph StateGraph
    """
    from src.pipeline.nodes import (
        analyze_product_node,
        finalize_prompt_node,
        generate_base_prompt_node,
        generate_mechanics_node,
    )

    # Create the graph with our state type
    graph = StateGraph(PipelineState)

    # Add all nodes
    graph.add_node("analyze_product", analyze_product_node)
    graph.add_node("generate_base_prompt", generate_base_prompt_node)
    graph.add_node("generate_mechanics", generate_mechanics_node)
    graph.add_node("finalize_prompt", finalize_prompt_node)

    # Define the flow

    # Start: Check if we need product analysis
    graph.add_conditional_edges(
        START,
        should_analyze_product,
        {
            "analyze_product": "analyze_product",
            "generate_base_prompt": "generate_base_prompt",
        },
    )

    # After product analysis, generate base prompt
    graph.add_edge("analyze_product", "generate_base_prompt")

    # After base prompt, check if we should generate mechanics
    graph.add_conditional_edges(
        "generate_base_prompt",
        should_generate_mechanics,
        {
            "generate_mechanics": "generate_mechanics",
            "finalize_prompt": "finalize_prompt",
        },
    )

    # After mechanics generation, finalize prompt
    graph.add_edge("generate_mechanics", "finalize_prompt")

    # Finalize prompt to end
    graph.add_edge("finalize_prompt", END)

    return graph


def compile_prompt_graph():
    """
    Build and compile the prompt graph.

    Returns:
        Compiled graph ready for execution
    """
    graph = build_prompt_graph()
    return graph.compile()


# Pre-compiled graph for direct import
prompt_graph = None


def get_prompt_graph():
    """
    Get the compiled prompt graph (lazy initialization).

    Returns:
        Compiled prompt graph
    """
    global prompt_graph
    if prompt_graph is None:
        prompt_graph = compile_prompt_graph()
    return prompt_graph
