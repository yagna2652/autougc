"""
Validate Prompt Node - Pre-generation quality gate for video prompts.

Evaluates the video prompt against 5 quality criteria that cause video model
artifacts (glitchy/melty output), then auto-fixes if high-severity issues found.

Criteria:
1. Spatial Anchoring — grip geometry must define a static reference frame
2. Beat Pacing — one primary action per time window, sequential not simultaneous
3. Anatomical Precision — [body part] [verb] [object surface], no dangling modifiers
4. Language Register — concrete/physical verbs only, no poetic/metaphorical phrases
5. Product Constraints — no conflicts with mechanics rules

This node never sets 'error' — it's a best-effort gate, not a hard stop.
"""

import json
import logging
import time
from typing import Any

from src.pipeline.utils import get_openrouter_client, parse_json_response
from src.prompt_store import get_prompt_store
from src.tracing import trace_span

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — stable rubric for video prompt quality review (~450 tokens)
# ---------------------------------------------------------------------------
VALIDATION_SYSTEM_PROMPT = """You are a video prompt quality reviewer. Your job is to evaluate prompts that will be sent to AI video generation models (Sora, Kling). These models interpret text literally and produce glitchy, melty output when the prompt has structural defects.

Evaluate the prompt against these 5 criteria:

1. **spatial_anchoring** — Every moving object needs a static reference frame. Is grip geometry explicit? Could the model infer hand position from text alone?
   FAIL: "hand interacts with device" (no anchor)
   PASS: "right hand wraps around the body, thumb braced on the left edge, index finger hovering over the top-left keycap"

2. **beat_pacing** — One primary action per time window. Beats must be sequential with timing, not overloaded simultaneous actions.
   FAIL: "finger presses key while thumb slides across and wrist rotates" (3 simultaneous actions)
   PASS: "Beat 1 (0-3s): index finger plunges the top-left keycap. Beat 2 (3-6s): thumb sweeps across the row."

3. **anatomical_precision** — Every sentence must be parseable as [body part] [verb] [object surface]. No dangling modifiers or ambiguous subject-action pairings.
   FAIL: "finger sinks into housing" (finger sinks into the housing? or keycap sinks?)
   PASS: "index fingertip presses the keycap flat surface, keycap sinks 2mm into housing"

4. **language_register** — Every verb must be concrete and physical. No poetic or metaphorical language.
   FAIL: "fingers dance playfully across the keys", "a flutter of motion"
   PASS: "index finger taps the keycap, keycap plunges downward 2mm, springs back up"

5. **product_constraint** — No conflicts with the product's physical mechanics rules.
   FAIL: Prompt shows pressing 3 keys simultaneously when mechanics say "only one key at a time"
   PASS: Actions match stated mechanics rules exactly

Respond with ONLY valid JSON:
{
  "passed": true/false,
  "issues": [
    {
      "category": "spatial_anchoring|beat_pacing|anatomical_precision|language_register|product_constraint",
      "severity": "high|medium|low",
      "description": "what's wrong",
      "location": "the problematic phrase or sentence"
    }
  ]
}

Set passed=false if ANY high-severity issue exists. Medium/low issues are informational only."""


