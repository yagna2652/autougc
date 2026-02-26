"""
Prompt Trace API routes — browse, inspect, and compare prompt traces.

Endpoints:
- GET /prompts/traces          — list trace summaries (paginated, filterable)
- GET /prompts/traces/{id}     — full trace detail
- GET /prompts/templates       — all template versions with run counts
- GET /prompts/compare         — side-by-side comparison of two traces
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.prompt_store import get_prompt_store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/prompts/traces")
async def list_traces(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    template_version: Optional[int] = Query(None),
    job_id: Optional[str] = Query(None),
):
    """Return paginated trace summaries."""
    store = get_prompt_store()
    traces = store.list_traces(
        limit=limit,
        offset=offset,
        template_version=template_version,
        job_id=job_id,
    )
    return {"traces": traces, "limit": limit, "offset": offset}


@router.get("/prompts/templates")
async def list_templates():
    """Return all template versions with run counts."""
    store = get_prompt_store()
    versions = store.get_template_versions()
    return {"templates": versions}


@router.get("/prompts/compare")
async def compare_traces(
    a: str = Query(..., description="First trace ID"),
    b: str = Query(..., description="Second trace ID"),
):
    """Return two full traces side by side for comparison."""
    store = get_prompt_store()
    result = store.compare_traces(a, b)
    if not result:
        raise HTTPException(status_code=404, detail="One or both traces not found")
    return result


@router.get("/prompts/traces/{trace_id}")
async def get_trace(trace_id: str):
    """Return full trace detail."""
    store = get_prompt_store()
    trace = store.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace
