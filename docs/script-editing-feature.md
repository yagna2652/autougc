# AutoUGC: Script Editing Feature Design Document

## Context: What Already Exists

### Current Project Structure

```
autougc/
├── api/
│   ├── server.py                    # FastAPI app entry point
│   ├── routes/
│   │   └── pipeline.py              # API endpoints for pipeline jobs
│   └── video_downloader.py          # TikTok download helper
├── src/
│   ├── pipeline/
│   │   ├── state.py                 # PipelineState TypedDict definition
│   │   ├── graphs/
│   │   │   └── simple_pipeline.py   # LangGraph workflow definition
│   │   └── nodes/
│   │       ├── __init__.py          # Node exports
│   │       ├── download_video.py    # yt-dlp download node
│   │       ├── extract_frames.py    # FFmpeg frame extraction node
│   │       ├── analyze_video.py     # Claude Vision analysis node
│   │       ├── generate_prompt.py   # Claude prompt generation node
│   │       └── generate_video.py    # Fal.ai video generation node
│   ├── analyzer/
│   │   └── frame_extractor.py       # FFmpeg frame extraction helper
│   └── tracing.py                   # LangSmith observability wrapper
├── web/
│   └── src/
│       ├── app/
│       │   ├── page.tsx             # Main React page (single page app)
│       │   ├── layout.tsx           # Root layout
│       │   └── api/
│       │       └── pipeline/
│       │           └── route.ts     # Next.js API route (proxy to Python)
│       └── components/
│           └── ui/                  # Radix UI components
├── requirements.txt                 # Python dependencies (includes whisper)
└── .env                            # API keys (ANTHROPIC, FAL, OPENAI)
```

### Current Pipeline State (src/pipeline/state.py)

```python
class PipelineState(TypedDict, total=False):
    # Job tracking
    job_id: str
    status: str              # pending, running, completed, failed
    current_step: str
    error: str

    # Input
    video_url: str
    product_description: str
    product_images: list[str]

    # Config
    config: dict[str, Any]

    # Pipeline data (populated as we go)
    video_path: str          # Downloaded video file path
    frames: list[str]        # Extracted frame paths
    video_analysis: dict     # Claude Vision analysis result
    video_prompt: str        # Generated prompt for video API
    suggested_script: str    # Basic script (1-3 sentences, auto-generated)

    # Output
    generated_video_url: str
```

### Current Pipeline Flow (src/pipeline/graphs/simple_pipeline.py)

```python
# Current node sequence
graph.add_node("download_video", download_video_node)
graph.add_node("extract_frames", extract_frames_node)
graph.add_node("analyze_video", analyze_video_node)
graph.add_node("generate_prompt", generate_prompt_node)
graph.add_node("generate_video", generate_video_node)

# Current edges
graph.add_edge(START, "download_video")
graph.add_edge("download_video", "extract_frames")
graph.add_edge("extract_frames", "analyze_video")       # ← Will change
graph.add_edge("analyze_video", "generate_prompt")
graph.add_edge("generate_prompt", "generate_video")
graph.add_edge("generate_video", END)
```

### Current API Endpoints (api/routes/pipeline.py)

```python
POST /api/v1/pipeline/start           # Start new job
GET  /api/v1/pipeline/jobs/{job_id}   # Get job status
DELETE /api/v1/pipeline/jobs/{job_id} # Delete job
GET  /api/v1/pipeline/health          # Health check
```

### Current Frontend UI (web/src/app/page.tsx)

5 cards in sequence:
1. **Input Card** - TikTok URL, product description, model selector
2. **Status Card** - Shows current step + spinner
3. **Analysis Card** - Shows video_analysis JSON
4. **Prompt Card** - Shows video_prompt + suggested_script (read-only)
5. **Video Card** - Shows generated video + download button

**Current State Variables:**
```typescript
const [tiktokUrl, setTiktokUrl] = useState("");
const [productDescription, setProductDescription] = useState("");
const [videoModel, setVideoModel] = useState<"sora" | "kling">("sora");
const [status, setStatus] = useState<Status>("idle");
const [currentStep, setCurrentStep] = useState("");
const [jobId, setJobId] = useState<string | null>(null);
const [videoAnalysis, setVideoAnalysis] = useState<Record<string, unknown> | null>(null);
const [videoPrompt, setVideoPrompt] = useState("");
const [suggestedScript, setSuggestedScript] = useState("");
const [generatedVideoUrl, setGeneratedVideoUrl] = useState("");
```

### Current generate_prompt_node.py (Key Parts)