def validate_prompt_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Validate video prompt quality and auto-fix if high-severity issues found.

    Phase 1: Evaluate prompt against 5 quality criteria
    Phase 2 (if needed): Rewrite fixing ONLY the listed issues

    Never sets 'error' — best-effort gate that skips gracefully on any failure.

    Args:
        state: Pipeline state with 'video_prompt', 'product_mechanics', 'config'

    Returns:
        State update with 'prompt_validation' and optionally rewritten 'video_prompt'
    """
    video_prompt = state.get("video_prompt", "")
    product_mechanics = state.get("product_mechanics", "")

    # Skip if no prompt to validate
    if not video_prompt or not video_prompt.strip():
        logger.warning("validate_prompt: skipping — empty video_prompt")
        return {
            "prompt_validation": {"status": "skipped", "reason": "empty_video_prompt"},
            "current_step": "prompt_validated",
        }

    # Skip if no mechanics to validate against
    if not product_mechanics or not product_mechanics.strip():
        logger.warning("validate_prompt: skipping — empty product_mechanics")
        return {
            "prompt_validation": {"status": "skipped", "reason": "empty_product_mechanics"},
            "current_step": "prompt_validated",
        }

    # Get LLM client
    client, model, client_error = get_openrouter_client(
        state, trace_name="validate_prompt", model_type="text"
    )
    if client_error or client is None:
        logger.warning(f"validate_prompt: skipping — LLM client unavailable: {client_error}")
        return {
            "prompt_validation": {"status": "skipped", "reason": f"llm_unavailable: {client_error}"},
            "current_step": "prompt_validated",
        }

    try:
        with trace_span(
            "validate_prompt",
            run_type="chain",
            inputs={
                "video_prompt": video_prompt[:200],
                "product_mechanics": product_mechanics[:200],
                "model": model,
            },
        ) as outer:
            # --- Phase 1: Evaluate prompt quality ---
            phase1_content = _build_phase1_content(video_prompt, product_mechanics)

            with trace_span(
                "validate_prompt.evaluate",
                run_type="llm",
                inputs={
                    "system_prompt": VALIDATION_SYSTEM_PROMPT[:200],
                    "user_content": phase1_content[:200],
                    "model": model,
                },
            ) as p1_span:
                logger.info(f"    ↳ Phase 1: Evaluating prompt quality ({model})...")
                t0 = time.time()
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": VALIDATION_SYSTEM_PROMPT},
                        {"role": "user", "content": phase1_content},
                    ],
                )
                phase1_elapsed = time.time() - t0

                # Extract Phase 1 token usage
                phase1_token_usage = None
                if hasattr(response, "usage") and response.usage:
                    phase1_token_usage = {
                        "input_tokens": getattr(response.usage, "prompt_tokens", 0) or 0,
                        "output_tokens": getattr(response.usage, "completion_tokens", 0) or 0,
                    }

                # Parse Phase 1 response
                if not response.choices or not response.choices[0].message:
                    p1_span.set_outputs({"error": "no_response"})
                    logger.warning("validate_prompt: skipping — no Phase 1 response")
                    return {
                        "prompt_validation": {"status": "skipped", "reason": "no_phase1_response"},
                        "current_step": "prompt_validated",
                    }

                response_text = response.choices[0].message.content or ""
                result = parse_json_response(response_text, context="prompt validation")

                if result is None:
                    p1_span.set_outputs({"error": "unparseable_response"})
                    logger.warning("validate_prompt: skipping — unparseable Phase 1 response")
                    return {
                        "prompt_validation": {"status": "skipped", "reason": "unparseable_phase1"},
                        "current_step": "prompt_validated",
                    }

                passed = result.get("passed", True)
                issues = result.get("issues", [])

                p1_span.set_outputs({
                    "passed": passed,
                    "issues_count": len(issues),
                    "latency_ms": int(phase1_elapsed * 1000),
                    "token_usage": phase1_token_usage,
                })

            logger.info(f"    ↳ Phase 1 result: passed={passed}, issues={len(issues)} ({phase1_elapsed:.1f}s)")
            for issue in issues:
                logger.info(f"      - [{issue.get('severity', '?')}] {issue.get('category', '?')}: {issue.get('description', '')[:80]}")

            # If passed or no high-severity issues, use prompt as-is
            if passed or not _has_high_severity(issues):
                logger.info("    ↳ Prompt passed validation — using as-is")

                # Save to PromptStore (non-fatal)
                trace_id = None
                try:
                    store = get_prompt_store()
                    trace_id = store.save_trace(
                        template_text=VALIDATION_SYSTEM_PROMPT,
                        assembled_prompt=phase1_content,
                        model=model,
                        inputs_snapshot={
                            "video_prompt": video_prompt,
                            "product_mechanics": product_mechanics,
                        },
                        job_id=state.get("job_id"),
                        raw_response=response_text,
                        processed_output={
                            "passed": True,
                            "issues": issues,
                            "rewritten": False,
                            "rewritten_prompt": None,
                        },
                        token_usage=phase1_token_usage,
                        latency_ms=int(phase1_elapsed * 1000),
                    )
                    logger.info(f"    ↳ Trace saved: {trace_id[:8]}...")
                except Exception as trace_err:
                    logger.warning(f"    ↳ Trace storage failed (non-fatal): {trace_err}")

                outer.set_outputs({"passed": True, "issues_count": len(issues), "trace_id": trace_id})
                return {
                    "prompt_validation": {
                        "passed": True,
                        "issues": issues,
                        "phase1_latency_ms": int(phase1_elapsed * 1000),
                        "trace_id": trace_id,
                    },
                    "current_step": "prompt_validated",
                }

            # --- Phase 2: Rewrite to fix high-severity issues ---
            phase2_content = _build_phase2_content(video_prompt, issues, product_mechanics)

            with trace_span(
                "validate_prompt.rewrite",
                run_type="llm",
                inputs={
                    "user_content": phase2_content[:200],
                    "model": model,
                },
            ) as p2_span:
                logger.info(f"    ↳ Phase 2: Rewriting prompt to fix {sum(1 for i in issues if i.get('severity') == 'high')} high-severity issues...")
                t1 = time.time()
                rewrite_response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a video prompt editor. Rewrite the prompt fixing ONLY the listed issues. Preserve everything else exactly. Return ONLY the rewritten prompt text, no JSON, no explanation."},
                        {"role": "user", "content": phase2_content},
                    ],
                )
                phase2_elapsed = time.time() - t1

                # Extract Phase 2 token usage
                phase2_token_usage = None
                if hasattr(rewrite_response, "usage") and rewrite_response.usage:
                    phase2_token_usage = {
                        "input_tokens": getattr(rewrite_response.usage, "prompt_tokens", 0) or 0,
                        "output_tokens": getattr(rewrite_response.usage, "completion_tokens", 0) or 0,
                    }

                # Parse Phase 2 response
                if not rewrite_response.choices or not rewrite_response.choices[0].message:
                    p2_span.set_outputs({"error": "no_response", "latency_ms": int(phase2_elapsed * 1000)})
                    logger.warning("validate_prompt: Phase 2 failed — keeping original")
                    return {
                        "prompt_validation": {
                            "passed": False,
                            "issues": issues,
                            "original_prompt": video_prompt,
                            "rewrite_failed": True,
                            "phase1_latency_ms": int(phase1_elapsed * 1000),
                        },
                        "current_step": "prompt_validated",
                    }

                rewritten = (rewrite_response.choices[0].message.content or "").strip()

                # Validate rewrite isn't empty or too short
                if not rewritten or len(rewritten) < 50:
                    p2_span.set_outputs({"error": "too_short", "length": len(rewritten), "latency_ms": int(phase2_elapsed * 1000)})
                    logger.warning(f"validate_prompt: Phase 2 rewrite too short ({len(rewritten)} chars) — keeping original")
                    return {
                        "prompt_validation": {
                            "passed": False,
                            "issues": issues,
                            "original_prompt": video_prompt,
                            "rewrite_failed": True,
                            "phase1_latency_ms": int(phase1_elapsed * 1000),
                            "phase2_latency_ms": int(phase2_elapsed * 1000),
                        },
                        "current_step": "prompt_validated",
                    }

                p2_span.set_outputs({
                    "rewritten_prompt_length": len(rewritten),
                    "latency_ms": int(phase2_elapsed * 1000),
                    "token_usage": phase2_token_usage,
                })

            logger.info(f"    ↳ Phase 2 rewrite: {len(rewritten)} chars ({phase2_elapsed:.1f}s)")
            logger.info(f"    ↳ Rewritten preview: {rewritten[:100]}...")

            # Sum Phase 1 + Phase 2 token usage
            total_token_usage = None
            if phase1_token_usage or phase2_token_usage:
                p1 = phase1_token_usage or {"input_tokens": 0, "output_tokens": 0}
                p2 = phase2_token_usage or {"input_tokens": 0, "output_tokens": 0}
                total_token_usage = {
                    "input_tokens": p1["input_tokens"] + p2["input_tokens"],
                    "output_tokens": p1["output_tokens"] + p2["output_tokens"],
                }
            total_latency_ms = int((phase1_elapsed + phase2_elapsed) * 1000)

            # Save to PromptStore (non-fatal)
            trace_id = None
            try:
                store = get_prompt_store()
                trace_id = store.save_trace(
                    template_text=VALIDATION_SYSTEM_PROMPT,
                    assembled_prompt=phase1_content,
                    model=model,
                    inputs_snapshot={
                        "video_prompt": video_prompt,
                        "product_mechanics": product_mechanics,
                    },
                    job_id=state.get("job_id"),
                    raw_response=response_text,
                    processed_output={
                        "passed": False,
                        "issues": issues,
                        "rewritten": True,
                        "rewritten_prompt": rewritten,
                    },
                    token_usage=total_token_usage,
                    latency_ms=total_latency_ms,
                )
                logger.info(f"    ↳ Trace saved: {trace_id[:8]}...")
            except Exception as trace_err:
                logger.warning(f"    ↳ Trace storage failed (non-fatal): {trace_err}")

            outer.set_outputs({"passed": False, "rewritten": True, "trace_id": trace_id})
            return {
                "video_prompt": rewritten,
                "prompt_validation": {
                    "passed": False,
                    "issues": issues,
                    "original_prompt": video_prompt,
                    "rewritten": True,
                    "phase1_latency_ms": int(phase1_elapsed * 1000),
                    "phase2_latency_ms": int(phase2_elapsed * 1000),
                    "trace_id": trace_id,
                },
                "current_step": "prompt_validated",
            }

    except Exception as e:
        logger.warning(f"validate_prompt: skipping due to exception — {e}")
        return {
            "prompt_validation": {"status": "skipped", "reason": f"exception: {e}"},
            "current_step": "prompt_validated",
        }


def _build_phase1_content(video_prompt: str, product_mechanics: str) -> str:
    """Build the Phase 1 user message for prompt evaluation."""
    return f"""Evaluate this video generation prompt for quality defects.

## VIDEO PROMPT TO EVALUATE
{video_prompt}

## PRODUCT MECHANICS RULES (for constraint checking)
{product_mechanics}

Check all 5 criteria and return your JSON assessment."""


def _build_phase2_content(
    video_prompt: str, issues: list[dict], product_mechanics: str
) -> str:
    """Build the Phase 2 user message for prompt rewriting."""
    issues_text = "\n".join(
        f"- [{i.get('severity', '?')}] {i.get('category', '?')}: {i.get('description', '')} (location: \"{i.get('location', '')}\")"
        for i in issues
        if i.get("severity") == "high"
    )

    return f"""Rewrite this video prompt, fixing ONLY the high-severity issues listed below.
Preserve everything else (structure, timing, beats, style) exactly as-is.

## ORIGINAL PROMPT
{video_prompt}

## HIGH-SEVERITY ISSUES TO FIX
{issues_text}

## PRODUCT MECHANICS (for reference)
{product_mechanics}

Return ONLY the rewritten prompt. No JSON, no explanation, no preamble."""


def _has_high_severity(issues: list[dict]) -> bool:
    """Check if any issue has high severity."""
    return any(i.get("severity") == "high" for i in issues)
