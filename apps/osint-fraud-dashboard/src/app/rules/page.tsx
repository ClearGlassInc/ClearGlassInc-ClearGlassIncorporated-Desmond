import { requireCtx } from "@/lib/auth/server";
import { can } from "@/lib/auth/roles";
import { IllustrativeBadge, RuleStatusBadge, SyntheticBadge } from "@/components/labels";
import { Card, Empty, Flash, PageHeader, sp } from "@/components/ui";

type Search = Promise<Record<string, string | string[] | undefined>>;

export default async function RulesPage({ searchParams }: { searchParams: Search }) {
  const ctx = await requireCtx();
  const q = await searchParams;
  const pendingOnly = sp(q.status) === "PENDING_APPROVAL";
  const rules = await ctx.db.detectionRule.findMany({
    where: pendingOnly ? { versions: { some: { status: "PENDING_APPROVAL" } } } : undefined,
    include: { versions: { orderBy: { version: "desc" } }, _count: { select: { alerts: true } } },
    orderBy: { ruleKey: "asc" },
  });
  return (
    <>
      <PageHeader
        title="Pattern registry"
        subtitle="Versioned, deterministic detection rules. A version runs only after a reviewer other than its proposer approves it. Illustrative templates are investigative checks, not patterns from verified incidents."
        actions={
          <>
            <a className="btn-quiet" href={pendingOnly ? "/rules" : "/rules?status=PENDING_APPROVAL"}>
              {pendingOnly ? "Show all" : "Awaiting approval"}
            </a>
            {can(ctx.actor.role, "rule:propose") ? (
              <a className="btn" href="/rules/new">
                Propose a rule
              </a>
            ) : null}
          </>
        }
      />
      <Flash ok={sp(q.ok)} error={sp(q.error)} />
      <Card>
        {rules.length === 0 ? (
          <Empty>No rules.</Empty>
        ) : (
          <div className="overflow-x-auto"><table>
            <thead>
              <tr>
                <th scope="col">Rule</th>
                <th scope="col">Versions</th>
                <th scope="col">Alerts</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id}>
                  <td>
                    <a href={`/rules/${r.id}`}>{r.ruleKey}</a> <IllustrativeBadge illustrative={r.isIllustrative} /> <SyntheticBadge synthetic={r.isSynthetic} />
                    <div>{r.name}</div>
                  </td>
                  <td>
                    <ul className="space-y-1">
                      {r.versions.map((v) => (
                        <li key={v.id} className="flex items-center gap-2 text-xs">
                          <a href={`/rules/${r.id}?v=${v.version}`}>v{v.version}</a> <RuleStatusBadge status={v.status} />
                        </li>
                      ))}
                    </ul>
                  </td>
                  <td className="tabular-nums">{r._count.alerts}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
      </Card>
    </>
  );
}
