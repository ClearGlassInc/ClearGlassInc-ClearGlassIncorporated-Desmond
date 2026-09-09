import { NextRequest, NextResponse } from "next/server";
import { ForensicCase, assessIntegrity } from "@/lib/truth-fabric/schema";

export async function POST(request: NextRequest) {
  try {
    const payload = await request.json();
    const parsed = ForensicCase.safeParse(payload);
    if (!parsed.success) {
      return NextResponse.json({ error: "Invalid forensic case", issues: parsed.error.issues }, { status: 400 });
    }

    // This endpoint performs deterministic metadata/provenance checks only.
    // It never edits evidence and never claims that media is authentic by itself.
    const result = assessIntegrity(parsed.data);
    return NextResponse.json({ caseId: parsed.data.caseId, result, evaluatedAt: new Date().toISOString() });
  } catch {
    return NextResponse.json({ error: "Malformed JSON" }, { status: 400 });
  }
}
