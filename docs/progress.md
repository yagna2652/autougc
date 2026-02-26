# Local Prompt Versioning & Trace Store — Progress

## Goal

Build a local-first system to capture, version, and compare every prompt sent to the LLM during `generate_prompt` pipeline runs. Currently only the final output survives — the full assembled prompt, raw LLM response, template version, and inputs are all lost.

---

## What Exists Today (Before This Work)

- `src/tracing.py` — LangSmith wrappers for Anthropic client, but **unused** because `generate_prompt.py` uses OpenRouter via the OpenAI SDK. Requires external SaaS + API key.
- `generate_prompt_node()` in `src/pipeline/nodes/generate_prompt.py` — the main function that assembles a ~400-line prompt template, calls OpenRouter, parses the JSON response, post-processes it (clip ID resolution, negative constraints), and returns `{video_prompt, suggested_script, scene_description}`.
- `api/server.py` — FastAPI app with one router (`pipeline`).
- `api/routes/pipeline.py` — pipeline endpoints with SSE streaming. `_get_filtered_output()` controls what data flows to the frontend per node.
- `web/src/app/api/pipeline/route.ts` — Next.js proxy to Python backend (the only API proxy route).
- `web/src/components/detail-panel.tsx` — right sidebar showing node outputs. For `generate_prompt`, shows video_prompt, script, and scene_description.
- `web/src/components/run-history.tsx` — left sidebar with run history entries (status dot, video URL, model name, timestamp, scene thumbnail).

---

## What's Been Done So Far

### 1. `src/prompt_store.py` — CREATED (complete)

SQLite-backed store at `data/prompts.db`. Zero external dependencies.

**Two tables:**
- `template_versions` — `hash` (PK), `version_number`, `template_text`, `first_seen`
- `prompt_traces` — `trace_id` (PK), `job_id`, `template_hash` (FK), `assembled_prompt`, `model`, `inputs_snapshot` (JSON), `raw_response`, `processed_output` (JSON), `token_usage` (JSON), `latency_ms`, `created_at`

**Indexes:** `job_id`, `template_hash`, `created_at DESC`

**Class `PromptStore` methods:**
- `save_trace(...)` — records a trace, auto-creates template version if hash is new
- `get_trace(trace_id)` — full trace with template version number
- `list_traces(limit, offset, template_version?, job_id?)` — summaries only (no assembled_prompt/raw_response)
- `get_template_versions()` — all versions with run counts
- `compare_traces(id_a, id_b)` — two full traces side by side
- `get_trace_by_job(job_id)` — lookup trace by pipeline job ID

**Singleton:** `get_prompt_store()` lazily creates the global instance.

**Template versioning logic:** SHA256 hash of the static template text. New hash → auto-increment version number. Editing prompt instructions bumps version; changing product config doesn't.

### 2. `src/pipeline/nodes/generate_prompt.py` — PARTIALLY MODIFIED

**Added imports only** (no instrumentation logic yet):
```python
import json
import time
from src.prompt_store import get_prompt_store
```

The actual instrumentation (wrapping the LLM call with timing, capturing raw response, calling `save_trace()`, adding `trace_id` to return dict) has **not been done yet**.

### 3. `.gitignore` — MODIFIED

Added `data/` to gitignore so `data/prompts.db` doesn't get committed.

---

## What Remains

### Backend (Python)

**A. Instrument `generate_prompt.py`** — in `generate_prompt_node()`:
- Extract the static template skeleton (the f-string at lines 322-399 with placeholder markers instead of actual values) as a constant for hashing
- Wrap the `client.chat.completions.create()` call (line 89-92) with `time.time()` for latency
- After the call, extract `response.usage` for token counts
- Capture `response_text` (line 112) as the raw response
- After post-processing, call `get_prompt_store().save_trace()` with all captured data
- Add `trace_id` to the return dict (lines 150-155)
- Inputs snapshot = `{video_analysis, product_description, product_mechanics}`

**B. Create `api/routes/prompts.py`** — FastAPI router with endpoints:
- `GET /prompts/traces` — list traces (paginated, filterable by `template_version` query param)
- `GET /prompts/traces/{trace_id}` — full trace
- `GET /prompts/templates` — all template versions
- `GET /prompts/compare?a={id}&b={id}` — two traces side by side

**C. Register in `api/server.py`** — add:
```python
from api.routes.prompts import router as prompts_router
app.include_router(prompts_router, prefix="/api/v1", tags=["prompts"])
```

**D. Modify `api/routes/pipeline.py`** — in `_get_filtered_output()` (line 249-254), add `trace_id` to the `generate_prompt` case:
```python
elif node_name == "generate_prompt":
    return {
        "video_prompt": state_update.get("video_prompt"),
        "suggested_script": state_update.get("suggested_script"),
        "scene_description": state_update.get("scene_description"),
        "trace_id": state_update.get("trace_id"),
    }
```

### Frontend (TypeScript/React)

**E. Create `web/src/app/api/prompts/route.ts`** — Next.js proxy to `http://localhost:8000/api/v1/prompts/*`. Same pattern as `pipeline/route.ts`.

**F. Create `web/src/components/prompt-trace-view.tsx`** — renders a single trace:
- Template version badge (e.g. `v3`)
- Full assembled prompt in scrollable monospace box
- Inputs snapshot (video analysis, product description, mechanics)
- Raw LLM response vs processed output
- Token usage + latency stats

**G. Modify `web/src/components/detail-panel.tsx`** — in the `generate_prompt` section (lines 221-311):
- Add "View Full Trace" expandable section that fetches trace via `/api/prompts/traces/{trace_id}`
- Show the `PromptTraceView` component
- Add "Compare with..." dropdown listing other traces

**H. Modify `web/src/components/run-history.tsx`** — add a small `v3` badge next to the model name in each run entry.

---

## Open Question

Whether to also fix the existing `src/tracing.py` LangSmith integration to capture OpenRouter calls (for external observability alongside the local store), or just rely on the local store alone. This is independent of the above work and can be done later.

---

## Key File Paths

```
src/prompt_store.py                          — SQLite store (DONE)
src/pipeline/nodes/generate_prompt.py        — prompt generation node (imports added)
api/server.py                                — FastAPI app entry
api/routes/pipeline.py                       — pipeline API + SSE streaming
api/routes/prompts.py                        — (TO CREATE) trace API
web/src/app/api/pipeline/route.ts            — existing Next.js proxy
web/src/app/api/prompts/route.ts             — (TO CREATE) prompts proxy
web/src/components/detail-panel.tsx           — right panel (node outputs)
web/src/components/run-history.tsx            — left panel (run history)
web/src/components/prompt-trace-view.tsx      — (TO CREATE) trace renderer
web/src/types/pipeline.ts                    — TypeScript types
web/src/hooks/use-pipeline.ts                — pipeline state hook
web/src/lib/nodes.ts                         — node definitions
web/src/components/pipeline-app.tsx           — main app component
data/prompts.db                              — SQLite DB (gitignored, auto-created)
.gitignore                                   — updated with data/
```
