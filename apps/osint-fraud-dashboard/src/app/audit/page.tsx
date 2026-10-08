import type { Prisma } from "@/generated/prisma/client";
import { redirect } from "next/navigation";
import { requireCtx } from "@/lib/auth/server";
import { can } from "@/lib/auth/roles";
import { audit } from "@/lib/services/context";
import { Card, Json, PageHeader, sp, When } from "@/components/ui";

type Search = Promise<Record<string, string | string[] | undefined>>;
const PAGE = 50;

export default async function AuditPage({ searchParams }: { searchParams: Search }) {
  const ctx = await requireCtx();
  if (!can(ctx.actor.role, "audit:view")) {
    await audit(ctx.db, ctx.actor, "security.access_denied", { type: "AuditEvent" }, { permission: "audit:view" }, "denied");
    redirect("/?error=" + encodeURIComponent("Your role cannot view the audit log"));
  }
  const q = await searchParams;
  const action = (sp(q.action) ?? "").trim().slice(0, 60);
  const outcome = sp(q.outcome);
  const page = Math.max(1, Number(sp(q.page)) || 1);
  const where: Prisma.AuditEventWhereInput = {};
  if (action) where.action = { startsWith: action };
  if (outcome === "ok" || outcome === "denied" || outcome === "failed") where.outcome = outcome;
  const [events, total] = await Promise.all([
    ctx.db.auditEvent.findMany({ where, include: { actor: true }, orderBy: { at: "desc" }, skip: (page - 1) * PAGE, take: PAGE }),
    ctx.db.auditEvent.count({ where }),
  ]);
  const qs = (p: number) => `?${new URLSearchParams({ ...(action ? { action } : {}), ...(outcome ? { outcome } : {}), page: String(p) })}`;

  return (
    <>
      <PageHeader
        title="Audit view"
        subtitle="Recorded actions: imports, rule changes, evaluations, review decisions, exports, sign-ins and denied access. This is an ordinary database table in the prototype. It is not immutable or tamper-proof."
      />
      <Card className="mb-4">
        <form className="flex flex-wrap items-end gap-3" method="get">
          <div className="flex flex-col gap-1">
            <label htmlFor="action">Action starts with</label>
            <input id="action" name="action" defaultValue={action} placeholder="rule. / import. / security." />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="outcome">Outcome</label>
            <select id="outcome" name="outcome" defaultValue={outcome ?? ""}>
              <option value="">Any</option>
              <option value="ok">ok</option>
              <option value="denied">denied</option>
              <option value="failed">failed</option>
            </select>
          </div>
          <button className="btn-quiet" type="submit">
            Filter
          </button>
        </form>
      </Card>
      <Card>
        <p className="muted mb-2">
          {total} events; page {page} of {Math.max(1, Math.ceil(total / PAGE))}
        </p>
        <div className="overflow-x-auto">
          <table>
            <thead>
              <tr>
                <th scope="col">When</th>
                <th scope="col">Actor</th>
                <th scope="col">Action</th>
                <th scope="col">Target</th>
                <th scope="col">Outcome</th>
                <th scope="col">Details</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id}>
                  <td className="whitespace-nowrap text-xs">
                    <When at={e.at} />
                  </td>
                  <td className="text-xs">
                    {e.actor?.name ?? "system"} <span className="muted">{e.actorRole?.toLowerCase()}</span>
                  </td>
                  <td>
                    <code className="text-xs">{e.action}</code>
                  </td>
                  <td className="font-mono text-xs">
                    {e.targetType}
                    {e.targetId ? `:${e.targetId.slice(-8)}` : ""}
                  </td>
                  <td className={e.outcome === "ok" ? "text-xs" : "text-xs text-rose-200"}>{e.outcome}</td>
                  <td className="min-w-64">{e.details ? <Json value={e.details} /> : null}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex gap-2">
          {page > 1 ? (
            <a className="btn-quiet" href={qs(page - 1)}>
              Newer
            </a>
          ) : null}
          {page * PAGE < total ? (
            <a className="btn-quiet" href={qs(page + 1)}>
              Older
            </a>
          ) : null}
        </div>
      </Card>
    </>
  );
}
