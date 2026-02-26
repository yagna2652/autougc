# Observability — Seeing Every Prompt in Real Time

How to run the pipeline and inspect every LLM prompt, response, token count, and latency as it happens.

---

## Quick Start (3 commands)

```bash
# 1. Start the Python API server
cd ~/Desktop/autougc2.0
source .venv/bin/activate
uvicorn api.server:app --reload --port 8000

# 2. In another terminal — start the Next.js frontend
cd ~/Desktop/autougc2.0/web
npm run dev

# 3. Open the dashboard
open http://localhost:3000
```

Trigger a run from the UI (paste a TikTok URL → click Start), then watch the SSE events flow through each node in real time.

---

## What Gets Traced

Two nodes now save full LLM traces to the local SQLite store (`data/prompts.db`):

| Node | LLM Calls | What's Captured |
|------|-----------|-----------------|
| `generate_prompt` | 1 call (vision + text) | Full assembled prompt, raw JSON response, video_prompt/script/scene outputs, token usage, latency, template version |
| `validate_prompt` | 1-2 calls (evaluate, then rewrite if needed) | System prompt, evaluation content, Phase 1 JSON result, Phase 2 rewrite (if triggered), summed token usage, total latency, template version |

Every trace includes:
- **`trace_id`** — UUID, returned in the API response and SSE events
- **`template_hash`** — SHA256 of the system prompt; auto-bumps version when you edit it
- **`assembled_prompt`** — the exact text sent to the LLM
- **`raw_response`** — the exact text received back
- **`processed_output`** — parsed/structured result
- **`token_usage`** — `{input_tokens, output_tokens}` from OpenRouter
- **`latency_ms`** — wall-clock time for the LLM call(s)
- **`inputs_snapshot`** — the pipeline state that fed into the prompt

---

## 3 Ways to See Traces

### 1. Real-Time via SSE (Frontend Dashboard)

The dashboard at `http://localhost:3000` streams events as each pipeline node runs:

- **`node_start`** → spinner appears on node
- **`node_done`** → node output rendered in the detail panel (right sidebar)

For `validate_prompt`, the SSE `node_done` payload includes:
```json
{
  "prompt_validation": {
    "passed": false,
    "issues": [...],
    "original_prompt": "...",
    "rewritten": true,
    "phase1_latency_ms": 2300,
    "phase2_latency_ms": 1800,
    "trace_id": "a1b2c3d4-..."
  },
  "video_prompt": "the rewritten prompt (if rewrite happened)"
}
```

You can also watch the raw SSE stream with curl:
```bash
# Start a job
JOB_ID=$(curl -s -X POST http://localhost:8000/api/v1/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://www.tiktok.com/@user/video/123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

# Stream events in real time
curl -N http://localhost:8000/api/v1/pipeline/stream/$JOB_ID
```

### 2. Trace API (curl / Postman)

Query the local trace store via REST:

```bash
# List recent traces (newest first)
curl http://localhost:8000/api/v1/prompts/traces?limit=10 | python3 -m json.tool

# Get full trace by ID (includes assembled_prompt + raw_response)
curl http://localhost:8000/api/v1/prompts/traces/<trace_id> | python3 -m json.tool

# List all template versions (see when prompt instructions changed)
curl http://localhost:8000/api/v1/prompts/templates | python3 -m json.tool

# Compare two traces side by side
curl "http://localhost:8000/api/v1/prompts/compare?a=<id1>&b=<id2>" | python3 -m json.tool

# Find trace for a specific job
curl "http://localhost:8000/api/v1/prompts/traces?job_id=<job_id>" | python3 -m json.tool
```

### 3. Direct SQLite (no server needed)

The database is a plain SQLite file. Query it directly:

```bash
# Latest 5 traces with key info
sqlite3 -header -column data/prompts.db \
  "SELECT trace_id, job_id, model, latency_ms, created_at
   FROM prompt_traces ORDER BY created_at DESC LIMIT 5"

# See the full prompt that was sent to the LLM
sqlite3 data/prompts.db \
  "SELECT assembled_prompt FROM prompt_traces
   WHERE trace_id = '<trace_id>'"

# See the raw LLM response
sqlite3 data/prompts.db \
  "SELECT raw_response FROM prompt_traces
   WHERE trace_id = '<trace_id>'"

# See parsed output (JSON)
sqlite3 data/prompts.db \
  "SELECT processed_output FROM prompt_traces
   WHERE trace_id = '<trace_id>'"

# Token usage across all runs
sqlite3 -header -column data/prompts.db \
  "SELECT model,
          COUNT(*) as runs,
          AVG(latency_ms) as avg_latency,
          SUM(json_extract(token_usage, '$.input_tokens')) as total_input,
          SUM(json_extract(token_usage, '$.output_tokens')) as total_output
   FROM prompt_traces
   GROUP BY model"

# Template version history
sqlite3 -header -column data/prompts.db \
  "SELECT tv.version_number, tv.first_seen, COUNT(t.trace_id) as runs
   FROM template_versions tv
   LEFT JOIN prompt_traces t ON tv.hash = t.template_hash
   GROUP BY tv.hash ORDER BY tv.version_number"

# validate_prompt traces specifically (filter by template hash)
sqlite3 -header -column data/prompts.db \
  "SELECT t.trace_id, t.latency_ms,
          json_extract(t.processed_output, '$.passed') as passed,
          json_extract(t.processed_output, '$.rewritten') as rewritten
   FROM prompt_traces t
   WHERE json_extract(t.inputs_snapshot, '$.video_prompt') IS NOT NULL
     AND json_extract(t.inputs_snapshot, '$.product_mechanics') IS NOT NULL
   ORDER BY t.created_at DESC LIMIT 10"
```

