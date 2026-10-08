import { notFound } from "next/navigation";
import { requireCtx } from "@/lib/auth/server";
import { can } from "@/lib/auth/roles";
import { ClaimBadge, RuleStatusBadge, SyntheticBadge } from "@/components/labels";
import { Card, PageHeader, When } from "@/components/ui";

type Params = Promise<{ id: string }>;

const SECTIONS = [
  { key: "A", kinds: ["OBSERVATION"], title: "A. Documented observations" },
  { key: "B", kinds: ["ACTOR"], title: "B. Actors and entities (no unsupported attribution)" },
  { key: "C", kinds: ["EVENT"], title: "C. Supported event sequence" },
  { key: "D", kinds: ["EVIDENCE_GAP", "CONTRADICTION"], title: "D. Unavailable or contradictory evidence" },
] as const;

export default async function IncidentPage({ params }: { params: Params }) {
  const ctx = await requireCtx();
  const { id } = await params;
  const inc = await ctx.db.incident.findUnique({
    where: { id },
    include: {
      steps: { include: { evidence: { select: { id: true, recordId: true } } }, orderBy: { position: "asc" } },
      evidence: { include: { evidence: { select: { id: true, recordId: true, title: true, isSynthetic: true } } } },
      ruleSupport: { include: { ruleVersion: { include: { rule: true, approvedBy: true } } } },
    },
  });
  if (!inc) notFound();
  const versions = [...new Map(inc.ruleSupport.map((s) => [s.ruleVersion.id, s.ruleVersion])).values()].sort((a, b) => a.version - b.version);

  return (
    <>
      <PageHeader
        title={`${inc.recordId}: ${inc.title}`}
        subtitle={
          <span className="flex flex-wrap items-center gap-2">
            <SyntheticBadge synthetic={inc.isSynthetic} />
            <ClaimBadge status={inc.claimStatus} />
            <span className="muted">
              Documented <When at={inc.documentedAt} />
            </span>
          </span>
        }
        actions={
          can(ctx.actor.role, "rule:propose") ? (
            <a className="btn" href={`/rules/new?incident=${inc.id}`}>
              E. Propose a rule from this incident
            </a>
          ) : null
        }
      />
      <Card title="Summary" className="mb-4">
        <p className="whitespace-pre-wrap">{inc.summary}</p>
        <h3 className="mb-1 mt-4">Evidence attached</h3>
        <ul className="text-sm">
          {inc.evidence.map((e) => (
            <li key={e.evidenceId}>
              <a href={`/evidence/${e.evidence.id}`}>{e.evidence.recordId}</a> {e.evidence.title} <SyntheticBadge synthetic={e.evidence.isSynthetic} />
            </li>
          ))}
        </ul>
      </Card>
      <div className="grid gap-4 lg:grid-cols-2">
        {SECTIONS.map((s) => {
          const steps = inc.steps.filter((st) => (s.kinds as readonly string[]).includes(st.kind));
          return (
            <Card key={s.key} title={s.title}>
              {steps.length === 0 ? (
                <p className="muted">Nothing recorded.</p>
              ) : (
                <ol className="space-y-2 text-sm">
                  {steps.map((st) => (
                    <li key={st.id} className="border-l-2 border-white/10 pl-3">
                      {st.kind === "CONTRADICTION" ? <strong className="text-rose-200">Contradiction: </strong> : null}
                      {st.kind === "EVIDENCE_GAP" ? <strong className="text-amber-200">Gap: </strong> : null}
                      {st.text}
                      <div className="muted text-xs">
                        {st.occurredAt ? (
                          <>
                            <When at={st.occurredAt} /> -{" "}
                          </>
                        ) : null}
                        {st.evidence ? (
                          <>
                            cites <a href={`/evidence/${st.evidence.id}`}>{st.evidence.recordId}</a>
                          </>
                        ) : st.isAssumption ? (
                          <span className="text-violet-200">analyst assumption - no evidence cited</span>
                        ) : (
                          "no evidence available"
                        )}
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </Card>
          );
        })}
      </div>
      <Card title="E-G. Rules derived from this incident and their approval" className="mt-4">
        {versions.length === 0 ? (
          <p className="muted">No rule cites this incident yet. A proposed rule stays inactive until a reviewer approves it.</p>
        ) : (
          <div className="overflow-x-auto"><table>
            <thead>
              <tr>
                <th scope="col">Rule version</th>
                <th scope="col">Status (G)</th>
                <th scope="col">Approved by</th>
                <th scope="col">Change</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.id}>
                  <td>
                    <a href={`/rules/${v.ruleId}?v=${v.version}`}>
                      {v.rule.ruleKey} v{v.version}
                    </a>
                  </td>
                  <td>
                    <RuleStatusBadge status={v.status} />
                  </td>
                  <td>{v.approvedBy ? v.approvedBy.name : <span className="muted">not yet</span>}</td>
                  <td className="text-sm">{v.changeSummary}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        )}
        <p className="muted mt-3">The condition-to-evidence mapping (F) for each version is on the rule page.</p>
      </Card>
    </>
  );
}