```python
def generate_prompt_node(state: dict[str, Any]) -> dict[str, Any]:
    video_analysis = state.get("video_analysis", {})
    product_description = state.get("product_description", "")

    # Claude prompt asks for JSON with:
    # - video_prompt: 150-250 word description for video AI
    # - script: 1-3 sentence casual script

    response = client.messages.create(
        model=model,
        max_tokens=1500,
        messages=[{"role": "user", "content": content}],
    )

    result = _parse_prompt_response(response_text)
    video_prompt = result.get("video_prompt", "")
    suggested_script = result.get("script", "")  # ← Currently auto-generated, no user input

    return {
        "video_prompt": video_prompt,
        "suggested_script": suggested_script,
        "current_step": "prompt_generated",
    }
```

### What Whisper Support Already Exists

In `requirements.txt`:
```
openai-whisper
```

In `.env` (already configured):
```
OPENAI_API_KEY=...        # Can use Whisper API
WHISPER_MODE=local        # "local" or "api"
```

The Whisper dependency exists but is **not used** in the current pipeline.

---

## Proposed Changes

### Goal

Allow users to:
1. See what was said in the original TikTok (transcription)
2. Edit the script before video generation
3. Have the edited script influence the generated video

### New Pipeline Flow

```
BEFORE:
download → extract_frames → analyze_video → generate_prompt → generate_video

AFTER:
download → extract_frames → transcribe_audio → analyze_video → [USER EDITS] → generate_prompt → generate_video
                                   ↑                                              ↑
                                  NEW                                         MODIFIED
```

---

## Specific Changes by File

### 1. CREATE: src/pipeline/nodes/transcribe_audio.py

**Purpose:** New node to transcribe TikTok audio using Whisper

```python
"""
Transcribe Audio Node - Extracts spoken content from TikTok video.

Uses OpenAI Whisper to transcribe what the person says in the video.
This provides the base script that users can then edit.
"""

import logging
import os
from typing import Any

import whisper

logger = logging.getLogger(__name__)


def transcribe_audio_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Transcribe audio from downloaded TikTok video.

    Args:
        state: Pipeline state with 'video_path'

    Returns:
        State update with 'transcribed_script'
    """
    video_path = state.get("video_path")

    if not video_path:
        logger.warning("No video path provided for transcription")
        return {
            "transcribed_script": "",
            "error": "No video path for transcription",
        }

    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return {
            "transcribed_script": "",
            "error": f"Video file not found: {video_path}",
        }

    logger.info(f"Transcribing audio from: {video_path}")

    try:
        # Load Whisper model
        # Options: "tiny", "base", "small", "medium", "large"
        # "base" balances speed and accuracy for short TikTok clips
        whisper_mode = os.getenv("WHISPER_MODE", "local")

        if whisper_mode == "api":
            # Use OpenAI Whisper API
            transcribed_text = _transcribe_with_api(video_path)
        else:
            # Use local Whisper model
            transcribed_text = _transcribe_with_local(video_path)

        logger.info(f"Transcription complete: {len(transcribed_text)} chars")

        return {
            "transcribed_script": transcribed_text.strip(),
            "current_step": "audio_transcribed",
        }

    except Exception as e:
        logger.exception("Error during transcription")
        return {
            "transcribed_script": "",
            "error": f"Transcription failed: {str(e)}",
        }


def _transcribe_with_local(video_path: str) -> str:
    """Transcribe using local Whisper model."""
    model = whisper.load_model("base")
    result = model.transcribe(video_path)
    return result["text"]


def _transcribe_with_api(video_path: str) -> str:
    """Transcribe using OpenAI Whisper API."""
    from openai import OpenAI

    client = OpenAI()

    with open(video_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )

    return response.text
```

### 2. MODIFY: src/pipeline/nodes/__init__.py

**Change:** Add export for new node

```python
# Current exports
from .download_video import download_video_node
from .extract_frames import extract_frames_node
from .analyze_video import analyze_video_node
from .generate_prompt import generate_prompt_node
from .generate_video import generate_video_node

# ADD THIS LINE:
from .transcribe_audio import transcribe_audio_node

__all__ = [
    "download_video_node",
    "extract_frames_node",
    "transcribe_audio_node",    # ADD THIS
    "analyze_video_node",
    "generate_prompt_node",
    "generate_video_node",
]
```

### 3. MODIFY: src/pipeline/state.py

**Change:** Add two new fields to PipelineState

```python
class PipelineState(TypedDict, total=False):
    # ... existing fields stay the same ...

    # ADD THESE TWO FIELDS:
    transcribed_script: str    # Original script extracted from TikTok audio
    edited_script: str         # User's edited version of the script


def create_initial_state(...) -> PipelineState:
    return PipelineState(
        # ... existing fields ...

        # ADD THESE:
        transcribed_script="",
        edited_script="",
    )
```

### 4. MODIFY: src/pipeline/graphs/simple_pipeline.py

