/**
 * Pipeline API Route - Simple proxy to Python backend.
 *
 * Endpoints:
 * - POST /api/pipeline (action: "start") - Start pipeline job
 * - POST /api/pipeline (action: "status") - Get job status
 */

import { NextRequest, NextResponse } from "next/server";
import type {
  StartPipelineRequest,
  StatusPipelineRequest,
  ResumePipelineRequest,
  PipelineRequest,
  PipelineResult,
  VideoAnalysisData,
} from "@/types/pipeline";

const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";
const API_KEY = process.env.API_KEY || "";
const START_REQUEST_TIMEOUT_MS = 210000; // 210s (~3.5 min)

export const maxDuration = 300; // 5 minutes

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (API_KEY) {
    headers["X-API-Key"] = API_KEY;
  }
  return headers;
}

export async function POST(request: NextRequest) {
  try {
    const body: PipelineRequest = await request.json();

    switch (body.action) {
      case "start":
        return handleStart(body);
      case "status":
        return handleStatus(body);
      case "resume":
        return handleResume(body as ResumePipelineRequest);
      default:
        return NextResponse.json(
          { error: "Invalid action. Use 'start', 'status', or 'resume'" },
          { status: 400 },
        );
    }
  } catch (error) {
    console.error("Pipeline API error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 },
    );
  }
}

async function handleStart(body: StartPipelineRequest): Promise<NextResponse> {
  const requestBody = {
    video_url: body.videoUrl,
    product_description: body.productDescription || "",
    product_mechanics: body.productMechanics || "",
    product_images: body.productImages || [],
    product_identity_pack: body.productIdentityPack,
    fal_key: (body as StartPipelineRequest & { falKey?: string }).falKey || undefined,
    config: {
      video_model: body.videoModel || "sora",
      use_identity_pack: body.useIdentityPack ?? false,
      use_tail_image: body.useTailImage ?? false,
      use_anchor_frames: body.useAnchorFrames ?? false,
      segment_duration: body.segmentDuration ?? 2,
    },
  };

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), START_REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${PYTHON_API_URL}/api/v1/pipeline/start`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify(requestBody),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || "Failed to start pipeline" },
        { status: response.status },
      );
    }

    return NextResponse.json({
      success: true,
      jobId: data.job_id,
      status: data.status,
      message: data.message,
    });
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error.name === "AbortError") {
      return NextResponse.json(
        { error: "Request timeout - backend took too long to respond" },
        { status: 504 },
      );
    }
    throw error;
  }
}

async function handleStatus(body: StatusPipelineRequest): Promise<NextResponse> {
  try {
    const response = await fetch(
      `${PYTHON_API_URL}/api/v1/pipeline/jobs/${body.jobId}`,
      { method: "GET", headers: getAuthHeaders() },
    );

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || "Failed to get job status" },
        { status: response.status },
      );
    }

    const result: Partial<PipelineResult> & { success: boolean } = {
      success: true,
      jobId: data.job_id,
      status: data.status,
      currentStep: data.current_step || "",
      error: data.error || null,
      videoAnalysis: (data.video_analysis || null) as VideoAnalysisData | null,
      videoPrompt: data.video_prompt || "",
      suggestedScript: data.suggested_script || "",
      sceneImageUrl: data.scene_image_url || "",
      generatedVideoUrl: data.generated_video_url || "",
    };

    return NextResponse.json(result);
  } catch {
    return NextResponse.json(
      { error: "Backend not reachable", status: "running", currentStep: "waiting" },
      { status: 502 },
    );
  }
}

async function handleResume(body: ResumePipelineRequest): Promise<NextResponse> {
  try {
    const requestBody: Record<string, unknown> = {};
    if (body.videoPrompt !== undefined) {
      requestBody.video_prompt = body.videoPrompt;
    }

    const response = await fetch(
      `${PYTHON_API_URL}/api/v1/pipeline/resume/${body.jobId}`,
      {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(requestBody),
      },
    );

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || "Failed to resume pipeline" },
        { status: response.status },
      );
    }

    return NextResponse.json({
      success: true,
      jobId: data.job_id,
      status: data.status,
      message: data.message,
    });
  } catch {
    return NextResponse.json(
      { error: "Backend not reachable" },
      { status: 502 },
    );
  }
}

export async function GET(request: NextRequest): Promise<Response> {
  const jobId = request.nextUrl.searchParams.get("jobId");

  // No jobId → health check
  if (!jobId) {
    try {
      const response = await fetch(`${PYTHON_API_URL}/api/v1/pipeline/health`);
      const data = await response.json();
      return NextResponse.json({ status: "ok", backend: data });
    } catch {
      return NextResponse.json({ status: "error", error: "Backend not reachable" });
    }
  }

  // jobId present → proxy SSE stream from backend
  try {
    const authHeaders: Record<string, string> = {};
    if (API_KEY) authHeaders["X-API-Key"] = API_KEY;

    const backendResponse = await fetch(
      `${PYTHON_API_URL}/api/v1/pipeline/stream/${jobId}`,
      { headers: authHeaders },
    );

    if (!backendResponse.ok) {
      return NextResponse.json({ error: "Job not found" }, { status: 404 });
    }

    return new Response(backendResponse.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
        Connection: "keep-alive",
      },
    });
  } catch {
    return NextResponse.json(
      { error: "Backend not reachable" },
      { status: 502 },
    );
  }
}
