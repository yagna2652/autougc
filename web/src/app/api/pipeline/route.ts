/**
 * Pipeline API Route - Proxies requests to the Python LangGraph pipeline backend.
 *
 * This route provides a Next.js API layer that forwards requests to the
 * Python FastAPI backend running the LangGraph pipeline.
 *
 * Endpoints:
 * - POST /api/pipeline (action: "start") - Start full pipeline
 * - POST /api/pipeline (action: "generate-prompt") - Generate prompts from blueprint
 * - POST /api/pipeline (action: "status") - Get job status
 */

import { NextRequest, NextResponse } from "next/server";

const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";

interface PipelineStartRequest {
  action: "start";
  videoUrl: string;
  productImages?: string[];
  productDescription?: string;
  productContext?: {
    type?: string;
    interactions?: string[];
    tactileFeatures?: string[];
    soundFeatures?: string[];
    sizeDescription?: string;
    highlightFeature?: string;
    customInstructions?: string;
  };
  config?: {
    enableMechanics?: boolean;
    productCategory?: string;
    targetDuration?: number;
    energyLevel?: string;
    videoModel?: string;
    videoDuration?: number;
    aspectRatio?: string;
    useImageToVideo?: boolean;
  };
  skipVideoGeneration?: boolean;
}

interface GeneratePromptRequest {
  action: "generate-prompt";
  blueprint: Record<string, unknown>;
  blueprintSummary?: Record<string, unknown>;
  productImages?: string[];
  productDescription?: string;
  productContext?: {
    type?: string;
    interactions?: string[];
    tactileFeatures?: string[];
    soundFeatures?: string[];
    sizeDescription?: string;
    highlightFeature?: string;
    customInstructions?: string;
  };
  config?: {
    enableMechanics?: boolean;
    productCategory?: string;
    targetDuration?: number;
    energyLevel?: string;
  };
}

interface StatusRequest {
  action: "status";
  jobId: string;
}

type PipelineRequest = PipelineStartRequest | GeneratePromptRequest | StatusRequest;

/**
 * Convert camelCase to snake_case for Python API
 */
function toSnakeCase(obj: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(obj)) {
    // Convert camelCase to snake_case
    const snakeKey = key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);

    if (value && typeof value === "object" && !Array.isArray(value)) {
      result[snakeKey] = toSnakeCase(value as Record<string, unknown>);
    } else {
      result[snakeKey] = value;
    }
  }

  return result;
}

/**
 * Convert snake_case to camelCase for frontend
 */
function toCamelCase(obj: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(obj)) {
    // Convert snake_case to camelCase
    const camelKey = key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());

    if (value && typeof value === "object" && !Array.isArray(value)) {
      result[camelKey] = toCamelCase(value as Record<string, unknown>);
    } else {
      result[camelKey] = value;
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
      case "generate-prompt":
        return handleGeneratePrompt(body);
      case "status":
        return handleGetStatus(body);
      default:
        return NextResponse.json(
          { error: "Invalid action. Use 'start', 'generate-prompt', or 'status'" },
          { status: 400 }
        );
    }
  } catch (error) {
    console.error("Pipeline API error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

async function handleStartPipeline(body: PipelineStartRequest) {
  const requestBody = {
    video_url: body.videoUrl,
    product_images: body.productImages || [],
    product_description: body.productDescription || "",
    product_context: body.productContext
      ? toSnakeCase(body.productContext as Record<string, unknown>)
      : null,
    config: body.config ? toSnakeCase(body.config as Record<string, unknown>) : null,
    skip_video_generation: body.skipVideoGeneration || false,
  };

  const response = await fetch(`${PYTHON_API_URL}/api/v1/pipeline/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody),
  });

  const data = await response.json();

  if (!response.ok) {
    return NextResponse.json(
      { error: data.detail || "Failed to start pipeline" },
      { status: response.status }
    );
  }

  return NextResponse.json({
    success: true,
    jobId: data.job_id,
    status: data.status,
    message: data.message,
  });
}

async function handleGeneratePrompt(body: GeneratePromptRequest) {
  const requestBody = {
    blueprint: body.blueprint,
    blueprint_summary: body.blueprintSummary || null,
    product_images: body.productImages || [],
    product_description: body.productDescription || "",
    product_context: body.productContext
      ? toSnakeCase(body.productContext as Record<string, unknown>)
      : null,
    config: body.config ? toSnakeCase(body.config as Record<string, unknown>) : null,
  };

  const response = await fetch(`${PYTHON_API_URL}/api/v1/pipeline/generate-prompt`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody),
  });

  const data = await response.json();

  if (!response.ok) {
    return NextResponse.json(
      { error: data.detail || "Failed to generate prompt" },
      { status: response.status }
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
    { method: "GET" }
  );

  const data = await response.json();

  if (!response.ok) {
    return NextResponse.json(
      { error: data.detail || "Failed to get job status" },
      { status: response.status }
    );
  }

  // Convert snake_case response to camelCase for frontend
  return NextResponse.json({
    success: true,
    jobId: data.job_id,
    status: data.status,
    currentStep: data.current_step,
    progress: data.progress,
    error: data.error,
    // Results
    blueprint: data.blueprint,
    blueprintSummary: data.blueprint_summary,
    basePrompt: data.base_prompt,
    mechanicsPrompt: data.mechanics_prompt,
    finalPrompt: data.final_prompt,
    promptSource: data.prompt_source,
    generatedVideoUrl: data.generated_video_url,
    // Metadata
    createdAt: data.created_at,
    completedAt: data.completed_at,
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
