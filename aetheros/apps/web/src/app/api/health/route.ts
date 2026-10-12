import { NextResponse } from "next/server";

export const runtime = "edge";

export async function GET() {
  const checks: Record<string, string> = {};
  let ok = true;

  try {
    const upstream = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/health`,
      { signal: AbortSignal.timeout(5000) },
    );
    const data = await upstream.json();
    checks["api"] = upstream.ok ? "healthy" : "degraded";
    if (!upstream.ok) ok = false;
  } catch {
    checks["api"] = "unreachable";
    ok = false;
  }

  return NextResponse.json(
    { status: ok ? "healthy" : "degraded", checks, timestamp: new Date().toISOString() },
    { status: ok ? 200 : 503 },
  );
}
