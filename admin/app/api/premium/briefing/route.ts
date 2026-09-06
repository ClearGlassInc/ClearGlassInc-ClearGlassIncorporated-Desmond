import { NextResponse } from "next/server";
import { requirePremiumSession } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET() {
  const session = await requirePremiumSession();
  return NextResponse.json({
    viewer: session.sub,
    briefing: "Server-only premium briefing payload. Never serialize this into public static pages.",
    workflow: ["analyze", "draft", "approval_required", "execute_after_approval"],
  });
}
