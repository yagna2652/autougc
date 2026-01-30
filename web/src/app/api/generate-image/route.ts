import { fal } from "@fal-ai/client";
import { NextRequest, NextResponse } from "next/server";

// Configure fal client with API key from environment
fal.config({
  credentials: process.env.FAL_KEY,
});

interface GenerateImageRequest {
  prompt: string;
  productImages?: string[]; // Base64 product reference images
  aspectRatio?: "9:16" | "16:9" | "1:1";
  model?: "flux-pro" | "flux-dev";
}

interface FalImageResult {
  images: Array<{
    url: string;
    content_type?: string;
  }>;
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

    const body: GenerateImageRequest = await request.json();
    const {
      prompt,
      aspectRatio = "9:16",
      model = "flux-pro",
    } = body;

    if (!prompt || !prompt.trim()) {
      return NextResponse.json(
        { error: "Prompt is required" },
        { status: 400 },
      );
    }

    // Map aspect ratio to image size
    const sizeMap = {
      "9:16": { width: 720, height: 1280 },
      "16:9": { width: 1280, height: 720 },
      "1:1": { width: 1024, height: 1024 },
    };
    const size = sizeMap[aspectRatio] || sizeMap["9:16"];

    // Select model endpoint
    const endpoint = model === "flux-pro"
      ? "fal-ai/flux-pro/v1.1"
      : "fal-ai/flux/dev";

    // Generate image
    const result = await fal.subscribe(endpoint, {
      input: {
        prompt: prompt.trim(),
        image_size: size,
        num_images: 1,
        safety_tolerance: "5", // Less restrictive for product photos
      },
      logs: false,
    });

    const data = result.data as FalImageResult;

    if (!data?.images?.[0]?.url) {
      return NextResponse.json(
        { error: "Image generation failed - no image URL returned" },
        { status: 500 },
      );
    }

    return NextResponse.json({
      success: true,
      imageUrl: data.images[0].url,
      model,
      aspectRatio,
    });
  } catch (error) {
    let errorMessage = "Unknown error";
    let errorDetails: unknown = null;

    if (error && typeof error === "object") {
      if ("body" in error) {
        errorDetails = (error as { body: unknown }).body;
      }
      if ("message" in error) {
        errorMessage = (error as { message: string }).message;
      }
    }

    return NextResponse.json(
      {
        error: errorMessage,
        details: errorDetails,
      },
      { status: 500 },
    );
  }
}

export async function GET() {
  const hasApiKey = !!process.env.FAL_KEY;

  return NextResponse.json({
    status: "ok",
    configured: hasApiKey,
    models: ["flux-pro", "flux-dev"],
    hint: hasApiKey
      ? "API is ready for image generation"
      : "Set FAL_KEY in .env.local to enable image generation",
  });
}
