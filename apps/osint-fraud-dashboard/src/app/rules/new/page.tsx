import { readFileSync } from "node:fs";
import { join } from "node:path";
import { redirect } from "next/navigation";
import { requireCtx } from "@/lib/auth/server";
import { can } from "@/lib/auth/roles";
import { draftFromIncident } from "@/lib/rules/draft";
import { Card, Flash, PageHeader, sp } from "@/components/ui";
import { createRuleAction } from "../../actions";

type Search = Promise<Record<string, string | string[] | undefined>>;

export default async function NewRulePage({ searchParams }: { searchParams: Search }) {
  const ctx = await requireCtx();
  if (!can(ctx.actor.role, "rule:propose")) redirect("/rules?error=" + encodeURIComponent("Your role cannot propose rules"));
  const q = await searchParams;
  const incidentId = sp(q.incident);
  let draft: unknown;
  let from = "the CG-T-003 template (edit the ruleKey before submitting)";
  if (incidentId && /^[a-z0-9]+$/i.test(incidentId)) {
    const inc = await ctx.db.incident.findUnique({ where: { id: incidentId }, include: { evidence: { include: { evidence: { select: { recordId: true } } } } } });
    if (inc) {
      draft = draftFromIncident(inc, inc.evidence.map((e) => e.evidence.recordId).sort());
      from = `incident ${inc.recordId}. Replace every TODO: the rule is refused until you do`;
    }
  }
  draft ??= JSON.parse(readFileSync(join(process.cwd(), "rules", "templates", "cg-t-003.v1.json"), "utf8"));

  return (
    <>
      <PageHeader
        title="Propose a rule"
        subtitle="Write the rule as JSON. Every condition must cite evidence, an incident, or an explicitly stated analyst assumption; every threshold needs a rationale. The rule stays inactive until a different reviewer approves it."
      />
      <Flash ok={sp(q.ok)} error={sp(q.error)} />
      <Card>
        <p className="muted mb-3">Started from {from}.</p>
        <form action={createRuleAction} className="grid gap-3">
          <label htmlFor="definition">Definition (JSON)</label>
          <textarea id="definition" name="definition" rows={28} className="font-mono text-xs" defaultValue={JSON.stringify(draft, null, 2)} />
          <label htmlFor="changeSummary">Summary of this proposal</label>
          <input id="changeSummary" name="changeSummary" required minLength={5} />
          <div>
            <button className="btn" type="submit">
              Submit for approval
            </button>
          </div>
        </form>
      </Card>
    </>
  );
}
