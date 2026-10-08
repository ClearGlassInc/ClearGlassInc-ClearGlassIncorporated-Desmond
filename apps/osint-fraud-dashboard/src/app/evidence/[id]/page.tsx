import { notFound } from "next/navigation";
import { requireCtx } from "@/lib/auth/server";
import { can, canReadClassification } from "@/lib/auth/roles";
import { HASH_DISCLAIMER } from "@/lib/hash";
import { RationaleField } from "@/components/forms";
import { ClaimBadge, ClassificationBadge, OriginBadge, SyntheticBadge, VerificationBadge } from "@/components/labels";
import { Card, Field, Flash, PageHeader, SourceLink, sp, When } from "@/components/ui";
import { addFactAction, verifyEvidenceAction } from "../../actions";

type Params = Promise<{ id: string }>;
type Search = Promise<Record<string, string | string[] | undefined>>;

export default async function EvidenceDetail({ params, searchParams }: { params: Params; searchParams: Search }) {
  const ctx = await requireCtx();
  const { id } = await params;
  const q = await searchParams;
  const e = await ctx.db.evidence.findUnique({
    where: { id },
    include: {
      source: true,
      verifiedBy: true,
      facts: { orderBy: { createdAt: "asc" } },
      incidents: { include: { incident: true } },
      ruleSupport: { include: { ruleVersion: { include: { rule: true } } } },
      transactions: { select: { id: true, recordId: true, type: true } },
      noteLinks: { include: { note: { include: { investigation: { select: { id: true, caseKey: true } } } } } },
    },
  });
  if (!e) notFound();
  const readable = canReadClassification(ctx.actor.role, e.accessClassification);
  const decisions = await ctx.db.reviewDecision.findMany({ where: { targetType: "EVIDENCE", targetId: id }, include: { decidedBy: true }, orderBy: { createdAt: "asc" } });
  const rules = new Map(e.ruleSupport.map((s) => [s.ruleVersion.id, s.ruleVersion]));

  return (
    <>
      <PageHeader
        title={e.recordId}
        subtitle={
          <span className="flex flex-wrap items-center gap-2">
            <SyntheticBadge synthetic={e.isSynthetic} />
            <OriginBadge origin={e.origin} hideSynthetic />
            <ClassificationBadge value={e.accessClassification} />
            <VerificationBadge status={e.verificationStatus} />
          </span>
        }
      />
      <Flash ok={sp(q.ok)} error={sp(q.error)} />
      <div className="grid gap-4 xl:grid-cols-3">
        <div className="space-y-4 xl:col-span-2">
          <Card title={e.title}>
            <h3 className="mb-2">Original excerpt (as collected)</h3>
            {readable ? (
              // Untrusted text: rendered as a text node, so any markup in it is shown, not executed.
              <blockquote className="whitespace-pre-wrap rounded-md border-l-2 border-cyan-300/40 bg-black/30 p-3 font-mono text-sm text-slate-100">{e.excerpt}</blockquote>
            ) : (
              <p className="muted">Excerpt withheld: {e.accessClassification.toLowerCase()} material is not shown to your role.</p>
            )}
          </Card>
          <Card title="Provenance">
            <dl>
              <Field label="Source">
                {e.source.title} {e.source.publisher ? <span className="muted">({e.source.publisher})</span> : null}
              </Field>
              <Field label="Source URL">
                <SourceLink url={e.url} />
              </Field>
              <Field label="Location in document">{e.documentLocation ?? <span className="muted">not supplied</span>}</Field>
              <Field label="Published">
                <When at={e.publishedAt} />
              </Field>
              <Field label="Observed">
                <When at={e.observedAt} />
              </Field>
              <Field label="Collected">
                <When at={e.collectedAt} />
              </Field>
              <Field label="Ingested">
                <When at={e.ingestedAt} />
              </Field>
              <Field label="Extraction method">{e.extractionMethod.replace(/_/g, " ").toLowerCase()}</Field>
              <Field label="Content hash">
                <code className="break-all text-xs">
                  {e.hashAlgorithm}:{e.contentHash}
                </code>
                <p className="muted mt-1 text-xs">{HASH_DISCLAIMER}</p>
              </Field>
              <Field label="Verification">
                <VerificationBadge status={e.verificationStatus} />{" "}
                {e.verifiedBy ? (
                  <span className="muted text-xs">
                    by {e.verifiedBy.name}, <When at={e.verifiedAt} />
                  </span>
                ) : null}
              </Field>
              <Field label="Limitations">{e.limitations ?? <span className="muted">none stated</span>}</Field>
              <Field label="Missing provenance">{e.missingFields.length ? e.missingFields.join(", ") : <span className="muted">none</span>}</Field>
            </dl>
          </Card>
          <Card title="Statements extracted from this evidence">
            {e.facts.length === 0 ? <p className="muted">None recorded.</p> : null}
            <ul className="space-y-2">
              {e.facts.map((f) => (
                <li key={f.id} className="flex flex-wrap items-start gap-2 text-sm">
                  <ClaimBadge status={f.claimStatus} /> <span>{f.statement}</span>
                </li>
              ))}
            </ul>
            {can(ctx.actor.role, "evidence:create") || can(ctx.actor.role, "evidence:verify") ? (
              <form action={addFactAction} className="mt-4 grid gap-2">
                <input type="hidden" name="evidenceId" value={e.id} />
                <label htmlFor="statement">Statement (what the excerpt says, not what it means)</label>
                <textarea id="statement" name="statement" required minLength={5} rows={2} />
                <label htmlFor="claimStatus">Status</label>
                <select id="claimStatus" name="claimStatus" defaultValue="SOURCE_SUPPORTED_OBSERVATION">
                  <option value="SOURCE_SUPPORTED_OBSERVATION">Source-supported observation</option>
                  <option value="ALLEGATION">Allegation (a claim the source reports)</option>
                  {can(ctx.actor.role, "evidence:verify") ? <option value="REVIEWED_FINDING">Reviewed finding</option> : null}
                </select>
                <div>
                  <button className="btn-quiet" type="submit">
                    Record statement
                  </button>
                </div>
              </form>
            ) : null}
          </Card>
        </div>
        <div className="space-y-4">
          <Card title="Used by">
            <h3 className="mb-1">Rules</h3>
            {rules.size === 0 ? (
              <p className="muted mb-3">No rule cites this evidence.</p>
            ) : (
              <ul className="mb-3 text-sm">
                {[...rules.values()].map((v) => (
                  <li key={v.id}>
                    <a href={`/rules/${v.ruleId}?v=${v.version}`}>
                      {v.rule.ruleKey} v{v.version}
                    </a>{" "}
                    <span className="muted">({v.status.toLowerCase()})</span>
                  </li>
                ))}
              </ul>
            )}
            <h3 className="mb-1">Incidents</h3>
            {e.incidents.length === 0 ? (
              <p className="muted mb-3">None.</p>
            ) : (
              <ul className="mb-3 text-sm">
                {e.incidents.map((i) => (
                  <li key={i.incidentId}>
                    <a href={`/incidents/${i.incidentId}`}>{i.incident.recordId}</a>
                  </li>
                ))}
              </ul>
            )}
            <h3 className="mb-1">Records and notes</h3>
            <ul className="text-sm">
              {e.transactions.map((t) => (
                <li key={t.id}>
                  <code>{t.recordId}</code> <span className="muted">({t.type.toLowerCase()})</span>
                </li>
              ))}
              {e.noteLinks.map((n) => (
                <li key={n.noteId}>
                  Note in <a href={`/investigations/${n.note.investigation.id}`}>{n.note.investigation.caseKey}</a>
                </li>
              ))}
              {e.transactions.length + e.noteLinks.length === 0 ? <li className="muted">None.</li> : null}
            </ul>
          </Card>
          {can(ctx.actor.role, "evidence:verify") ? (
            <Card title="Verification decision">
              <form action={verifyEvidenceAction} className="grid gap-2">
                <input type="hidden" name="evidenceId" value={e.id} />
                <label htmlFor="status">Status</label>
                <select id="status" name="status" defaultValue={e.verificationStatus}>
                  <option value="UNVERIFIED">Unverified</option>
                  <option value="PARTIALLY_VERIFIED">Partially verified</option>
                  <option value="VERIFIED">Verified (the excerpt matches the source)</option>
                  <option value="DISPUTED">Disputed</option>
                  <option value="REJECTED">Rejected</option>
                </select>
                <RationaleField id="verify-rationale" label="How you checked it (required)" />
                <div>
                  <button className="btn" type="submit">
                    Record verification
                  </button>
                </div>
              </form>
            </Card>
          ) : null}
          <Card title="Verification history">
            {decisions.length === 0 ? (
              <p className="muted">No decisions.</p>
            ) : (
              <ol className="space-y-2 text-sm">
                {decisions.map((d) => (
                  <li key={d.id}>
                    {d.fromState?.toLowerCase()} → <strong>{d.toState.toLowerCase()}</strong>{" "}
                    <span className="muted text-xs">
                      {d.decidedBy.name}, <When at={d.createdAt} />
                    </span>
                    <p>{d.rationale}</p>
                  </li>
                ))}
              </ol>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
