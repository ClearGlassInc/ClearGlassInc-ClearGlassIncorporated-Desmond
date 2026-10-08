import type { Prisma } from "@/generated/prisma/client";
import { requireCtx } from "@/lib/auth/server";
import { can } from "@/lib/auth/roles";
import { isReviewState, REVIEW_STATES } from "@/lib/review";
import { ClaimBadge, PriorityBadge, ReviewStateBadge, SyntheticBadge, stateLabel } from "@/components/labels";
import { Card, Empty, Flash, PageHeader, sp, When } from "@/components/ui";
import { createInvestigationAction } from "../actions";

type Search = Promise<Record<string, string | string[] | undefined>>;

export default async function InvestigationsPage({ searchParams }: { searchParams: Search }) {
  const ctx = await requireCtx();
  const params = await searchParams;
  const q = (sp(params.q) ?? "").trim().slice(0, 200);
  const status = sp(params.status);
  const owner = sp(params.owner);
  const where: Prisma.InvestigationWhereInput = {};
  if (q) {
    where.OR = [
      { title: { contains: q, mode: "insensitive" } },
      { summary: { contains: q, mode: "insensitive" } },
      { caseKey: { contains: q, mode: "insensitive" } },
    ];
  }
  if (status && isReviewState(status)) where.status = status;
  if (owner && /^[a-z0-9]+$/i.test(owner)) where.ownerId = owner;
  const [cases, owners] = await Promise.all([
    ctx.db.investigation.findMany({ where, include: { owner: true, _count: { select: { alerts: true, notes: true } } }, orderBy: { updatedAt: "desc" } }),
    ctx.db.user.findMany({ where: { ownedInvestigations: { some: {} } }, orderBy: { name: "asc" } }),
  ]);

  return (
    <>
      <PageHeader title="Investigations" subtitle="Cases group alerts, evidence and notes. An open case is an inquiry; nothing in it is established until a reviewer records a decision." />
      <Flash ok={sp(params.ok)} error={sp(params.error)} />
      <Card className="mb-4">
        <form className="flex flex-wrap items-end gap-3" method="get" role="search">
          <div className="flex flex-col gap-1">
            <label htmlFor="q">Search</label>
            <input id="q" name="q" defaultValue={q} placeholder="Case key, title or summary" />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="status">State</label>
            <select id="status" name="status" defaultValue={status ?? ""}>
              <option value="">All</option>
              {REVIEW_STATES.map((s) => (
                <option key={s} value={s}>
                  {stateLabel(s)}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="owner">Owner</label>
            <select id="owner" name="owner" defaultValue={owner ?? ""}>
              <option value="">Anyone</option>
              {owners.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.name}
                </option>
              ))}
            </select>
          </div>
          <button className="btn-quiet" type="submit">
            Apply
          </button>
        </form>
      </Card>
      <Card>
        {cases.length === 0 ? (
          <Empty>No cases match.</Empty>
        ) : (
          <div className="overflow-x-auto">
            <table>
              <thead>
                <tr>
                  <th scope="col">Case</th>
                  <th scope="col">State</th>
                  <th scope="col">Status of claims</th>
                  <th scope="col">Owner</th>
                  <th scope="col">Alerts / notes</th>
                  <th scope="col">Updated</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <a href={`/investigations/${c.id}`}>{c.caseKey}</a> <SyntheticBadge synthetic={c.isSynthetic} />
                      <div>{c.title}</div>
                      <div className="mt-1">
                        <PriorityBadge priority={c.priority} />
                      </div>
                    </td>
                    <td>
                      <ReviewStateBadge state={c.status} />
                    </td>
                    <td>
                      <ClaimBadge status={c.claimStatus} />
                    </td>
                    <td>{c.owner.name}</td>
                    <td className="tabular-nums">
                      {c._count.alerts} / {c._count.notes}
                    </td>
                    <td className="text-xs">
                      <When at={c.updatedAt} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {can(ctx.actor.role, "investigation:create") ? (
        <Card title="Open a case without an alert" className="mt-4">
          <form action={createInvestigationAction} className="grid gap-3 md:grid-cols-2">
            <div className="flex flex-col gap-1">
              <label htmlFor="new-title">Title</label>
              <input id="new-title" name="title" required minLength={5} />
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="new-priority">Priority</label>
              <select id="new-priority" name="priority" defaultValue="MEDIUM">
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
              </select>
            </div>
            <div className="flex flex-col gap-1 md:col-span-2">
              <label htmlFor="new-summary">Why open it (avoid naming individuals as wrongdoers)</label>
              <textarea id="new-summary" name="summary" required minLength={10} rows={2} />
            </div>
            <div>
              <button className="btn" type="submit">
                Open case
              </button>
            </div>
          </form>
        </Card>
      ) : null}
    </>
  );
}
