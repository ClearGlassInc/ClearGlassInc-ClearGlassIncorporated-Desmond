import { notFound } from "next/navigation";
import { requireCtx } from "@/lib/auth/server";
import { can } from "@/lib/auth/roles";
import { conditionSupport } from "@/lib/rules/schema";
import { parseDefinition, previewVersion } from "@/lib/services/rules";
import { RationaleField } from "@/components/forms";
import { IllustrativeBadge, OutcomeBadge, RuleStatusBadge, SyntheticBadge } from "@/components/labels";
import { Card, Field, Flash, Json, PageHeader, sp, When } from "@/components/ui";
import { decideVersionAction, proposeVersionAction, retireVersionAction } from "../../actions";

type Params = Promise<{ id: string }>;
type Search = Promise<Record<string, string | string[] | undefined>>;

export default async function RulePage({ params, searchParams }: { params: Params; searchParams: Search }) {
  const ctx = await requireCtx();
  const { id } = await params;
  const q = await searchParams;
  const rule = await ctx.db.detectionRule.findUnique({
    where: { id },
    include: { versions: { include: { proposedBy: true, approvedBy: true }, orderBy: { version: "desc" } } },
  });
  if (!rule) notFound();
  const wanted = Number(sp(q.v));
  const version = rule.versions.find((v) => v.version === wanted) ?? rule.versions.find((v) => v.status === "ACTIVE") ?? rule.versions[0];
  const def = parseDefinition(version.definition);
  const support = conditionSupport(def.pattern);
  const [evidence, incidents, decisions] = await Promise.all([
    ctx.db.evidence.findMany({ where: { ruleSupport: { some: { ruleVersionId: version.id } } }, select: { id: true, recordId: true } }),
    ctx.db.incident.findMany({ where: { ruleSupport: { some: { ruleVersionId: version.id } } }, select: { id: true, recordId: true } }),
    ctx.db.reviewDecision.findMany({ where: { targetType: "RULE_VERSION", targetId: { in: rule.versions.map((v) => v.id) } }, include: { decidedBy: true }, orderBy: { createdAt: "asc" } }),
  ]);
  const evLink = new Map(evidence.map((e) => [e.recordId, e.id]));
  const incLink = new Map(incidents.map((i) => [i.recordId, i.id]));
  const preview = version.status === "PENDING_APPROVAL" ? await previewVersion(ctx, version.id) : null;
  const canDecide = can(ctx.actor.role, "rule:approve") && version.proposedById !== ctx.actor.id;
  const editing = sp(q.edit) === "1" && can(ctx.actor.role, "rule:propose");

  const cite = (ids: string[], links: Map<string, string>, base: string) =>
    ids.map((x, i) => (
      <span key={x}>
        {i ? ", " : ""}
        {links.has(x) ? <a href={`/${base}/${links.get(x)}`}>{x}</a> : <code>{x}</code>}
      </span>
    ));

  return (
    <>
      <PageHeader
        title={`${rule.ruleKey} v${version.version}`}
        subtitle={
          <span className="flex flex-wrap items-center gap-2">
            <RuleStatusBadge status={version.status} />
            <IllustrativeBadge illustrative={def.illustrative} />
            <SyntheticBadge synthetic={rule.isSynthetic} />
            <span className="muted">Review priority: {def.reviewPriority.toLowerCase()} (not a probability)</span>
          </span>
        }
        actions={
          can(ctx.actor.role, "rule:propose") ? (
            <a className="btn-quiet" href={`/rules/${rule.id}?v=${version.version}&edit=1`}>
              Propose a new version
            </a>
          ) : null
        }
      />
      <Flash ok={sp(q.ok)} error={sp(q.error)} />
      {def.disclaimer ? (
        <div role="note" className="mb-4 rounded-lg border border-violet-300/30 bg-violet-300/10 px-4 py-3 text-sm text-violet-100">
          {def.disclaimer}
        </div>
      ) : null}
      <div className="grid gap-4 xl:grid-cols-3">
        <div className="space-y-4 xl:col-span-2">
          <Card title={def.name}>
            <p>{def.description}</p>
            <dl className="mt-3">
              <Field label="Pattern">{def.pattern.kind.replace(/_/g, " ")}</Field>
              <Field label="Required input fields">{def.requiredFields.join(", ")}</Field>
              <Field label="Entity matching">
                {def.entityMatching === "explicit_vendor_record_id" ? "Explicit vendor record id only (names are never used)" : "Each record on its own"}
              </Field>
              <Field label="Missing data">Returns INSUFFICIENT_DATA; never treated as a negative</Field>
              <Field label="Supporting incidents">{def.supportingIncidentIds.length ? cite(def.supportingIncidentIds, incLink, "incidents") : <span className="muted">none</span>}</Field>
              <Field label="Supporting evidence">{def.supportingEvidenceIds.length ? cite(def.supportingEvidenceIds, evLink, "evidence") : <span className="muted">none</span>}</Field>
            </dl>
          </Card>

          <Card title="Conditions and what supports them">
            <div className="overflow-x-auto"><table>
              <thead>
                <tr>
                  <th scope="col">Condition</th>
                  <th scope="col">Supported by</th>
                </tr>
              </thead>
              <tbody>
                {support.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <code className="text-xs">{c.id}</code> {c.role === "applicability" ? <span className="muted text-xs">(scope)</span> : null}
                      <div>{c.description}</div>
                    </td>
                    <td className="text-sm">
                      {c.support.evidenceIds.length ? <div>Evidence: {cite(c.support.evidenceIds, evLink, "evidence")}</div> : null}
                      {c.support.incidentIds.length ? <div>Incident: {cite(c.support.incidentIds, incLink, "incidents")}</div> : null}
                      {c.support.assumption ? (
                        <div className="text-violet-200">
                          <strong>Analyst assumption:</strong> {c.support.assumption}
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table></div>
          </Card>

          <Card title="Thresholds">
            {Object.keys(def.thresholds).length === 0 ? (
              <p className="muted">This rule has no configurable thresholds.</p>
            ) : (
              <div className="overflow-x-auto"><table>
                <thead>
                  <tr>
                    <th scope="col">Name</th>
                    <th scope="col">Value</th>
                    <th scope="col">Basis</th>
                    <th scope="col">Rationale</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(def.thresholds).map(([name, t]) => (
                    <tr key={name}>
                      <td>
                        <code>{name}</code>
                      </td>
                      <td className="tabular-nums">
                        {t.value} {t.unit}
                      </td>
                      <td className="text-xs">
                        {t.basis.replace(/_/g, " ").toLowerCase()}
                        {t.evidenceIds.length ? <div>{cite(t.evidenceIds, evLink, "evidence")}</div> : null}
                      </td>
                      <td className="text-sm">{t.rationale}</td>
                    </tr>
                  ))}
                </tbody>
              </table></div>
            )}
          </Card>

          <div className="grid gap-4 md:grid-cols-2">
            <Card title="Known benign explanations">
              <ul className="list-inside list-disc text-sm">
                {def.benignExplanations.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </Card>
            <Card title="False-positive considerations">
              <ul className="list-inside list-disc text-sm">
                {def.falsePositiveConsiderations.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </Card>
          </div>

          {preview ? (
            <Card title="Preview against current records (no alerts created)">
              <p className="muted mb-2">
                {preview.results.filter((r) => r.outcome === "MATCH").length} match, {preview.results.filter((r) => r.outcome === "NO_MATCH").length} no match,{" "}
                {preview.results.filter((r) => r.outcome === "INSUFFICIENT_DATA").length} insufficient data, {preview.outOfScope} out of scope.
              </p>
              <ul className="space-y-2 text-sm">
                {preview.results
                  .filter((r) => r.outcome !== "NO_MATCH")
                  .map((r) => (
                    <li key={r.subjectKey}>
                      <OutcomeBadge outcome={r.outcome} /> {r.explanation}
                    </li>
                  ))}
              </ul>
            </Card>
          ) : null}

          {editing ? (
            <Card title="Propose a new version">
              <form action={proposeVersionAction} className="grid gap-3">
                <input type="hidden" name="ruleId" value={rule.id} />
                <label htmlFor="definition">Definition (JSON, validated on submit)</label>
                <textarea id="definition" name="definition" rows={24} className="font-mono text-xs" defaultValue={JSON.stringify(def, null, 2)} />
                <label htmlFor="changeSummary">What changed and why</label>
                <input id="changeSummary" name="changeSummary" required minLength={5} />
                <div>
                  <button className="btn" type="submit">
                    Submit for approval
                  </button>
                </div>
              </form>
            </Card>
          ) : (
            <Card title="Definition (JSON)">
              <Json value={def} />
            </Card>
          )}
        </div>

        <div className="space-y-4">
          <Card title="Versions">
            <ul className="space-y-3 text-sm">
              {rule.versions.map((v) => (
                <li key={v.id} className={v.id === version.id ? "rounded-md border border-cyan-300/30 p-2" : "p-2"}>
                  <a href={`/rules/${rule.id}?v=${v.version}`}>v{v.version}</a> <RuleStatusBadge status={v.status} />
                  <div className="muted text-xs">
                    Proposed by {v.proposedBy.name}, <When at={v.createdAt} />
                  </div>
                  <div>{v.changeSummary}</div>
                  {v.approvedBy ? (
                    <div className="muted text-xs">
                      Decided by {v.approvedBy.name}: {v.approvalRationale}
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          </Card>
          {version.status === "PENDING_APPROVAL" ? (
            <Card title="Approval (G)">
              {canDecide ? (
                <form action={decideVersionAction} className="grid gap-2">
                  <input type="hidden" name="ruleId" value={rule.id} />
                  <input type="hidden" name="versionId" value={version.id} />
                  <label htmlFor="decision">Decision</label>
                  <select id="decision" name="decision" defaultValue="APPROVE">
                    <option value="APPROVE">Approve and activate (supersedes the active version)</option>
                    <option value="REJECT">Reject</option>
                  </select>
                  <RationaleField id="approve-rationale" />
                  <div>
                    <button className="btn" type="submit">
                      Record decision
                    </button>
                  </div>
                </form>
              ) : (
                <p className="muted">
                  {version.proposedById === ctx.actor.id
                    ? "You proposed this version, so another reviewer must decide it."
                    : "A reviewer or administrator must approve this version before it runs."}
                </p>
              )}
            </Card>
          ) : null}
          {version.status === "ACTIVE" && can(ctx.actor.role, "rule:approve") ? (
            <Card title="Retire this version">
              <form action={retireVersionAction} className="grid gap-2">
                <input type="hidden" name="ruleId" value={rule.id} />
                <input type="hidden" name="versionId" value={version.id} />
                <RationaleField id="retire-rationale" />
                <div>
                  <button className="btn-quiet" type="submit">
                    Retire
                  </button>
                </div>
              </form>
            </Card>
          ) : null}
          <Card title="Approval history">
            {decisions.length === 0 ? (
              <p className="muted">No decisions.</p>
            ) : (
              <ol className="space-y-2 text-sm">
                {decisions.map((d) => (
                  <li key={d.id}>
                    v{rule.versions.find((v) => v.id === d.targetId)?.version}: {d.fromState?.toLowerCase().replace(/_/g, " ")} → <strong>{d.toState.toLowerCase()}</strong>
                    <div className="muted text-xs">
                      {d.decidedBy.name}, <When at={d.createdAt} />
                    </div>
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
