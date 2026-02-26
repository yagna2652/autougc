/**
 * Prompts API Route — proxy to Python backend prompt trace endpoints.
 *
 * GET /api/prompts?action=list          → /api/v1/prompts/traces
 * GET /api/prompts?action=trace&traceId=x → /api/v1/prompts/traces/{id}
 * GET /api/prompts?action=templates     → /api/v1/prompts/templates
 * GET /api/prompts?action=compare&a=x&b=y → /api/v1/prompts/compare
 */

import { NextRequest, NextResponse } from "next/server";

const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const action = searchParams.get("action") || "list";

  try {
    let url: string;

    switch (action) {
      case "list": {
        const params = new URLSearchParams();
        const limit = searchParams.get("limit");
        const offset = searchParams.get("offset");
        const templateVersion = searchParams.get("template_version");
        const jobId = searchParams.get("job_id");
        if (limit) params.set("limit", limit);
        if (offset) params.set("offset", offset);
        if (templateVersion) params.set("template_version", templateVersion);
        if (jobId) params.set("job_id", jobId);
        url = `${PYTHON_API_URL}/api/v1/prompts/traces?${params.toString()}`;
        break;
      }
      case "trace": {
        const traceId = searchParams.get("traceId");
        if (!traceId) {
          return NextResponse.json(
            { error: "Missing traceId parameter" },
            { status: 400 },
          );
        }
        url = `${PYTHON_API_URL}/api/v1/prompts/traces/${traceId}`;
        break;
      }
      case "templates": {
        url = `${PYTHON_API_URL}/api/v1/prompts/templates`;
        break;
      }
      case "compare": {
        const a = searchParams.get("a");
        const b = searchParams.get("b");
        if (!a || !b) {
          return NextResponse.json(
            { error: "Missing a or b parameter" },
            { status: 400 },
          );
        }
        url = `${PYTHON_API_URL}/api/v1/prompts/compare?a=${a}&b=${b}`;
        break;
      }
      default:
        return NextResponse.json(
          { error: "Invalid action. Use list, trace, templates, or compare" },
          { status: 400 },
        );
    }

    const response = await fetch(url);
    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || "Backend error" },
        { status: response.status },
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error("Prompts API proxy error:", error);
    return NextResponse.json(
      { error: "Backend not reachable" },
      { status: 502 },
    );
  }
}
