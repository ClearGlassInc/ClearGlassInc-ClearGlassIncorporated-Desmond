import type { Prisma } from "@/generated/prisma/client";
import { requireCtx } from "@/lib/auth/server";
import { can } from "@/lib/auth/roles";
import { isReviewState, OPEN_STATES, REVIEW_STATES } from "@/lib/review";
import { OutcomeBadge, PriorityBadge, ReviewStateBadge, SyntheticBadge, stateLabel } from "@/components/labels";
import { Card, Empty, Flash, PageHeader, sp, When } from "@/components/ui";
import { runEvaluationAction } from "../actions";

type Search = Promise<Record<string, string | string[] | undefined>>;

export default async function AlertsPage({ searchParams }: { searchParams: Search }) {
  const ctx = await requireCtx();
  const params = await searchParams;
  const status = sp(params.status);
  const outcome = sp(params.outcome);
  const where: Prisma.AlertWhereInput = {};
  if (status === "OPEN") where.status = { in: OPEN_STATES };
  else if (status && isReviewState(status)) where.status = status;
  if (outcome === "MATCH" || outcome === "INSUFFICIENT_DATA") where.outcome = outcome;
  const alerts = await ctx.db.alert.findMany({
    where,
    include: { rule: true, ruleVersion: { select: { version: true } }, investigation: { select: { caseKey: true, id: true } } },
    orderBy: [{ createdAt: "desc" }],
  });

  return (
    <>
      <PageHeader
        title="Alert queue"
        subtitle="Rule matches and insufficient-data results from approved rule versions. A match is a reason to review the records, not a finding. No-match results are not shown as alerts and are not clearances."
        actions={
          can(ctx.actor.role, "rule:evaluate") ? (
            <form action={runEvaluationAction}>
              <button className="btn" type="submit">
                Run active rules
              </button>
            </form>
          ) : null
        }
      />
      <Flash ok={sp(params.run) ? `Evaluation finished: ${sp(params.run)}` : sp(params.ok)} error={sp(params.error)} />
      <Card className="mb-4">
        <form className="flex flex-wrap items-end gap-3" method="get">
          <div className="flex flex-col gap-1">
            <label htmlFor="status">Review state</label>
            <select id="status" name="status" defaultValue={status ?? ""}>
              <option value="">All</option>
              <option value="OPEN">Open (awaiting review)</option>
              {REVIEW_STATES.map((s) => (
                <option key={s} value={s}>
                  {stateLabel(s)}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="outcome">Outcome</label>
            <select id="outcome" name="outcome" defaultValue={outcome ?? ""}>
              <option value="">All</option>
              <option value="MATCH">Match</option>
              <option value="INSUFFICIENT_DATA">Insufficient data</option>
            </select>
          </div>
          <button className="btn-quiet" type="submit">
            Filter
          </button>
        </form>
      </Card>
      <Card>
        {alerts.length === 0 ? (
          <Empty>No alerts match these filters.</Empty>
        ) : (
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th scope="col">Alert</th>
                  <th scope="col">Rule</th>
                  <th scope="col">Outcome</th>
                  <th scope="col">Review state</th>
                  <th scope="col">Subject</th>
                  <th scope="col">Case</th>
                  <th scope="col">Created</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <a href={`/alerts/${a.id}`}>{a.id.slice(-8)}</a>
                      <div className="mt-1 flex flex-wrap gap-1">
                        <SyntheticBadge synthetic={a.isSynthetic} />
                        <PriorityBadge priority={a.priority} />
                      </div>
                    </td>
                    <td>
                      <a href={`/rules/${a.ruleId}`}>{a.rule.ruleKey}</a> <span className="muted">v{a.ruleVersion.version}</span>
                      <div className="muted text-xs">{a.rule.name}</div>
                    </td>
                    <td>
                      <OutcomeBadge outcome={a.outcome} />
                    </td>
                    <td>
                      <ReviewStateBadge state={a.status} />
                    </td>
                    <td className="font-mono text-xs">{a.subjectKey}</td>
                    <td>{a.investigation ? <a href={`/investigations/${a.investigation.id}`}>{a.investigation.caseKey}</a> : <span className="muted">none</span>}</td>
                    <td className="text-xs">
                      <When at={a.createdAt} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
