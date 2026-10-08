import { requireCtx } from "@/lib/auth/server";
import { can } from "@/lib/auth/roles";
import { SIMILARITY_DISCLAIMER } from "@/lib/entities/resolve";
import { RationaleField } from "@/components/forms";
import { ClaimBadge, OriginBadge, RelationshipStatusBadge, SyntheticBadge } from "@/components/labels";
import { Card, Flash, PageHeader, sp, When } from "@/components/ui";
import { generateLinksAction, reviewRelationshipAction } from "../actions";

type Search = Promise<Record<string, string | string[] | undefined>>;

const ACTIONS: Record<string, { value: string; label: string }[]> = {
  CANDIDATE: [
    { value: "CONFIRM", label: "Confirm link" },
    { value: "REJECT", label: "Reject link" },
  ],
  CONFIRMED: [{ value: "REVERSE", label: "Reverse confirmed link" }],
  REJECTED: [{ value: "REOPEN", label: "Reopen as candidate" }],
  REVERSED: [{ value: "REOPEN", label: "Reopen as candidate" }],
};

export default async function EntitiesPage({ searchParams }: { searchParams: Search }) {
  const ctx = await requireCtx();
  const q = await searchParams;
  const [people, orgs, vendors, rels] = await Promise.all([
    ctx.db.person.findMany({ include: { organization: true }, orderBy: { recordId: "asc" } }),
    ctx.db.organization.findMany({ orderBy: { recordId: "asc" } }),
    ctx.db.vendor.findMany({ include: { organization: true }, orderBy: { recordId: "asc" } }),
    ctx.db.relationship.findMany({ orderBy: [{ status: "asc" }, { createdAt: "asc" }] }),
  ]);
  const history = await ctx.db.reviewDecision.findMany({
    where: { targetType: "RELATIONSHIP", targetId: { in: rels.map((r) => r.id) } },
    include: { decidedBy: true },
    orderBy: { createdAt: "asc" },
  });
  const name = new Map<string, string>([...orgs.map((o) => [o.id, `${o.recordId} ${o.name}`] as const), ...vendors.map((v) => [v.id, `${v.recordId} ${v.name}`] as const)]);
  const domains = new Map<string, string[]>();
  for (const e of [...orgs, ...vendors]) if (e.domain) domains.set(e.domain, [...(domains.get(e.domain) ?? []), e.recordId]);

  return (
    <>
      <PageHeader
        title="Entity explorer"
        subtitle={`People, organizations, vendors and domains, with every relationship's basis shown. ${SIMILARITY_DISCLAIMER}`}
        actions={
          can(ctx.actor.role, "entity:propose") ? (
            <form action={generateLinksAction}>
              <button className="btn" type="submit">
                Generate candidate links
              </button>
            </form>
          ) : null
        }
      />
      <Flash ok={sp(q.ok)} error={sp(q.error)} />
      <Card title="Relationships" className="mb-4">
        {rels.length === 0 ? (
          <p className="muted">No relationships yet.</p>
        ) : (
          <ul className="space-y-4">
            {rels.map((r) => (
              <li key={r.id} className="rounded-lg border border-white/10 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-slate-100">{name.get(r.fromId) ?? r.fromId}</span>
                  <span className="muted">{r.relationType.replace(/_/g, " ")}</span>
                  <span className="text-slate-100">{name.get(r.toId) ?? r.toId}</span>
                  <RelationshipStatusBadge status={r.status} />
                  <ClaimBadge status={r.claimStatus} />
                  <SyntheticBadge synthetic={r.isSynthetic} />
                </div>
                <p className="mt-1 text-sm">
                  <strong className="text-slate-300">Basis ({r.basis.replace(/_/g, " ").toLowerCase()}):</strong> {r.basisDetail}
                </p>
                {history.filter((h) => h.targetId === r.id).length ? (
                  <ol className="muted mt-2 space-y-1 text-xs">
                    {history
                      .filter((h) => h.targetId === r.id)
                      .map((h) => (
                        <li key={h.id}>
                          {h.fromState?.toLowerCase()} → {h.toState.toLowerCase()} by {h.decidedBy.name}, <When at={h.createdAt} />: {h.rationale}
                        </li>
                      ))}
                  </ol>
                ) : null}
                {can(ctx.actor.role, "entity:review") && ACTIONS[r.status] ? (
                  <form action={reviewRelationshipAction} className="mt-3 grid gap-2 md:grid-cols-[14rem_1fr_auto] md:items-end">
                    <input type="hidden" name="relationshipId" value={r.id} />
                    <div className="flex flex-col gap-1">
                      <label htmlFor={`a-${r.id}`}>Decision</label>
                      <select id={`a-${r.id}`} name="action">
                        {ACTIONS[r.status].map((a) => (
                          <option key={a.value} value={a.value}>
                            {a.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <RationaleField id={`r-${r.id}`} />
                    <button className="btn-quiet" type="submit">
                      Record
                    </button>
                  </form>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Vendors">
          <ul className="space-y-2 text-sm">
            {vendors.map((v) => (
              <li key={v.id}>
                <code>{v.recordId}</code> {v.name} <SyntheticBadge synthetic={v.isSynthetic} />
                <div className="muted text-xs">
                  Tax id {v.taxId ?? "not supplied"} - {v.domain ?? "no domain"} - {v.address ?? "no address"}
                  {v.organization ? ` - names ${v.organization.recordId}` : ""}
                </div>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Organizations">
          <ul className="space-y-2 text-sm">
            {orgs.map((o) => (
              <li key={o.id}>
                <code>{o.recordId}</code> {o.name} <SyntheticBadge synthetic={o.isSynthetic} /> <OriginBadge origin={o.origin} hideSynthetic />
                <div className="muted text-xs">
                  Registration {o.registrationNumber ?? "not supplied"} - {o.domain ?? "no domain"}
                </div>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="People">
          <p className="muted mb-2 text-xs">Only people named in evidence for a case belong here. Do not add unrelated personal information.</p>
          <ul className="space-y-2 text-sm">
            {people.map((p) => (
              <li key={p.id}>
                <code>{p.recordId}</code> {p.displayName} <SyntheticBadge synthetic={p.isSynthetic} />
                <div className="muted text-xs">
                  {p.roleTitle ?? "role not supplied"}
                  {p.organization ? ` at ${p.organization.name}` : ""}
                </div>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Domains">
          <ul className="space-y-2 text-sm">
            {[...domains.entries()].map(([d, ids]) => (
              <li key={d}>
                <code>{d}</code> <span className="muted text-xs">listed by {ids.join(", ")}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
}
