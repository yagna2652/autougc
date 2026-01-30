import { fal } from "@fal-ai/client";
import { NextRequest, NextResponse } from "next/server";

// Configure fal client with API key from environment
fal.config({
  credentials: process.env.FAL_KEY,
});

// Model endpoints on Fal.ai
const MODEL_ENDPOINTS = {
  // Text-to-video endpoints
  sora2: "fal-ai/sora-2/text-to-video",
  sora2pro: "fal-ai/sora-2/text-to-video/pro",
  kling: "fal-ai/kling-video/v2.5-turbo/pro/text-to-video",
  // Image-to-video endpoints
  sora2_i2v: "fal-ai/sora-2/image-to-video",
  sora2pro_i2v: "fal-ai/sora-2/image-to-video/pro",
  kling_i2v: "fal-ai/kling-video/v2.5-turbo/pro/image-to-video",
} as const;

type ModelType = keyof typeof MODEL_ENDPOINTS;

type AspectRatio = "9:16" | "16:9";
type KlingDuration = "5" | "10";

interface GenerateRequest {
  prompt: string;
  model: "sora2" | "sora2pro" | "kling";
  duration?: number; // seconds
  aspectRatio?: AspectRatio;
  imageUrl?: string; // Product image URL for image-to-video
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
    const { prompt, model, duration = 4, imageUrl } = body;
    const aspectRatio: AspectRatio = body.aspectRatio || "9:16";

    // Validate required fields
    if (!prompt || !prompt.trim()) {
      return NextResponse.json(
        { error: "Prompt is required" },
        { status: 400 },
      );
    }

    const validBaseModels = ["sora2", "sora2pro", "kling"];
    if (!model || !validBaseModels.includes(model)) {
      return NextResponse.json(
        {
          error: "Invalid model",
          validModels: validBaseModels,
        },
        { status: 400 },
      );
    }

    // Determine if we should use image-to-video or text-to-video
    const useImageToVideo = !!imageUrl;

    // Select the appropriate endpoint
    let endpoint: string;
    if (useImageToVideo) {
      endpoint = MODEL_ENDPOINTS[`${model}_i2v` as ModelType];
    } else {
      endpoint = MODEL_ENDPOINTS[model as ModelType];
    }

    // Truncate prompt if too long (Fal.ai has limits)
    const maxPromptLength = 1500;
    const truncatedPrompt =
      prompt.trim().length > maxPromptLength
        ? prompt.trim().substring(0, maxPromptLength) + "..."
        : prompt.trim();

    // Build arguments based on model and mode
    // Kling uses string duration ("5" or "10"), Sora uses integer (4, 8, or 12)
    const klingDuration: KlingDuration = duration <= 5 ? "5" : "10";
    const soraDuration = duration <= 4 ? 4 : duration <= 8 ? 8 : 12;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let input: any;

    if (model === "kling") {
      input = {
        prompt: truncatedPrompt,
        aspect_ratio: aspectRatio,
        duration: klingDuration,
      };
      if (useImageToVideo && imageUrl) {
        input.image_url = imageUrl;
      }
    } else {
      // Sora 2 / Sora 2 Pro
      input = {
        prompt: truncatedPrompt,
        aspect_ratio: aspectRatio,
        duration: soraDuration,
      };
      if (useImageToVideo && imageUrl) {
        input.image_url = imageUrl;
      }
    }

    // Submit generation request and wait for result
    const result = await fal.subscribe(endpoint, {
      input,
      logs: false,
    });

    const data = result.data as FalVideoResult;

    if (!data?.video?.url) {
      return NextResponse.json(
        { error: "Video generation failed - no video URL returned" },
        { status: 500 },
      );
    }

    // Return the video URL
    return NextResponse.json({
      success: true,
      videoUrl: data.video.url,
      model,
      mode: useImageToVideo ? "image-to-video" : "text-to-video",
      duration,
      aspectRatio,
      usedProductImage: useImageToVideo,
    });
  } catch (error) {
    // Extract Fal.ai error details
    let errorDetails: unknown = null;
    let errorMessage = "Unknown error";

    if (error && typeof error === "object") {
      if ("body" in error) {
        errorDetails = (error as { body: unknown }).body;
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
    models: ["sora2", "sora2pro", "kling"],
    capabilities: {
      textToVideo: true,
      imageToVideo: true,
    },
    hint: hasApiKey
      ? "API is ready for video generation (text-to-video and image-to-video supported)"
      : "Set FAL_KEY in .env.local to enable video generation",
  });
}
