import { NextResponse } from "next/server";
import { requirePremiumSession } from "@/lib/auth";
import { emitSecurityLog } from "@/lib/request-logging";

export async function GET() {
  const session = await requirePremiumSession();
  emitSecurityLog({ event: "premium_api_workflow", fingerprint: session.sub, path: "/api/premium/workflow", referrer: null, timestamp: new Date().toISOString() });
  return NextResponse.json({
    workflow: ["triage", "enrich", "correlate", "approval_gate", "audited_delivery"],
    prompt: "Return evidence-bound recommendations only; operational actions require human approval.",
  });
}
