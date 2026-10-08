import { notFound } from "next/navigation";
import { requireCtx } from "@/lib/auth/server";
import { can } from "@/lib/auth/roles";
import { DecisionForm } from "@/components/forms";
import { ClaimBadge, OutcomeBadge, PriorityBadge, ReviewStateBadge, SyntheticBadge, stateLabel } from "@/components/labels";
import { Card, Flash, PageHeader, sp, When } from "@/components/ui";
import { addNoteAction, decideInvestigationAction } from "../../actions";

type Params = Promise<{ id: string }>;
type Search = Promise<Record<string, string | string[] | undefined>>;

const NOTE_CLAIM: Record<string, string> = {
  OBSERVATION: "SOURCE_SUPPORTED_OBSERVATION",
  INTERPRETATION: "ANALYST_INTERPRETATION",
};

export default async function InvestigationPage({ params, searchParams }: { params: Params; searchParams: Search }) {
  const ctx = await requireCtx();
  const { id } = await params;
  const q = await searchParams;
  const inv = await ctx.db.investigation.findUnique({
    where: { id },
    include: {
      owner: true,
      alerts: { include: { rule: true, ruleVersion: { select: { version: true } } }, orderBy: { createdAt: "asc" } },
      notes: { include: { author: true, evidence: { include: { evidence: { select: { id: true, recordId: true } } } } }, orderBy: { createdAt: "asc" } },
    },
  });
  if (!inv) notFound();
  const [decisions, events] = await Promise.all([
    ctx.db.reviewDecision.findMany({
      where: { OR: [{ targetType: "INVESTIGATION", targetId: id }, { targetType: "ALERT", targetId: { in: inv.alerts.map((a) => a.id) } }] },
      include: { decidedBy: true },
      orderBy: { createdAt: "asc" },
    }),
    ctx.db.auditEvent.findMany({
      where: { OR: [{ targetType: "Investigation", targetId: id }, { targetType: "Alert", targetId: { in: inv.alerts.map((a) => a.id) }, action: "alert.link" }] },
      include: { actor: true },
      orderBy: { at: "asc" },
    }),
  ]);

  type Entry = { at: Date; kind: string; text: string; who: string };
  const timeline: Entry[] = [
    ...events
      .filter((e) => e.action === "investigation.create" || e.action === "alert.link" || e.action === "export.investigation")
      .map((e) => ({
        at: e.at,
        kind: e.action,
        text:
          e.action === "investigation.create"
            ? "Case opened"
            : e.action === "alert.link"
              ? `Alert ${e.targetId?.slice(-8)} added`
              : `Exported (${(e.details as { mode?: string } | null)?.mode ?? "?"})`,
        who: e.actor?.name ?? "system",
      })),
    ...decisions.map((d) => ({
      at: d.createdAt,
      kind: "decision",
      text: `${d.targetType === "ALERT" ? `Alert ${d.targetId.slice(-8)}` : "Case"}: ${stateLabel(d.fromState ?? "")} → ${stateLabel(d.toState)}. ${d.rationale}`,
      who: d.decidedBy.name,
    })),
    ...inv.notes.map((n) => ({ at: n.createdAt, kind: "note", text: `${n.kind.toLowerCase()} note added`, who: n.author.name })),
  ].sort((a, b) => a.at.getTime() - b.at.getTime());

  return (
    <>
      <PageHeader
        title={`${inv.caseKey}: ${inv.title}`}
        subtitle={
          <span className="flex flex-wrap items-center gap-2">
            <ReviewStateBadge state={inv.status} />
            <ClaimBadge status={inv.claimStatus} />
            <PriorityBadge priority={inv.priority} />
            <SyntheticBadge synthetic={inv.isSynthetic} />
            <span className="muted">Owner: {inv.owner.name}</span>
          </span>
        }
        actions={
          <>
            {can(ctx.actor.role, "export:redacted") ? (
              <a className="btn-quiet" href={`/api/export/investigations/${inv.id}?mode=redacted`}>
                Export (redacted JSON)
              </a>
            ) : null}
            {can(ctx.actor.role, "export:unredacted") ? (
              <a className="btn-quiet" href={`/api/export/investigations/${inv.id}?mode=unredacted`}>
                Export (unredacted, audited)
              </a>
            ) : null}
          </>
        }
      />
      <Flash ok={sp(q.ok)} error={sp(q.error)} />
      <div className="grid gap-4 xl:grid-cols-3">
        <div className="space-y-4 xl:col-span-2">
          <Card title="Summary">
            <p className="whitespace-pre-wrap">{inv.summary}</p>
          </Card>
          <Card title="Alerts in this case">
            {inv.alerts.length === 0 ? (
              <p className="muted">No alerts linked.</p>
            ) : (
              <ul className="space-y-3">
                {inv.alerts.map((a) => (
                  <li key={a.id} className="rounded-lg border border-white/10 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <a href={`/alerts/${a.id}`}>{a.id.slice(-8)}</a>
                      <span className="muted">
                        {a.rule.ruleKey} v{a.ruleVersion.version}
                      </span>
                      <OutcomeBadge outcome={a.outcome} />
                      <ReviewStateBadge state={a.status} />
                    </div>
                    <p className="mt-1 text-sm">{a.explanation}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title="Notes">
            {inv.notes.length === 0 ? <p className="muted">No notes yet.</p> : null}
            <ul className="space-y-3">
              {inv.notes.map((n) => (
                <li key={n.id} className="rounded-lg border border-white/10 p-3">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    {NOTE_CLAIM[n.kind] ? <ClaimBadge status={NOTE_CLAIM[n.kind]} /> : <span className="uppercase tracking-wide text-slate-300">Open question</span>}
                    <span className="muted">
                      {n.author.name} - <When at={n.createdAt} />
                    </span>
                  </div>
                  <p className="mt-2 whitespace-pre-wrap">{n.body}</p>
                  {n.evidence.length ? (
                    <p className="muted mt-1 text-xs">
                      Cites:{" "}
                      {n.evidence.map((e, i) => (
                        <span key={e.evidence.id}>
                          {i ? ", " : ""}
                          <a href={`/evidence/${e.evidence.id}`}>{e.evidence.recordId}</a>
                        </span>
                      ))}
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
            {can(ctx.actor.role, "investigation:note") ? (
              <form action={addNoteAction} className="mt-4 grid gap-3">
                <input type="hidden" name="investigationId" value={inv.id} />
                <div className="flex flex-col gap-1">
                  <label htmlFor="kind">Note type</label>
                  <select id="kind" name="kind" defaultValue="OBSERVATION">
                    <option value="OBSERVATION">Observation (must cite evidence)</option>
                    <option value="INTERPRETATION">Interpretation (your reading, labelled as such)</option>
                    <option value="QUESTION">Open question</option>
                  </select>
                </div>
                <div className="flex flex-col gap-1">
                  <label htmlFor="body">Note</label>
                  <textarea id="body" name="body" required minLength={3} rows={3} />
                </div>
                <div className="flex flex-col gap-1">
                  <label htmlFor="evidenceRecordIds">Evidence record ids (comma separated)</label>
                  <input id="evidenceRecordIds" name="evidenceRecordIds" placeholder="SYN-EV-001, SYN-EV-002" />
                </div>
                <div>
                  <button className="btn" type="submit">
                    Add note
                  </button>
                </div>
              </form>
            ) : null}
          </Card>
        </div>
        <div className="space-y-4">
          <Card title="Case decision">
            <DecisionForm action={decideInvestigationAction} hidden={{ investigationId: inv.id }} state={inv.status} role={ctx.actor.role} decidePermission="investigation:decide" />
          </Card>
          <Card title="Timeline">
            <ol className="space-y-3 text-sm">
              {timeline.map((t, i) => (
                <li key={i} className="border-l-2 border-cyan-300/30 pl-3">
                  <div className="muted text-xs">
                    <When at={t.at} /> - {t.who}
                  </div>
                  <div>{t.text}</div>
                </li>
              ))}
            </ol>
          </Card>
        </div>
      </div>
    </>
  );
}
