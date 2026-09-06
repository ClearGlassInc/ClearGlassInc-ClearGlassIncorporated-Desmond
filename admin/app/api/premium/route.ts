// GET /api/premium — protected API route example.
//
// Returns premium JSON (workflows + prompts) only to an authenticated session.
// Middleware already rejects unauthenticated /api/* calls with 401; this handler
// re-checks the session itself so the sensitive data path is safe even if the
// route is reached by some means other than the matched middleware. This is the
// pattern to copy for any new premium data endpoint.
import { NextResponse } from "next/server";
import { getSession } from "@/lib/session";
import { getPlaybooks } from "@/lib/premium";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(): Promise<NextResponse> {
  const session = await getSession();
  if (!session) {
    return NextResponse.json(
      { error: "authentication required" },
      { status: 401, headers: { "Cache-Control": "no-store" } },
    );
  }

  const playbooks = await getPlaybooks();
  return NextResponse.json(
    { operator: session.sub, playbooks },
    { headers: { "Cache-Control": "no-store, max-age=0", "X-Robots-Tag": "noindex" } },
  );
}
