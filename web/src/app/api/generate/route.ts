import { fal } from "@fal-ai/client";
import { NextRequest, NextResponse } from "next/server";

// Configure fal client with API key from environment
fal.config({
  credentials: process.env.FAL_KEY,
});

// Model endpoints on Fal.ai
const MODEL_ENDPOINTS = {
  sora2: "fal-ai/sora-2/text-to-video",
  sora2pro: "fal-ai/sora-2/text-to-video/pro",
  kling: "fal-ai/kling-video/v2.5-turbo/pro/text-to-video",
} as const;

type ModelType = keyof typeof MODEL_ENDPOINTS;

type AspectRatio = "9:16" | "16:9";
type KlingDuration = "5" | "10";

interface GenerateRequest {
  prompt: string;
  model: ModelType;
  duration?: number; // seconds
  aspectRatio?: AspectRatio;
}

interface FalVideoResult {
  video: {
    url: string;
    content_type?: string;
    file_name?: string;
    file_size?: number;
  };
}

export async function POST(request: NextRequest) {
  try {
    // Check for API key
    if (!process.env.FAL_KEY) {
      return NextResponse.json(
        {
          error: "FAL_KEY environment variable not configured",
          hint: "Add FAL_KEY to your .env.local file",
        },
        { status: 500 },
      );
    }

    // Parse request body
    const body: GenerateRequest = await request.json();
    const { prompt, model, duration = 4 } = body;
    const aspectRatio: AspectRatio = body.aspectRatio || "9:16";

    // Validate required fields
    if (!prompt || !prompt.trim()) {
      return NextResponse.json(
        { error: "Prompt is required" },
        { status: 400 },
      );
    }

    if (!model || !MODEL_ENDPOINTS[model]) {
      return NextResponse.json(
        {
          error: "Invalid model",
          validModels: Object.keys(MODEL_ENDPOINTS),
        },
        { status: 400 },
      );
    }

    const endpoint = MODEL_ENDPOINTS[model];

    // Truncate prompt if too long (Fal.ai has limits)
    const maxPromptLength = 1500;
    const truncatedPrompt =
      prompt.trim().length > maxPromptLength
        ? prompt.trim().substring(0, maxPromptLength) + "..."
        : prompt.trim();

    console.log(`🎬 Starting video generation with ${model}...`);
    console.log(`   Endpoint: ${endpoint}`);
    console.log(`   Duration: ${duration}s`);
    console.log(`   Aspect Ratio: ${aspectRatio}`);
    console.log(`   Prompt length: ${truncatedPrompt.length} chars`);
    console.log(`   Prompt: ${truncatedPrompt.substring(0, 100)}...`);

    // Build arguments based on model
    // Kling uses string duration ("5" or "10"), Sora uses integer (4, 8, or 12)
    const klingDuration: KlingDuration = duration <= 5 ? "5" : "10";
    const soraDuration = duration <= 4 ? 4 : duration <= 8 ? 8 : 12;

    // Submit generation request and wait for result
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const input: any =
      model === "kling"
        ? {
            prompt: truncatedPrompt,
            aspect_ratio: aspectRatio,
            duration: klingDuration,
          }
        : {
            prompt: truncatedPrompt,
            aspect_ratio: aspectRatio,
            duration: soraDuration,
          };

    const result = await fal.subscribe(endpoint, {
      input,
      logs: true,
      onQueueUpdate: (update) => {
        if (update.status === "IN_PROGRESS" && update.logs) {
          update.logs.forEach((log) => {
            console.log(`   [${model}] ${log.message}`);
          });
        }
      },
    });

    const data = result.data as FalVideoResult;

    if (!data?.video?.url) {
      console.error("❌ No video URL in response:", result);
      return NextResponse.json(
        { error: "Video generation failed - no video URL returned" },
        { status: 500 },
      );
    }

    console.log(`✅ Video generated successfully!`);
    console.log(`   URL: ${data.video.url}`);

    // Return the video URL
    return NextResponse.json({
      success: true,
      videoUrl: data.video.url,
      model,
      duration,
      aspectRatio,
    });
  } catch (error) {
    console.error("❌ Video generation error:", error);

    // Extract Fal.ai error details
    let errorDetails: unknown = null;
    let errorMessage = "Unknown error";

    if (error && typeof error === "object") {
      // Log full error for debugging
      console.error(
        "Full error object:",
        JSON.stringify(error, Object.getOwnPropertyNames(error), 2),
      );

      // Check for Fal.ai specific error body
      if ("body" in error) {
        errorDetails = (error as { body: unknown }).body;
        console.error(
          "Fal.ai error body:",
          JSON.stringify(errorDetails, null, 2),
        );
      }

      if ("message" in error) {
        errorMessage = (error as { message: string }).message;
      }
    }

    // Return detailed error to frontend
    return NextResponse.json(
      {
        error: errorMessage,
        details: errorDetails,
        hint: "Check the prompt content or try a shorter prompt",
      },
      { status: 500 },
    );
  }
}

// GET endpoint to check API status
export async function GET() {
  const hasApiKey = !!process.env.FAL_KEY;

  return NextResponse.json({
    status: "ok",
    configured: hasApiKey,
    models: Object.keys(MODEL_ENDPOINTS),
    hint: hasApiKey
      ? "API is ready for video generation"
      : "Set FAL_KEY in .env.local to enable video generation",
  });
}
