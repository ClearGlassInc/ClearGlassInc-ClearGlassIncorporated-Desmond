import { HASH_DISCLAIMER } from "../hash";
import { NotFoundError } from "../errors";
import { NOT_A_CLEARANCE, NOT_A_FINDING } from "../rules/engine";
import { redactExport, type InvestigationExport } from "../export/redact";
import { audit, now, requirePermission, type Ctx } from "./context";

export async function exportInvestigation(ctx: Ctx, investigationId: string, mode: "redacted" | "unredacted"): Promise<InvestigationExport> {
  await requirePermission(ctx, mode === "redacted" ? "export:redacted" : "export:unredacted", { type: "Investigation", id: investigationId });
  const inv = await ctx.db.investigation.findUnique({
    where: { id: investigationId },
    include: {
      owner: true,
      alerts: { include: { rule: true, ruleVersion: true }, orderBy: { createdAt: "asc" } },
      notes: { include: { author: true, evidence: { include: { evidence: true } } }, orderBy: { createdAt: "asc" } },
    },
  });
  if (!inv) throw new NotFoundError("Investigation not found");

  const alertIds = inv.alerts.map((a) => a.id);
  const decisions = await ctx.db.reviewDecision.findMany({
    where: { OR: [{ targetType: "INVESTIGATION", targetId: inv.id }, { targetType: "ALERT", targetId: { in: alertIds } }] },
    include: { decidedBy: true },
    orderBy: { createdAt: "asc" },
  });
  const evidenceIds = new Set([...inv.alerts.flatMap((a) => a.evidenceRefs), ...inv.notes.flatMap((n) => n.evidence.map((e) => e.evidence.recordId))]);
  const evidence = await ctx.db.evidence.findMany({ where: { recordId: { in: [...evidenceIds] } }, orderBy: { recordId: "asc" } });
  const txIds = [...new Set(inv.alerts.flatMap((a) => a.matchedRecordIds))];
  const transactions = await ctx.db.transaction.findMany({ where: { recordId: { in: txIds } }, orderBy: { recordId: "asc" } });

  const full: InvestigationExport = {
    exportVersion: 1,
    generatedAt: now(ctx).toISOString(),
    redaction: { mode: "unredacted", applied: [], notice: "Unredacted export. Handle under your data-protection obligations." },
    disclaimers: [
      NOT_A_FINDING,
      `No-match results are not included as clearances. ${NOT_A_CLEARANCE}`,
      HASH_DISCLAIMER,
      "Prototype export. Statuses marked ALLEGATION or ANALYST_INTERPRETATION are not established facts.",
    ],
    containsSyntheticData: inv.isSynthetic || inv.alerts.some((a) => a.isSynthetic) || evidence.some((e) => e.isSynthetic),
    investigation: {
      caseKey: inv.caseKey,
      title: inv.title,
      summary: inv.summary,
      status: inv.status,
      claimStatus: inv.claimStatus,
      owner: { label: inv.owner.name, role: inv.owner.role },
    },
    alerts: inv.alerts.map((a) => ({
      ruleKey: a.rule.ruleKey,
      ruleVersion: a.ruleVersion.version,
      outcome: a.outcome,
      status: a.status,
      explanation: a.explanation,
      matchedRecordIds: a.matchedRecordIds,
      evidenceRefs: a.evidenceRefs,
    })),
    notes: inv.notes.map((n) => ({
      kind: n.kind,
      body: n.body,
      author: { label: n.author.name, role: n.author.role },
      createdAt: n.createdAt.toISOString(),
      evidenceRecordIds: n.evidence.map((e) => e.evidence.recordId),
    })),
    decisions: decisions.map((d) => ({
      target: `${d.targetType}:${d.targetId}`,
      from: d.fromState,
      to: d.toState,
      rationale: d.rationale,
      decidedBy: { label: d.decidedBy.name, role: d.decidedBy.role },
      at: d.createdAt.toISOString(),
    })),
    evidence: evidence.map((e) => ({
      recordId: e.recordId,
      title: e.title,
      excerpt: e.excerpt,
      url: e.url,
      accessClassification: e.accessClassification,
      verificationStatus: e.verificationStatus,
      contentHash: e.contentHash,
      isSynthetic: e.isSynthetic,
      origin: e.origin,
    })),
    transactions: transactions.map((t) => ({
      recordId: t.recordId,
      type: t.type,
      vendorRecordId: t.vendorRecordId,
      approvedBy: t.approvedBy,
      description: t.description,
    })),
  };

  const out = mode === "redacted" ? redactExport(full) : full;
  await audit(ctx.db, ctx.actor, "export.investigation", { type: "Investigation", id: inv.id }, { mode, caseKey: inv.caseKey });
  return out;
}
