import { createHmac, timingSafeEqual } from "crypto";
import { NextResponse } from "next/server";
import { requirePremiumSession } from "@/lib/auth";

const ALLOWED_ASSETS = new Map([
  ["operator-playbook.pdf", "Premium operator playbook placeholder. Replace with private object storage streaming."],
  ["premium-briefing.csv", "metric,value\nprecision,0.94\nrecall,0.89\n"],
]);

function assetSecret(): string {
  return process.env.ASSET_SIGNING_SECRET || process.env.ADMIN_API_KEY || "dev-only-asset-secret-change-me";
}

function expectedSignature(sub: string, asset: string, expires: string): string {
  return createHmac("sha256", assetSecret()).update(`${sub}:${asset}:${expires}`).digest("base64url");
}

export async function GET(request: Request) {
  const session = await requirePremiumSession();
  const url = new URL(request.url);
  const asset = url.searchParams.get("asset") || "";
  const expires = url.searchParams.get("expires") || "0";
  const signature = url.searchParams.get("signature") || "";
  const content = ALLOWED_ASSETS.get(asset);

  if (!content) return NextResponse.json({ error: "asset_not_found" }, { status: 404 });
  if (Number(expires) < Math.floor(Date.now() / 1000)) return NextResponse.json({ error: "link_expired" }, { status: 410 });

  const signatureBuffer = Buffer.from(signature);
  const expectedBuffer = Buffer.from(expectedSignature(session.sub, asset, expires));
  if (!signature || signatureBuffer.length !== expectedBuffer.length || !timingSafeEqual(signatureBuffer, expectedBuffer)) {
    return NextResponse.json({ error: "invalid_signature" }, { status: 403 });
  }

  return new NextResponse(content, {
    headers: {
      "Content-Type": asset.endsWith(".csv") ? "text/csv; charset=utf-8" : "application/octet-stream",
      "Content-Disposition": `attachment; filename="${asset}"`,
      "Cache-Control": "private, no-store",
    },
  });
}
