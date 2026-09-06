// GET /healthz — public liveness probe (allowlisted in middleware). Returns 200
// without touching the session or any premium data, so platform health checks
// and uptime monitors work without credentials.
import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export function GET(): NextResponse {
  return NextResponse.json(
    { status: "ok", service: "admin", ts: new Date().toISOString() },
    { headers: { "Cache-Control": "no-store" } },
  );
}
