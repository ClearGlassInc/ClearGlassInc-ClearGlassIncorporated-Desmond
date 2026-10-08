import { getActor } from "@/lib/auth/server";
import { db } from "@/lib/db";
import { exportInvestigation } from "@/lib/services/exports";

export async function GET(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const actor = await getActor();
  if (!actor) return Response.json({ error: "Sign in required" }, { status: 401 });
  const { id } = await params;
  const mode = new URL(request.url).searchParams.get("mode") === "unredacted" ? "unredacted" : "redacted";
  try {
    const data = await exportInvestigation({ db: db(), actor }, id, mode);
    return new Response(JSON.stringify(data, null, 2), {
      headers: {
        "content-type": "application/json; charset=utf-8",
        "content-disposition": `attachment; filename="${data.investigation.caseKey}-${mode}.json"`,
        "cache-control": "no-store",
      },
    });
  } catch (e) {
    const status = typeof (e as { status?: unknown }).status === "number" ? (e as { status: number }).status : 500;
    return Response.json({ error: status === 500 ? "Export failed" : (e as Error).message }, { status });
  }
}
