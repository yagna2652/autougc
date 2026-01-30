import { NextRequest, NextResponse } from "next/server";

const FASTAPI_URL = process.env.FASTAPI_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Forward to FastAPI backend
    const response = await fetch(`${FASTAPI_URL}/api/v1/analyze`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: error.detail || "Failed to start analysis" },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error forwarding to FastAPI:", error);
    return NextResponse.json(
      {
        error: "Failed to connect to analysis service",
        hint: "Make sure FastAPI server is running on http://localhost:8000",
      },
      { status: 500 }
    );
  }
}
