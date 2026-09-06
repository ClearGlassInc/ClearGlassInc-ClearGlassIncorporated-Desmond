import { NextResponse } from "next/server";
import { env } from "@/lib/env";
const plans = new Set(["control", "oversight", "command"]);
const intervals = new Set(["monthly", "annual"]);
export async function POST(request: Request) {
  if (env.COMMERCE_APPROVED !== "true") return NextResponse.json({ error: "Checkout is disabled pending owner approval." }, { status: 503 });
  const body: unknown = await request.json();
  if (!body || typeof body !== "object" || Array.isArray(body)) return NextResponse.json({ error: "Invalid selection." }, { status: 400 });
  const keys = Object.keys(body);
  const values = body as Record<string, unknown>;
  if (keys.length !== 2 || !plans.has(String(values.plan)) || !intervals.has(String(values.interval))) return NextResponse.json({ error: "Invalid selection." }, { status: 400 });
  return NextResponse.json({ error: "Checkout adapter is intentionally not activated." }, { status: 503 });
}
