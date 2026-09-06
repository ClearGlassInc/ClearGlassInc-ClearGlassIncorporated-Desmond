import { NextRequest, NextResponse } from "next/server";
import { verifyAssetToken } from "@/lib/asset-signing";
import { emitSecurityLog } from "@/lib/request-logging";

export async function GET(_request: NextRequest, { params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const verified = verifyAssetToken(token);
  if (!verified) {
    return NextResponse.json({ error: "Expired or invalid asset token" }, { status: 403 });
  }
  emitSecurityLog({ event: "premium_asset_download", fingerprint: verified.subject, path: `/download/${verified.assetId}`, referrer: null, timestamp: new Date().toISOString() });
  return new NextResponse(`Protected asset placeholder for ${verified.assetId}\n`, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Content-Disposition": `attachment; filename="${verified.assetId.replace(/[^a-zA-Z0-9._-]/g, "_")}"`,
      "Cache-Control": "private, no-store",
    },
  });
}
