/**
 * Pipeline API Route - Proxies requests to the Python UGC pipeline backend.
 *
 * Simple API that forwards requests to the Python FastAPI backend.
 *
 * Endpoints:
 * - POST /api/pipeline (action: "start") - Start pipeline job
 * - POST /api/pipeline (action: "status") - Get job status
 */

import { NextRequest, NextResponse } from "next/server";

const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";

interface PipelineStartRequest {
  action: "start";
  videoUrl: string;
  productDescription?: string;
  productImages?: string[];
  config?: {
    claudeModel?: string;
    numFrames?: number;
    videoModel?: string;
    videoDuration?: number;
    aspectRatio?: string;
  };
}

interface StatusRequest {
  action: "status";
  jobId: string;
}

type PipelineRequest = PipelineStartRequest | StatusRequest;

/**
 * Convert camelCase to snake_case for Python API
 */
function toSnakeCase(obj: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(obj)) {
    const snakeKey = key.replace(
      /[A-Z]/g,
      (letter) => `_${letter.toLowerCase()}`,
    );

    if (value && typeof value === "object" && !Array.isArray(value)) {
      result[snakeKey] = toSnakeCase(value as Record<string, unknown>);
    } else {
      result[snakeKey] = value;
    }
  }

  return result;
}

export async function POST(request: NextRequest) {
  try {
    const body: PipelineRequest = await request.json();

    switch (body.action) {
      case "start":
        return handleStartPipeline(body);
      case "status":
        return handleGetStatus(body);
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

async function handleStartPipeline(body: PipelineStartRequest) {
  const requestBody = {
    video_url: body.videoUrl,
    product_description: body.productDescription || "",
    product_images: body.productImages || [],
    config: body.config
      ? toSnakeCase(body.config as Record<string, unknown>)
      : null,
  };

  console.log("Starting pipeline with:", JSON.stringify(requestBody, null, 2));

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

async function handleGetStatus(body: StatusRequest) {
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

  // Return simplified response matching new backend
  return NextResponse.json({
    success: true,
    jobId: data.job_id,
    status: data.status,
    currentStep: data.current_step,
    error: data.error || null,
    // Analysis results
    videoAnalysis: data.video_analysis || null,
    // Prompt results
    videoPrompt: data.video_prompt || "",
    suggestedScript: data.suggested_script || "",
    // Video output
    generatedVideoUrl: data.generated_video_url || "",
    // Metadata
    createdAt: data.created_at,
    updatedAt: data.updated_at,
  });
}

// GET endpoint for health check
export async function GET() {
  try {
    const response = await fetch(`${PYTHON_API_URL}/api/v1/pipeline/health`, {
      method: "GET",
    });

    const data = await response.json();

    return NextResponse.json({
      status: "ok",
      pythonBackend: data,
    });
  } catch (error) {
    return NextResponse.json({
      status: "error",
      error: "Python backend not reachable",
      hint: "Make sure the Python API server is running on localhost:8000",
    });
  }
}
