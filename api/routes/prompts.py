"""
Prompt versioning API routes.

CRUD for prompt versions, labels, and generation trace ratings.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

# Store will be set by server.py at startup
store = None


def get_store():
    if store is None:
        raise HTTPException(status_code=500, detail="PromptStore not initialized")
    return store


# ---------- Request models ----------


class SaveVersionRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    negative_prompt: str = Field(default="")
    name: str | None = None
    change_note: str | None = None
    model_config_data: dict | None = Field(default=None, alias="model_config")


class SetLabelRequest(BaseModel):
    name: str = Field(..., min_length=1)


class UpdateTraceRequest(BaseModel):
    rating: int | None = Field(default=None, ge=-1, le=1)
    notes: str | None = None


# ---------- Routes ----------


@router.get("/prompts")
async def list_versions(limit: int = 50, offset: int = 0):
    return get_store().list_versions(limit=limit, offset=offset)


@router.get("/prompts/{version_id}")
async def get_version(version_id: str):
    s = get_store()
    version = s.get_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    version["traces"] = s.get_traces(version_id)
    version["labels"] = s.get_labels_for_version(version_id)
    return version


@router.post("/prompts")
async def save_version(req: SaveVersionRequest):
    return get_store().save_version(
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        name=req.name,
        change_note=req.change_note,
        model_config=req.model_config_data,
    )


@router.post("/prompts/{version_id}/labels")
async def add_label(version_id: str, req: SetLabelRequest):
    s = get_store()
    version = s.get_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    s.set_label(req.name, version_id)
    return {"ok": True}


@router.delete("/prompts/{version_id}/labels/{label_name}")
async def remove_label(version_id: str, label_name: str):
    get_store().remove_label(label_name)
    return {"ok": True}


@router.put("/traces/{trace_id}")
async def update_trace(trace_id: str, req: UpdateTraceRequest):
    s = get_store()
    trace = s.get_trace(trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    kwargs = {}
    if req.rating is not None:
        kwargs["rating"] = req.rating
    if req.notes is not None:
        kwargs["notes"] = req.notes
    if kwargs:
        s.update_trace(trace_id, **kwargs)
    return {"ok": True}
