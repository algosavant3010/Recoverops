import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export function GET() {
  return NextResponse.json({
    status: "ok",
    service: "recoverops-demo",
    mode: process.env.GEMINI_API_KEY ? "hybrid" : "deterministic",
    timestamp: new Date().toISOString(),
  });
}