**Change:** Insert transcribe_audio node into the graph

```python
from src.pipeline.nodes import (
    download_video_node,
    extract_frames_node,
    transcribe_audio_node,    # ADD THIS IMPORT
    analyze_video_node,
    generate_prompt_node,
    generate_video_node,
)

def create_simple_pipeline():
    # ... existing setup ...

    # Add nodes (ADD transcribe_audio)
    graph.add_node("download_video", download_video_node)
    graph.add_node("extract_frames", extract_frames_node)
    graph.add_node("transcribe_audio", transcribe_audio_node)    # ADD THIS
    graph.add_node("analyze_video", analyze_video_node)
    graph.add_node("generate_prompt", generate_prompt_node)
    graph.add_node("generate_video", generate_video_node)

    # Update edges
    graph.add_edge(START, "download_video")
    graph.add_edge("download_video", "extract_frames")
    graph.add_edge("extract_frames", "transcribe_audio")        # CHANGED (was analyze_video)
    graph.add_edge("transcribe_audio", "analyze_video")         # ADD THIS
    graph.add_edge("analyze_video", "generate_prompt")
    graph.add_edge("generate_prompt", "generate_video")
    graph.add_edge("generate_video", END)
```

### 5. MODIFY: src/pipeline/nodes/generate_prompt.py

**Change:** Use edited_script (or fallback to transcribed_script) in prompt

```python
def generate_prompt_node(state: dict[str, Any]) -> dict[str, Any]:
    video_analysis = state.get("video_analysis", {})
    product_description = state.get("product_description", "")
    product_images = state.get("product_images", [])

    # ADD THIS BLOCK:
    # Get script - prefer edited, fall back to transcribed, then empty
    edited_script = state.get("edited_script", "")
    transcribed_script = state.get("transcribed_script", "")
    script_to_use = edited_script or transcribed_script

    # ... existing API key check ...

    # MODIFY _build_prompt_request call to include script:
    content = _build_prompt_request(
        video_analysis,
        product_description,
        product_images,
        script_to_use,    # ADD THIS PARAMETER
    )

    # ... rest stays the same ...


def _build_prompt_request(
    video_analysis: dict[str, Any],
    product_description: str,
    product_images: list[str],
    script: str = "",    # ADD THIS PARAMETER
) -> list[dict[str, Any]]:
    # ... existing formatting ...

    # MODIFY the prompt to include the script:
    prompt = f"""You are an expert at creating prompts for AI video generation models.

I analyzed a TikTok video and extracted this information about its style:

{analysis_text}

{"Product to feature: " + product_description if product_description else "No specific product."}

{"The person in the video should appear to say something like: " + script if script else ""}

Your task: Create a detailed prompt for an AI video generator that will recreate this EXACT style.

CRITICAL REQUIREMENTS FOR REALISM:
1. iPhone front-facing camera look, NOT cinematic
2. Real skin with pores, texture, natural imperfections
3. Slight handheld shake, natural micro-movements
4. Natural indoor lighting
5. Real lived-in space
6. Genuine emotions
7. Looking at phone screen (like filming themselves)

Respond in JSON format:
{{
    "video_prompt": "A detailed 150-250 word prompt...",
    "script": "The exact script the person will say"
}}
"""
    # ... rest stays the same ...
```

### 6. MODIFY: api/routes/pipeline.py

**Change:** Add PATCH endpoint and update response model

```python
from pydantic import BaseModel

# ADD this request model:
class UpdateScriptRequest(BaseModel):
    edited_script: str


# MODIFY JobStatusResponse to include script fields:
class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    current_step: str
    error: str | None = None
    video_analysis: dict | None = None
    video_prompt: str = ""
    suggested_script: str = ""
    generated_video_url: str = ""
    transcribed_script: str = ""    # ADD THIS
    edited_script: str = ""         # ADD THIS


# ADD this new endpoint:
@router.patch("/jobs/{job_id}/script")
async def update_job_script(job_id: str, request: UpdateScriptRequest):
    """
    Update the edited script for a pipeline job.

    This allows users to modify the script before video generation.
    """
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update the job state with edited script
    job["state"]["edited_script"] = request.edited_script

    return {
        "job_id": job_id,
        "status": "script_updated",
        "edited_script": request.edited_script,
    }


# MODIFY get_job_status to return script fields:
@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> JobStatusResponse:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    state = job.get("state", {})

    return JobStatusResponse(
        job_id=job_id,
        status=job.get("status", "unknown"),
        current_step=state.get("current_step", ""),
        error=state.get("error"),
        video_analysis=state.get("video_analysis"),
        video_prompt=state.get("video_prompt", ""),
        suggested_script=state.get("suggested_script", ""),
        generated_video_url=state.get("generated_video_url", ""),
        transcribed_script=state.get("transcribed_script", ""),    # ADD THIS
        edited_script=state.get("edited_script", ""),              # ADD THIS
    )
```

