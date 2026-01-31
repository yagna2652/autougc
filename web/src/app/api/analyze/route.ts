import Anthropic from "@anthropic-ai/sdk";
import { NextRequest, NextResponse } from "next/server";

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

interface AnalyzeRequest {
  productImages: string[]; // base64 encoded images
  productDescription?: string;
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
    const { productImages, productDescription } = body;

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

    // Call Claude Vision API
    const response = await anthropic.messages.create({
      model: "claude-sonnet-4-20250514",
      max_tokens: 1500,
      messages: [
        {
          role: "user",
          content: [
            ...imageContent,
            {
              type: "text",
              text: `Analyze this product image for a UGC-style TikTok video.

${productDescription ? `Product description: "${productDescription}"` : ""}

Provide:
1. What type of product this is
2. Key features visible
3. Best way to showcase it in a video

Respond in JSON format:
{
  "productType": "type of product",
  "description": "detailed description",
  "keyFeatures": ["feature1", "feature2"],
  "suggestedShowcase": "how to best show this product"
}

Return ONLY valid JSON.`,
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
      analysis: analysisResult,
    });
  } catch (error) {
    if (error instanceof Anthropic.APIError) {
      return NextResponse.json(
        { error: error.message },
        { status: error.status },
      );
    }

    if (error instanceof Error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json(
      { error: "Unknown error occurred" },
      { status: 500 },
    );
  }
}

export async function GET() {
  return NextResponse.json({
    status: "ok",
    configured: !!process.env.ANTHROPIC_API_KEY,
  });
}
