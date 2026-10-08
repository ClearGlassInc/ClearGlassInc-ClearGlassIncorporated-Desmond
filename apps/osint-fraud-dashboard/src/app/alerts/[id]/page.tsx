import { notFound } from "next/navigation";
import { requireCtx } from "@/lib/auth/server";
import { can } from "@/lib/auth/roles";
import type { ConditionResult, MissingField } from "@/lib/rules/engine";
import { OPEN_STATES } from "@/lib/review";
import { DecisionForm } from "@/components/forms";
import { ClassificationBadge, OutcomeBadge, PriorityBadge, ReviewStateBadge, SyntheticBadge, VerificationBadge, stateLabel } from "@/components/labels";
import { Card, Field, Flash, Json, PageHeader, sp, When } from "@/components/ui";
import { createInvestigationAction, decideAlertAction, linkAlertAction } from "../../actions";

type Params = Promise<{ id: string }>;
type Search = Promise<Record<string, string | string[] | undefined>>;

const RESULT_TEXT: Record<string, string> = { TRUE: "met", FALSE: "not met", UNKNOWN: "unknown - data missing" };

export default async function AlertPage({ params, searchParams }: { params: Params; searchParams: Search }) {
  const ctx = await requireCtx();
  const { id } = await params;
  const q = await searchParams;
  const alert = await ctx.db.alert.findUnique({
    where: { id },
    include: { rule: true, ruleVersion: true, investigation: true, evaluation: true },
  });
  if (!alert) notFound();
  const conditions = alert.conditions as unknown as ConditionResult[];
  const missing = alert.missingFields as unknown as MissingField[];
  const [records, evidence, decisions, openCases] = await Promise.all([
    ctx.db.transaction.findMany({ where: { recordId: { in: alert.matchedRecordIds } }, orderBy: { recordId: "asc" } }),
    ctx.db.evidence.findMany({ where: { recordId: { in: alert.evidenceRefs } }, orderBy: { recordId: "asc" } }),
    ctx.db.reviewDecision.findMany({ where: { targetType: "ALERT", targetId: id }, include: { decidedBy: true }, orderBy: { createdAt: "asc" } }),
    ctx.db.investigation.findMany({ where: { status: { in: OPEN_STATES } }, orderBy: { caseKey: "asc" }, select: { id: true, caseKey: true, title: true } }),
  ]);

  return (
    <>
      <PageHeader
        title={`Alert ${alert.id.slice(-8)}`}
        subtitle={
          <span className="flex flex-wrap items-center gap-2">
            <OutcomeBadge outcome={alert.outcome} />
            <ReviewStateBadge state={alert.status} />
            <PriorityBadge priority={alert.priority} />
            <SyntheticBadge synthetic={alert.isSynthetic} />
          </span>
        }
      />
      <Flash ok={sp(q.ok)} error={sp(q.error)} />
      <div className="grid gap-4 xl:grid-cols-3">
        <div className="space-y-4 xl:col-span-2">
          <Card title="Explanation">
            <p className="text-slate-100">{alert.explanation}</p>
            <dl className="mt-3">
              <Field label="Rule">
                <a href={`/rules/${alert.ruleId}?v=${alert.ruleVersion.version}`}>
                  {alert.rule.ruleKey} v{alert.ruleVersion.version}
                </a>{" "}
                - {alert.rule.name}
              </Field>
              <Field label="Subject">
                <code>{alert.subjectKey}</code>
              </Field>
              <Field label="Evaluated">
                <When at={alert.evaluation.evaluatedAt} />
              </Field>
            </dl>
          </Card>

          <Card title="Evaluated conditions">
            <div className="overflow-x-auto">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Condition</th>
                    <th scope="col">Result</th>
                    <th scope="col">Expected</th>
                    <th scope="col">Actual values</th>
                  </tr>
                </thead>
                <tbody>
                  {conditions.map((c) => (
                    <tr key={c.id}>
                      <td>
                        <code className="text-xs">{c.id}</code>
                        <div>{c.description}</div>
                      </td>
                      <td className={c.result === "TRUE" ? "text-cyan-200" : c.result === "UNKNOWN" ? "text-amber-200" : "text-slate-400"}>{RESULT_TEXT[c.result]}</td>
                      <td className="text-xs">{c.expected}</td>
                      <td>
                        <Json value={c.actual} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {missing.length ? (
              <div className="mt-4">
                <h3 className="mb-2">Missing inputs</h3>
                <ul className="list-inside list-disc text-sm text-amber-100">
                  {missing.map((m) => (
                    <li key={`${m.recordId}.${m.field}`}>
                      <code>{m.recordId}</code>: <code>{m.field}</code> was not supplied by the source
                    </li>
                  ))}
                </ul>
                <p className="muted mt-2">Missing fields are not treated as negative facts. The records stay uncleared until the data is supplied.</p>
              </div>
            ) : null}
          </Card>

          <Card title="Matched records">
            <div className="overflow-x-auto">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Record</th>
                    <th scope="col">Type</th>
                    <th scope="col">Vendor id</th>
                    <th scope="col">Amount</th>
                    <th scope="col">Occurred</th>
                    <th scope="col">Fields not supplied</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <code>{r.recordId}</code> <SyntheticBadge synthetic={r.isSynthetic} />
                        {r.description ? <div className="muted text-xs">{r.description}</div> : null}
                      </td>
                      <td className="text-xs">{r.type}</td>
                      <td className="font-mono text-xs">{r.vendorRecordId ?? "not supplied"}</td>
                      <td className="tabular-nums">{r.amount ? `${r.amount.toString()} ${r.currency ?? ""}` : <span className="muted">not supplied</span>}</td>
                      <td className="text-xs">
                        <When at={r.occurredAt} />
                      </td>
                      <td className="text-xs">{r.missingFields.length ? r.missingFields.join(", ") : <span className="muted">none</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title="Supporting evidence">
            {evidence.length === 0 ? (
              <p className="muted">This alert cites no evidence records. Illustrative templates rest on stated analyst assumptions instead.</p>
            ) : (
              <ul className="space-y-2">
                {evidence.map((e) => (
                  <li key={e.id} className="flex flex-wrap items-center gap-2 text-sm">
                    <a href={`/evidence/${e.id}`}>{e.recordId}</a> {e.title} <SyntheticBadge synthetic={e.isSynthetic} />
                    <ClassificationBadge value={e.accessClassification} />
                    <VerificationBadge status={e.verificationStatus} />
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="space-y-4">
          <Card title="Review decision">
            <DecisionForm action={decideAlertAction} hidden={{ alertId: alert.id }} state={alert.status} role={ctx.actor.role} decidePermission="alert:decide" />
          </Card>
          <Card title="Investigation">
            {alert.investigation ? (
              <p>
                Part of <a href={`/investigations/${alert.investigation.id}`}>{alert.investigation.caseKey}</a> - {alert.investigation.title}
              </p>
            ) : can(ctx.actor.role, "investigation:create") || can(ctx.actor.role, "alert:triage") ? (
              <div className="space-y-4">
                {can(ctx.actor.role, "alert:triage") && openCases.length ? (
                  <form action={linkAlertAction} className="flex flex-col gap-2">
                    <input type="hidden" name="alertId" value={alert.id} />
                    <label htmlFor="investigationId">Add to an open case</label>
                    <select id="investigationId" name="investigationId">
                      {openCases.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.caseKey} - {c.title}
                        </option>
                      ))}
                    </select>
                    <button className="btn-quiet" type="submit">
                      Add to case
                    </button>
                  </form>
                ) : null}
                {can(ctx.actor.role, "investigation:create") ? (
                  <form action={createInvestigationAction} className="flex flex-col gap-2">
                    <input type="hidden" name="alertIds" value={alert.id} />
                    <label htmlFor="title">Open a new case</label>
                    <input id="title" name="title" required minLength={5} defaultValue={`${alert.rule.ruleKey}: ${alert.subjectKey}`} />
                    <label htmlFor="summary">Why open it</label>
                    <textarea id="summary" name="summary" required minLength={10} rows={2} />
                    <label htmlFor="priority">Priority</label>
                    <select id="priority" name="priority" defaultValue={alert.priority}>
                      <option value="LOW">Low</option>
                      <option value="MEDIUM">Medium</option>
                      <option value="HIGH">High</option>
                    </select>
                    <button className="btn" type="submit">
                      Open case
                    </button>
                  </form>
                ) : null}
              </div>
            ) : (
              <p className="muted">Not part of a case.</p>
            )}
          </Card>
          <Card title="Decision history">
            {decisions.length === 0 ? (
              <p className="muted">No decisions yet.</p>
            ) : (
              <ol className="space-y-3 text-sm">
                {decisions.map((d) => (
                  <li key={d.id} className="border-l-2 border-cyan-300/30 pl-3">
                    <div>
                      {stateLabel(d.fromState ?? "")} → <strong>{stateLabel(d.toState)}</strong>
                    </div>
                    <div className="muted text-xs">
                      {d.decidedBy.name} ({d.decidedBy.role.toLowerCase()}) - <When at={d.createdAt} />
                    </div>
                    <p className="mt-1">{d.rationale}</p>
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
