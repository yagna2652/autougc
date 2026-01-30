import Anthropic from "@anthropic-ai/sdk";
import { NextRequest, NextResponse } from "next/server";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

interface AnalyzeRequest {
  productImages: string[]; // base64 encoded images
  productDescription?: string;
  blueprintData?: {
    transcript: string;
    hookStyle: string;
    bodyFramework: string;
    ctaUrgency: string;
    setting: string;
    lighting: string;
    energy: string;
    duration: number;
  };
}

export async function POST(request: NextRequest) {
  try {
    // Check for API key
    if (!process.env.ANTHROPIC_API_KEY) {
      return NextResponse.json(
        {
          error: "ANTHROPIC_API_KEY environment variable not configured",
          hint: "Add ANTHROPIC_API_KEY to your .env.local file",
        },
        { status: 500 },
      );
    }

    const body: AnalyzeRequest = await request.json();
    const { productImages, productDescription, blueprintData } = body;

    if (!productImages || productImages.length === 0) {
      return NextResponse.json(
        { error: "At least one product image is required" },
        { status: 400 },
      );
    }

    // Build the image content for Claude
    const imageContent: Anthropic.ImageBlockParam[] = productImages.map(
      (base64Image) => {
        // Extract media type from base64 string if it includes data URL prefix
        let mediaType: "image/jpeg" | "image/png" | "image/gif" | "image/webp" =
          "image/jpeg";
        let imageData = base64Image;

        if (base64Image.startsWith("data:")) {
          const matches = base64Image.match(
            /data:([a-zA-Z0-9]+\/[a-zA-Z0-9-.+]+);base64,(.+)/,
          );
          if (matches) {
            const detectedType = matches[1];
            if (
              ["image/jpeg", "image/png", "image/gif", "image/webp"].includes(
                detectedType,
              )
            ) {
              mediaType = detectedType as typeof mediaType;
            }
            imageData = matches[2];
          }
        }

        return {
          type: "image" as const,
          source: {
            type: "base64" as const,
            media_type: mediaType,
            data: imageData,
          },
        };
      },
    );

    // Build context from blueprint data if available
    let blueprintContext = "";
    if (blueprintData) {
      blueprintContext = `
The user wants to recreate a TikTok-style video with these characteristics:
- Hook Style: ${blueprintData.hookStyle}
- Body Framework: ${blueprintData.bodyFramework}
- CTA Style: ${blueprintData.ctaUrgency}
- Setting: ${blueprintData.setting}
- Lighting: ${blueprintData.lighting}
- Energy Level: ${blueprintData.energy}
- Duration: ${blueprintData.duration} seconds

Original script reference:
"${blueprintData.transcript}"
`;
    }

    // Call Claude Vision API
    const response = await anthropic.messages.create({
      model: "claude-sonnet-4-20250514",
      max_tokens: 2000,
      messages: [
        {
          role: "user",
          content: [
            ...imageContent,
            {
              type: "text",
              text: `You are an expert at creating prompts for AI video generation models (like Sora 2 and Kling) that produce authentic UGC (User-Generated Content) style videos.

Analyze the product image(s) provided and generate a detailed video prompt that will create a realistic TikTok-style product review video.

${productDescription ? `Product description from user: "${productDescription}"` : ""}

${blueprintContext}

Your task:
1. Identify the product (type, color, size, brand if visible, key features)
2. Suggest the best way to showcase this product in a UGC video
3. Generate a detailed prompt for the AI video model

The prompt MUST create a video that looks like a REAL TikTok, NOT an AI-generated video. Include these elements:

CRITICAL REALISM REQUIREMENTS:
- iPhone front camera quality (not cinematic)
- Real skin with pores, texture, natural imperfections
- Handheld camera shake and amateur framing
- Natural indoor lighting (not studio lighting)
- Authentic bedroom/bathroom/kitchen setting
- Person looking at phone screen, not through camera
- Genuine excitement, not acted performance

Respond in this exact JSON format:
{
  "productAnalysis": {
    "type": "what type of product this is",
    "description": "detailed description of the product",
    "keyFeatures": ["feature1", "feature2"],
    "suggestedShowcase": "how to best show this product in video"
  },
  "videoPrompt": "The complete, detailed prompt for the AI video generator. This should be 150-300 words and extremely specific about achieving realism.",
  "suggestedScript": "A short, casual script the person might say (2-3 sentences, very casual TikTok style)"
}

Return ONLY valid JSON, no other text.`,
            },
          ],
        },
      ],
    });

    // Extract the text response
    const textContent = response.content.find((block) => block.type === "text");
    if (!textContent || textContent.type !== "text") {
      return NextResponse.json(
        { error: "No text response from Claude" },
        { status: 500 },
      );
    }

    // Parse the JSON response
    let analysisResult;
    try {
      // Try to extract JSON from the response (in case there's extra text)
      const jsonMatch = textContent.text.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        analysisResult = JSON.parse(jsonMatch[0]);
      } else {
        throw new Error("No JSON found in response");
      }
    } catch {
      return NextResponse.json(
        {
          error: "Failed to parse analysis response",
          rawResponse: textContent.text,
        },
        { status: 500 },
      );
    }

    return NextResponse.json({
      success: true,
      analysis: analysisResult.productAnalysis,
      prompt: analysisResult.videoPrompt,
      suggestedScript: analysisResult.suggestedScript,
    });
  } catch (error) {
    if (error instanceof Anthropic.APIError) {
      if (error.status === 401) {
        return NextResponse.json(
          { error: "Invalid ANTHROPIC_API_KEY - check your API key" },
          { status: 401 },
        );
      }
      if (error.status === 429) {
        return NextResponse.json(
          { error: "Rate limited - please wait and try again" },
          { status: 429 },
        );
      }
      return NextResponse.json(
        { error: error.message },
        { status: error.status },
      );
    }

    if (error instanceof Error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json(
      { error: "Unknown error occurred during analysis" },
      { status: 500 },
    );
  }
}

// GET endpoint to check API status
export async function GET() {
  const hasApiKey = !!process.env.ANTHROPIC_API_KEY;

  return NextResponse.json({
    status: "ok",
    configured: hasApiKey,
    model: "claude-sonnet-4-20250514",
    hint: hasApiKey
      ? "API is ready for product analysis"
      : "Set ANTHROPIC_API_KEY in .env.local to enable smart prompt generation",
  });
}