### 7. MODIFY: web/src/app/page.tsx

**Change:** Add script editing UI and state

```typescript
// ADD these state variables (after existing ones):
const [transcribedScript, setTranscribedScript] = useState("");
const [editedScript, setEditedScript] = useState("");

// MODIFY the polling useEffect to capture transcribedScript:
useEffect(() => {
  // ... existing polling code ...

  if (data.status === "completed") {
    setStatus("completed");
    setVideoAnalysis(data.videoAnalysis);
    setVideoPrompt(data.videoPrompt);
    setSuggestedScript(data.suggestedScript);
    setGeneratedVideoUrl(data.generatedVideoUrl);

    // ADD THESE:
    setTranscribedScript(data.transcribedScript || "");
    setEditedScript(data.transcribedScript || "");  // Pre-fill with original
  }
}, [jobId, status]);

// ADD this handler for saving edited script:
const handleSaveScript = async () => {
  if (!jobId) return;

  try {
    await fetch("/api/pipeline", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: "update_script",
        jobId,
        editedScript,
      }),
    });
  } catch (err) {
    console.error("Failed to save script:", err);
  }
};

// ADD this new Card between Video Analysis and Generated Prompt cards:
{status === "completed" && videoAnalysis && (
  <Card className="mb-6">
    <CardHeader>
      <CardTitle>4. Script</CardTitle>
      <CardDescription>
        Edit the script while keeping the video style
      </CardDescription>
    </CardHeader>
    <CardContent className="space-y-4">
      {/* Original transcription */}
      <div>
        <Label className="text-sm text-gray-500">
          Original (from TikTok):
        </Label>
        <div className="bg-gray-100 dark:bg-gray-800 p-3 rounded-lg mt-1 italic text-sm">
          {transcribedScript || "(No speech detected in video)"}
        </div>
      </div>

      {/* Editable version */}
      <div>
        <Label htmlFor="edited-script">Your Version:</Label>
        <Textarea
          id="edited-script"
          value={editedScript}
          onChange={(e) => setEditedScript(e.target.value)}
          rows={4}
          className="mt-1"
          placeholder="Edit the script to change what the person says..."
        />
        <div className="flex justify-between text-sm text-gray-500 mt-1">
          <span>
            {editedScript.split(/\s+/).filter(Boolean).length} words
          </span>
          <span>
            ~{Math.ceil(editedScript.split(/\s+/).filter(Boolean).length / 2.5)}s
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <Button
          variant="outline"
          onClick={() => setEditedScript(transcribedScript)}
          disabled={editedScript === transcribedScript}
        >
          Reset to Original
        </Button>
        <Button onClick={handleSaveScript}>
          Save & Use This Script
        </Button>
      </div>
    </CardContent>
  </Card>
)}
```

### 8. MODIFY: web/src/app/api/pipeline/route.ts

**Change:** Add handler for update_script action

```typescript
// In the POST handler, ADD this case:

if (action === "update_script") {
  const { jobId, editedScript } = body;

  const res = await fetch(
    `${API_BASE_URL}/api/v1/pipeline/jobs/${jobId}/script`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ edited_script: editedScript }),
    }
  );

  const data = await res.json();
  return NextResponse.json(data);
}
```

---

## Summary of All Changes

| File | Action | What Changes |
|------|--------|--------------|
| `src/pipeline/nodes/transcribe_audio.py` | CREATE | New Whisper transcription node |
| `src/pipeline/nodes/__init__.py` | MODIFY | Add 1 import + 1 export |
| `src/pipeline/state.py` | MODIFY | Add 2 fields to TypedDict + initializer |
| `src/pipeline/graphs/simple_pipeline.py` | MODIFY | Add 1 node, change 1 edge, add 1 edge |
| `src/pipeline/nodes/generate_prompt.py` | MODIFY | Add script parameter, modify prompt |
| `api/routes/pipeline.py` | MODIFY | Add 1 endpoint, add 2 response fields |
| `web/src/app/page.tsx` | MODIFY | Add 2 state vars, 1 handler, 1 Card |
| `web/src/app/api/pipeline/route.ts` | MODIFY | Add 1 action handler |

**Total: 1 new file, 7 modified files**

---

## Testing Checklist

1. [ ] Run pipeline with TikTok that has speech → verify transcription appears
2. [ ] Run pipeline with TikTok that has only music → verify graceful handling
3. [ ] Edit script in UI → verify changes are saved
4. [ ] Generate video → verify edited script influences the result
5. [ ] Reset to original → verify button works
6. [ ] Word count / duration estimate → verify calculations are reasonable
