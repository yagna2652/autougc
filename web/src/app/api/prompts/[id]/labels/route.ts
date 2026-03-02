import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await req.text();
  const res = await fetch(`${BACKEND}/api/v1/prompts/${id}/labels`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const { searchParams } = new URL(req.url);
  const labelName = searchParams.get("name");
  if (!labelName) {
    return NextResponse.json({ error: "Missing label name" }, { status: 400 });
  }
  const res = await fetch(`${BACKEND}/api/v1/prompts/${id}/labels/${encodeURIComponent(labelName)}`, {
    method: "DELETE",
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
