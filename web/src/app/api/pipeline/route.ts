/**
 * Pipeline API Route - Simple proxy to Python backend.
 *
 * Endpoints:
 * - POST /api/pipeline (action: "start") - Start pipeline job
 * - POST /api/pipeline (action: "status") - Get job status
 */

import { NextRequest, NextResponse } from "next/server";

const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";

interface StartRequest {
  action: "start";
  videoUrl: string;
  productDescription?: string;
  productImages?: string[];
  videoModel?: "sora" | "kling";
}

interface StatusRequest {
  action: "status";
  jobId: string;
}

type PipelineRequest = StartRequest | StatusRequest;

export async function POST(request: NextRequest) {
  try {
    const body: PipelineRequest = await request.json();

    switch (body.action) {
      case "start":
        return handleStart(body);
      case "status":
        return handleStatus(body);
      default:
        return NextResponse.json(
          { error: "Invalid action. Use 'start' or 'status'" },
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

async function handleStart(body: StartRequest) {
  const requestBody = {
    video_url: body.videoUrl,
    product_description: body.productDescription || "",
    product_images: body.productImages || [],
    config: {
      video_model: body.videoModel || "sora",
    },
  };

  console.log("Starting pipeline:", requestBody.video_url);

  const response = await fetch(`${PYTHON_API_URL}/api/v1/pipeline/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody),
  });

  const data = await response.json();

  if (!response.ok) {
    console.error("Pipeline start failed:", data);
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
}

async function handleStatus(body: StatusRequest) {
  const response = await fetch(
    `${PYTHON_API_URL}/api/v1/pipeline/jobs/${body.jobId}`,
    { method: "GET" },
  );

  const data = await response.json();

  if (!response.ok) {
    return NextResponse.json(
      { error: data.detail || "Failed to get job status" },
      { status: response.status },
    );
  }

  return NextResponse.json({
    success: true,
    jobId: data.job_id,
    status: data.status,
    currentStep: data.current_step || "",
    error: data.error || null,
    videoAnalysis: data.video_analysis || null,
    videoPrompt: data.video_prompt || "",
    suggestedScript: data.suggested_script || "",
    generatedVideoUrl: data.generated_video_url || "",
  });
}

export async function GET() {
  try {
    const response = await fetch(`${PYTHON_API_URL}/api/v1/pipeline/health`);
    const data = await response.json();

    return NextResponse.json({
      status: "ok",
      backend: data,
    });
  } catch {
    return NextResponse.json({
      status: "error",
      error: "Backend not reachable",
    });
  }
}
