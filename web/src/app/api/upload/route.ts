import { fal } from "@fal-ai/client";
import { NextRequest, NextResponse } from "next/server";

// Configure fal client with API key from environment
fal.config({
  credentials: process.env.FAL_KEY,
});

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

    const contentType = request.headers.get("content-type") || "";

    // Handle JSON with base64 image
    if (contentType.includes("application/json")) {
      const body = await request.json();
      const { base64Image } = body;

      if (!base64Image) {
        return NextResponse.json(
          { error: "No base64Image provided in JSON body" },
          { status: 400 },
        );
      }

      // Convert base64 to blob
      let imageData = base64Image;
      let mimeType = "image/jpeg";

      // Extract mime type and data from data URL
      if (base64Image.startsWith("data:")) {
        const matches = base64Image.match(
          /data:([a-zA-Z0-9]+\/[a-zA-Z0-9-.+]+);base64,(.+)/,
        );
        if (matches) {
          mimeType = matches[1];
          imageData = matches[2];
        }
      }

      // Convert base64 to Uint8Array
      const binaryString = atob(imageData);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Create a Blob
      const blob = new Blob([bytes], { type: mimeType });
      const extension = mimeType.split("/")[1]?.replace("jpeg", "jpg") || "jpg";
      const fileName = `product-${Date.now()}.${extension}`;

      console.log(`📤 Uploading base64 image to Fal storage...`);
      console.log(`   File name: ${fileName}`);
      console.log(`   Size: ${(blob.size / 1024).toFixed(1)} KB`);
      console.log(`   Type: ${mimeType}`);

      // Upload to Fal storage - pass the Blob directly
      const url = await fal.storage.upload(blob);

      console.log(`✅ Image uploaded successfully!`);
      console.log(`   URL: ${url}`);

      return NextResponse.json({
        success: true,
        url,
        fileName,
        size: blob.size,
      });
    }

    // Handle multipart form data
    if (contentType.includes("multipart/form-data")) {
      const formData = await request.formData();
      const file = formData.get("image") as File | null;

      if (!file) {
        return NextResponse.json(
          { error: "No image file provided in form data" },
          { status: 400 },
        );
      }

      // Validate file type
      const validTypes = ["image/jpeg", "image/png", "image/webp", "image/gif"];
      if (!validTypes.includes(file.type)) {
        return NextResponse.json(
          {
            error: "Invalid file type",
            validTypes,
            received: file.type,
          },
          { status: 400 },
        );
      }

      // Validate file size (max 10MB)
      const maxSize = 10 * 1024 * 1024; // 10MB
      if (file.size > maxSize) {
        return NextResponse.json(
          {
            error: "File too large",
            maxSize: "10MB",
            received: `${(file.size / 1024 / 1024).toFixed(1)}MB`,
          },
          { status: 400 },
        );
      }

      console.log(`📤 Uploading form file to Fal storage...`);
      console.log(`   File name: ${file.name}`);
      console.log(`   Type: ${file.type}`);
      console.log(`   Size: ${(file.size / 1024).toFixed(1)} KB`);

      // Upload to Fal storage
      const url = await fal.storage.upload(file);

      console.log(`✅ Image uploaded successfully!`);
      console.log(`   URL: ${url}`);

      return NextResponse.json({
        success: true,
        url,
        fileName: file.name,
        size: file.size,
      });
    }

    // Unsupported content type
    return NextResponse.json(
      {
        error: "Unsupported content type",
        hint: "Send either JSON with 'base64Image' field or multipart form data with 'image' field",
        received: contentType,
      },
      { status: 400 },
    );
  } catch (error) {
    console.error("❌ Upload error:", error);

    let errorMessage = "Unknown error during upload";
    if (error instanceof Error) {
      errorMessage = error.message;
    }

    return NextResponse.json(
      {
        error: errorMessage,
        hint: "Check that FAL_KEY is valid and has storage permissions",
      },
      { status: 500 },
    );
  }
}

// GET endpoint to check upload API status
export async function GET() {
  const hasApiKey = !!process.env.FAL_KEY;

  return NextResponse.json({
    status: "ok",
    configured: hasApiKey,
    supportedFormats: ["image/jpeg", "image/png", "image/webp", "image/gif"],
    maxSize: "10MB",
    endpoints: {
      json: "POST with { base64Image: 'data:image/jpeg;base64,...' }",
      formData: "POST with multipart form data, field name 'image'",
    },
    hint: hasApiKey
      ? "Upload API is ready"
      : "Set FAL_KEY in .env.local to enable image uploads",
  });
}
