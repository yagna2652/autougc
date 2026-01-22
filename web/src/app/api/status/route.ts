import { NextResponse } from "next/server";

export async function GET() {
  const hasApiKey = !!process.env.FAL_KEY;

  return NextResponse.json({
    status: "ok",
    configured: hasApiKey,
    models: {
      sora2: {
        name: "Sora 2",
        endpoint: "fal-ai/sora-2/text-to-video",
        costPerSecond: 0.10,
        durations: [4, 8, 12],
      },
      sora2pro: {
        name: "Sora 2 Pro",
        endpoint: "fal-ai/sora-2/text-to-video/pro",
        costPerSecond: 0.30,
        durations: [4, 8, 12],
      },
      kling: {
        name: "Kling 2.5 Turbo Pro",
        endpoint: "fal-ai/kling-video/v2.5-turbo/pro/text-to-video",
        costPerSecond: 0.07,
        durations: [5, 10],
      },
    },
    hint: hasApiKey
      ? "API is ready for video generation"
      : "Set FAL_KEY in .env.local to enable video generation",
  });
}