---

## LangSmith (Cloud Tracing — Optional)

LangSmith tracing is built in but disabled by default (the pipeline passes large base64 images that exceed LangSmith's payload limit). When enabled, `validate_prompt` produces a nested trace hierarchy:

```
validate_prompt (chain)
├── validate_prompt.evaluate (llm)  ← Phase 1: quality check
└── validate_prompt.rewrite (llm)   ← Phase 2: auto-fix (only if needed)
```

To enable:
```bash
# Add to .env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...  # get from smith.langchain.com
LANGCHAIN_PROJECT=autougc-pipeline
```

Then view traces at https://smith.langchain.com → your project.

**Note:** The `trace_span()` calls in `validate_prompt` are a no-op when LangSmith is disabled — zero overhead.

---

## Template Versioning

Both `generate_prompt` and `validate_prompt` auto-version their system prompts:

- The system prompt text is SHA256-hashed
- First time a new hash appears → version number auto-increments (v1, v2, v3...)
- Editing `VALIDATION_SYSTEM_PROMPT` in `validate_prompt.py` bumps the version
- Editing product config or video prompts does NOT bump it (those go in `inputs_snapshot`)

This lets you compare outputs across prompt instruction changes:
```bash
# "Did my v4 prompt produce better validations than v3?"
sqlite3 -header -column data/prompts.db \
  "SELECT tv.version_number,
          COUNT(*) as runs,
          AVG(t.latency_ms) as avg_latency,
          SUM(CASE WHEN json_extract(t.processed_output, '$.passed') = 1 THEN 1 ELSE 0 END) as passed,
          SUM(CASE WHEN json_extract(t.processed_output, '$.rewritten') = 1 THEN 1 ELSE 0 END) as rewritten
   FROM prompt_traces t
   JOIN template_versions tv ON t.template_hash = tv.hash
   GROUP BY tv.version_number
   ORDER BY tv.version_number"
```

---

## Environment Setup

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | Powers vision analysis + prompt generation + validation |
| `FAL_KEY` | Yes (for video gen) | Powers scene image + video generation |
| `API_KEY` | No | API auth key (dev mode works without it) |
| `LANGCHAIN_TRACING_V2` | No | Set to `true` to enable LangSmith |
| `LANGCHAIN_API_KEY` | No | LangSmith API key |
| `LANGCHAIN_PROJECT` | No | LangSmith project name (default: `autougc-pipeline`) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Pipeline Run                                                │
│                                                              │
│  download_video → extract_frames → analyze_video             │
│       → generate_prompt ──┐    → validate_prompt ──┐         │
│                           │                        │         │
│                      save_trace()              save_trace()  │
│                           │                        │         │
│                           ▼                        ▼         │
│                    ┌─────────────┐                            │
│                    │ prompts.db  │  ← SQLite (always on)     │
│                    └─────────────┘                            │
│                           │                                  │
│                    ┌─────────────┐                            │
│                    │  trace API  │  ← /api/v1/prompts/*      │
│                    └─────────────┘                            │
│                           │                                  │
│       → generate_scene_image → generate_video                │
│                                                              │
│  ──── SSE stream ──── node_start/node_done events ────►      │
│                                                              │
└──────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   ┌──────────┐                  ┌──────────────┐
   │ LangSmith│ (optional)       │  Frontend    │
   │ cloud    │                  │  dashboard   │
   └──────────┘                  └──────────────┘
```

---

## File Map

```
src/prompt_store.py                          ← SQLite store (PromptStore class)
src/tracing.py                               ← LangSmith wrappers (trace_span)
src/pipeline/nodes/generate_prompt.py        ← prompt gen + trace save
src/pipeline/nodes/validate_prompt.py        ← validation + trace save (NEW)
api/routes/prompts.py                        ← trace query API
api/routes/pipeline.py                       ← pipeline API + SSE streaming
web/src/components/prompt-trace-view.tsx      ← trace viewer component
web/src/components/detail-panel.tsx           ← node output panel
data/prompts.db                              ← SQLite DB (auto-created, gitignored)
```
