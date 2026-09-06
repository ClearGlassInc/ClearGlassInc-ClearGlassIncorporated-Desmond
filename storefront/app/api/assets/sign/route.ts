import { NextRequest, NextResponse } from "next/server";
import { requirePremiumSession } from "@/lib/auth";
import { createAssetToken } from "@/lib/asset-signing";

const ALLOWED_ASSETS = new Set(["artemis-blueprint.pdf", "workflow-pack.zip"]);

export async function POST(request: NextRequest) {
  const session = await requirePremiumSession();
  const body = (await request.json().catch(() => null)) as { assetId?: string } | null;
  if (!body?.assetId || !ALLOWED_ASSETS.has(body.assetId)) {
    return NextResponse.json({ error: "Unknown asset" }, { status: 400 });
  }
  const token = createAssetToken(body.assetId, session.sub);
  return NextResponse.json({ url: `/download/${token}`, expiresInSeconds: 300 });
}
