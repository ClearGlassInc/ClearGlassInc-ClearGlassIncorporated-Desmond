import { db } from "@/lib/db";

export const dynamic = "force-dynamic";

/** Liveness plus database reachability. Reveals nothing else. */
export async function GET() {
  try {
    await db().$queryRaw`SELECT 1`;
    return Response.json({ ok: true, database: "reachable" });
  } catch {
    return Response.json({ ok: false, database: "unreachable" }, { status: 503 });
  }
}
