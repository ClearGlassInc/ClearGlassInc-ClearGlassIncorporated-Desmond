import { createHmac } from "crypto";
import { NextResponse } from "next/server";
import { requirePremiumSession } from "@/lib/auth";

const ALLOWED_ASSETS = new Set(["operator-playbook.pdf", "premium-briefing.csv"]);

function assetSecret(): string {
  return process.env.ASSET_SIGNING_SECRET || process.env.ADMIN_API_KEY || "dev-only-asset-secret-change-me";
}

export async function GET(request: Request) {
  const session = await requirePremiumSession();
  const url = new URL(request.url);
  const asset = url.searchParams.get("asset") || "";
  if (!ALLOWED_ASSETS.has(asset)) {
    return NextResponse.json({ error: "asset_not_found" }, { status: 404 });
  }

  const expires = Math.floor(Date.now() / 1000) + 300;
  const subject = `${session.sub}:${asset}:${expires}`;
  const signature = createHmac("sha256", assetSecret()).update(subject).digest("base64url");
  const signedUrl = `/api/assets/download?asset=${encodeURIComponent(asset)}&expires=${expires}&signature=${signature}`;

  return NextResponse.json({ asset, expires, signedUrl });
}
