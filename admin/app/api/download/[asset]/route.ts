// GET /api/download/:asset?token=... — serve a premium asset behind a signed,
// expiring token.
//
// Two independent checks must both pass:
//   1. A valid session cookie (enforced by middleware, re-checked here).
//   2. A signed token that matches THIS asset id and has not expired.
// The token is bound to the asset id, so it cannot be replayed against another
// file, and it self-expires so a leaked link dies within minutes. The asset is
// streamed with no-store + Content-Disposition: attachment and is never exposed
// at a public/static path.
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getSession } from "@/lib/session";
import { verifyAssetToken } from "@/lib/signing";
import { getAssetMarkdown } from "@/lib/premium";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ asset: string }> },
): Promise<NextResponse> {
  const { asset } = await params;

  // 1. Session backstop.
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: "authentication required" }, { status: 401 });
  }

  // 2. Signed-token check, bound to this asset id.
  const token = req.nextUrl.searchParams.get("token");
  const subject = await verifyAssetToken(asset, token);
  if (!subject) {
    return NextResponse.json(
      { error: "invalid or expired download token" },
      { status: 403, headers: { "Cache-Control": "no-store" } },
    );
  }

  const file = await getAssetMarkdown(asset);
  if (!file) {
    return NextResponse.json({ error: "asset not found" }, { status: 404 });
  }

  return new NextResponse(file.body, {
    status: 200,
    headers: {
      "Content-Type": "text/markdown; charset=utf-8",
      "Content-Disposition": `attachment; filename="${file.filename}"`,
      "Cache-Control": "no-store, max-age=0, must-revalidate",
      "X-Robots-Tag": "noindex, nofollow",
    },
  });
}
