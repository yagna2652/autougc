import { NextRequest } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

/** Proxy POST /api/generate → backend POST /api/v1/generate (SSE passthrough) */
export async function POST(req: NextRequest) {
  const body = await req.text();

  const upstream = await fetch(`${BACKEND}/api/v1/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });

  if (!upstream.ok || !upstream.body) {
    return new Response(upstream.statusText, { status: upstream.status });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
