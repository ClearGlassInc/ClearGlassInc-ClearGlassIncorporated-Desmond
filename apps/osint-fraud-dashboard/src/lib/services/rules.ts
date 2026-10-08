import type { Prisma, Transaction } from "@/generated/prisma/client";
import { evaluateRule, type EvaluationResult } from "../rules/engine";
import { RECORD_FIELDS, type RecordField, type RecordView, type TransactionTypeName } from "../rules/records";
import { citedRecordIds, conditionSupport, formatIssues, ruleDefinitionSchema, type RuleDefinition } from "../rules/schema";
import { sha256 } from "../hash";
import { ForbiddenError, NotFoundError, ValidationError } from "../errors";
import { audit, now, requirePermission, type Ctx } from "./context";

export function parseDefinition(input: unknown): RuleDefinition {
  const parsed = ruleDefinitionSchema.safeParse(input);
  if (!parsed.success) throw new ValidationError("Rule definition is invalid", formatIssues(parsed.error));
  return parsed.data;
}

export function parseDefinitionText(text: string): RuleDefinition {
  let json: unknown;
  try {
    json = JSON.parse(text);
  } catch (e) {
    throw new ValidationError("Rule definition is not valid JSON", [e instanceof Error ? e.message : String(e)]);
  }
  return parseDefinition(json);
}

type Tx = Prisma.TransactionClient;

/** Resolve every cited evidence/incident record id, or refuse the rule. */
async function resolveCitations(tx: Tx, def: RuleDefinition) {
  const cited = citedRecordIds(def);
  const evidence = await tx.evidence.findMany({ where: { recordId: { in: cited.evidenceIds } }, select: { id: true, recordId: true } });
  const incidents = await tx.incident.findMany({ where: { recordId: { in: cited.incidentIds } }, select: { id: true, recordId: true } });
  const evMap = new Map(evidence.map((e) => [e.recordId, e.id]));
  const incMap = new Map(incidents.map((i) => [i.recordId, i.id]));
  const missing = [
    ...cited.evidenceIds.filter((id) => !evMap.has(id)).map((id) => `evidence "${id}" does not exist`),
    ...cited.incidentIds.filter((id) => !incMap.has(id)).map((id) => `incident "${id}" does not exist`),
  ];
  if (missing.length) throw new ValidationError("Rule cites records that are not in the workspace", missing);
  return { evMap, incMap };
}

function supportRows(def: RuleDefinition, evMap: Map<string, string>, incMap: Map<string, string>) {
  const rows: { conditionId: string | null; evidenceId: string | null; incidentId: string | null }[] = [];
  for (const id of def.supportingEvidenceIds) rows.push({ conditionId: null, evidenceId: evMap.get(id)!, incidentId: null });
  for (const id of def.supportingIncidentIds) rows.push({ conditionId: null, evidenceId: null, incidentId: incMap.get(id)! });
  for (const c of conditionSupport(def.pattern)) {
    for (const id of c.support.evidenceIds) rows.push({ conditionId: c.id, evidenceId: evMap.get(id)!, incidentId: null });
    for (const id of c.support.incidentIds) rows.push({ conditionId: c.id, evidenceId: null, incidentId: incMap.get(id)! });
  }
  for (const [name, t] of Object.entries(def.thresholds)) {
    for (const id of t.evidenceIds) rows.push({ conditionId: `threshold:${name}`, evidenceId: evMap.get(id)!, incidentId: null });
  }
  return rows;
}

/** Create a rule and its first version, pending approval. */
export async function createRule(
  ctx: Ctx,
  input: { definition: unknown; changeSummary: string; isSynthetic?: boolean },
): Promise<{ ruleId: string; versionId: string }> {
  await requirePermission(ctx, "rule:propose", { type: "DetectionRule" });
  const def = parseDefinition(input.definition);
  if (input.changeSummary.trim().length < 5) throw new ValidationError("Describe the change", ["changeSummary: at least 5 characters"]);
  return ctx.db.$transaction(async (tx) => {
    if (await tx.detectionRule.findUnique({ where: { ruleKey: def.ruleKey } })) {
      throw new ValidationError(`Rule ${def.ruleKey} already exists; propose a new version of it instead`);
    }
    const { evMap, incMap } = await resolveCitations(tx, def);
    const rule = await tx.detectionRule.create({
      data: {
        ruleKey: def.ruleKey,
        name: def.name,
        description: def.description,
        isIllustrative: def.illustrative,
        isSynthetic: input.isSynthetic ?? false,
      },
    });
    const version = await tx.ruleVersion.create({
      data: {
        ruleId: rule.id,
        version: 1,
        definition: def as unknown as Prisma.InputJsonValue,
        changeSummary: input.changeSummary.trim(),
        status: "PENDING_APPROVAL",
        proposedById: ctx.actor.id,
        support: { create: supportRows(def, evMap, incMap) },
      },
    });
    await audit(tx, ctx.actor, "rule.create", { type: "RuleVersion", id: version.id }, { ruleKey: def.ruleKey, version: 1 });
    return { ruleId: rule.id, versionId: version.id };
  });
}

/** Propose a new version. Earlier versions, and the alerts they produced, are kept. */
export async function proposeVersion(
  ctx: Ctx,
  ruleId: string,
  input: { definition: unknown; changeSummary: string },
): Promise<{ versionId: string; version: number }> {
  await requirePermission(ctx, "rule:propose", { type: "DetectionRule", id: ruleId });
  const def = parseDefinition(input.definition);
  if (input.changeSummary.trim().length < 5) throw new ValidationError("Describe the change", ["changeSummary: at least 5 characters"]);
  return ctx.db.$transaction(async (tx) => {
    const rule = await tx.detectionRule.findUnique({ where: { id: ruleId }, include: { versions: { orderBy: { version: "desc" }, take: 1 } } });
    if (!rule) throw new NotFoundError("Rule not found");
    if (def.ruleKey !== rule.ruleKey) throw new ValidationError(`ruleKey must stay ${rule.ruleKey}`);
    const { evMap, incMap } = await resolveCitations(tx, def);
    const next = (rule.versions[0]?.version ?? 0) + 1;
    const version = await tx.ruleVersion.create({
      data: {
        ruleId,
        version: next,
        definition: def as unknown as Prisma.InputJsonValue,
        changeSummary: input.changeSummary.trim(),
        status: "PENDING_APPROVAL",
        proposedById: ctx.actor.id,
        support: { create: supportRows(def, evMap, incMap) },
      },
    });
    await tx.detectionRule.update({ where: { id: ruleId }, data: { name: def.name, description: def.description, isIllustrative: def.illustrative } });
    await audit(tx, ctx.actor, "rule.version.propose", { type: "RuleVersion", id: version.id }, { ruleKey: rule.ruleKey, version: next });
    return { versionId: version.id, version: next };
  });
}

/**
 * Approve or reject a pending version. The proposer can never approve their own
 * version, whatever their role. Approval supersedes the previously active version.
 */
export async function decideVersion(
  ctx: Ctx,
  versionId: string,
  decision: "APPROVE" | "REJECT",
  rationale: string,
): Promise<void> {
  await requirePermission(ctx, "rule:approve", { type: "RuleVersion", id: versionId });
  if (rationale.trim().length < 10) throw new ValidationError("A rationale of at least 10 characters is required");
  const v = await ctx.db.ruleVersion.findUnique({ where: { id: versionId }, include: { rule: true } });
  if (!v) throw new NotFoundError("Rule version not found");
  if (v.status !== "PENDING_APPROVAL") throw new ValidationError(`Version is ${v.status}, not pending approval`);
  if (v.proposedById === ctx.actor.id) {
    await audit(ctx.db, ctx.actor, "security.access_denied", { type: "RuleVersion", id: versionId }, { reason: "self-approval" }, "denied");
    throw new ForbiddenError("Separation of duties: the proposer of a rule version cannot approve or reject it");
  }
  const at = now(ctx);
  await ctx.db.$transaction(async (tx) => {
    if (decision === "APPROVE") {
      await tx.ruleVersion.updateMany({ where: { ruleId: v.ruleId, status: "ACTIVE" }, data: { status: "SUPERSEDED" } });
    }
    const to = decision === "APPROVE" ? "ACTIVE" : "REJECTED";
    await tx.ruleVersion.update({
      where: { id: versionId },
      data: { status: to, approvedById: ctx.actor.id, approvedAt: at, approvalRationale: rationale.trim() },
    });
    await tx.reviewDecision.create({
      data: {
        targetType: "RULE_VERSION",
        targetId: versionId,
        fromState: v.status,
        toState: to,
        rationale: rationale.trim(),
        ruleVersionId: versionId,
        decidedById: ctx.actor.id,
      },
    });
    await audit(tx, ctx.actor, decision === "APPROVE" ? "rule.version.approve" : "rule.version.reject", { type: "RuleVersion", id: versionId }, {
      ruleKey: v.rule.ruleKey,
      version: v.version,
    });
  });
}

export async function retireVersion(ctx: Ctx, versionId: string, rationale: string): Promise<void> {
  await requirePermission(ctx, "rule:approve", { type: "RuleVersion", id: versionId });
  if (rationale.trim().length < 10) throw new ValidationError("A rationale of at least 10 characters is required");
  const v = await ctx.db.ruleVersion.findUnique({ where: { id: versionId }, include: { rule: true } });
  if (!v) throw new NotFoundError("Rule version not found");
  if (v.status !== "ACTIVE") throw new ValidationError("Only an active version can be retired");
  await ctx.db.$transaction(async (tx) => {
    await tx.ruleVersion.update({ where: { id: versionId }, data: { status: "RETIRED" } });
    await tx.reviewDecision.create({
      data: { targetType: "RULE_VERSION", targetId: versionId, fromState: "ACTIVE", toState: "RETIRED", rationale: rationale.trim(), ruleVersionId: versionId, decidedById: ctx.actor.id },
    });
    await audit(tx, ctx.actor, "rule.version.retire", { type: "RuleVersion", id: versionId }, { ruleKey: v.rule.ruleKey, version: v.version });
  });
}

// ---------------------------------------------------------------- evaluation

export function toRecordView(t: Transaction): RecordView {
  const provided = new Set(t.providedFields.filter((f): f is RecordField => (RECORD_FIELDS as readonly string[]).includes(f)));
  return {
    id: t.id,
    recordId: t.recordId,
    type: t.type as TransactionTypeName,
    values: {
      vendorRecordId: t.vendorRecordId,
      amount: t.amount === null ? null : Number(t.amount.toString()),
      currency: t.currency,
      occurredAt: t.occurredAt,
      recordedAt: t.recordedAt,
      approvedAt: t.approvedAt,
      workStartedAt: t.workStartedAt,
      approvedBy: t.approvedBy,
      poReference: t.poReference,
      invoiceReference: t.invoiceReference,
      documents: t.documents,
      description: t.description,
    },
    provided,
    evidenceRecordId: null,
    isSynthetic: t.isSynthetic,
  };
}

async function loadRecords(ctx: Ctx): Promise<RecordView[]> {
  const rows = await ctx.db.transaction.findMany({ orderBy: { recordId: "asc" }, include: { evidence: { select: { recordId: true } } } });
  return rows.map((t) => ({ ...toRecordView(t), evidenceRecordId: t.evidence?.recordId ?? null }));
}

/** Evaluate a version without creating alerts. Lets reviewers see what a pending version would do. */
export async function previewVersion(ctx: Ctx, versionId: string): Promise<{ results: EvaluationResult[]; outOfScope: number }> {
  await requirePermission(ctx, "workspace:view", { type: "RuleVersion", id: versionId });
  const v = await ctx.db.ruleVersion.findUnique({ where: { id: versionId } });
  if (!v) throw new NotFoundError("Rule version not found");
  const def = parseDefinition(v.definition);
  return evaluateRule(def, { ruleVersionId: v.id, version: v.version }, await loadRecords(ctx), now(ctx));
}

export interface RunSummary {
  runId: string;
  rules: number;
  results: Record<"MATCH" | "NO_MATCH" | "INSUFFICIENT_DATA", number>;
  alertsCreated: number;
  alertsExisting: number;
  outOfScope: number;
}

/** Evaluate every ACTIVE rule version against all transactions. Only approved rules run. */
export async function runEvaluation(ctx: Ctx): Promise<RunSummary> {
  await requirePermission(ctx, "rule:evaluate", { type: "EvaluationRun" });
  const versions = await ctx.db.ruleVersion.findMany({ where: { status: "ACTIVE" }, include: { rule: true }, orderBy: { createdAt: "asc" } });
  const records = await loadRecords(ctx);
  const byRecordId = new Map(records.map((r) => [r.recordId, r]));
  const at = now(ctx);
  const run = await ctx.db.evaluationRun.create({ data: { triggeredById: ctx.actor.id, startedAt: at } });
  const summary: RunSummary = { runId: run.id, rules: versions.length, results: { MATCH: 0, NO_MATCH: 0, INSUFFICIENT_DATA: 0 }, alertsCreated: 0, alertsExisting: 0, outOfScope: 0 };

  for (const v of versions) {
    const def = parseDefinition(v.definition);
    const out = evaluateRule(def, { ruleVersionId: v.id, version: v.version }, records, at);
    summary.outOfScope += out.outOfScope;
    for (const r of out.results) {
      summary.results[r.outcome] += 1;
      const created = await storeResult(ctx, run.id, v.ruleId, v.rule.isSynthetic, def, r, byRecordId);
      if (created === "created") summary.alertsCreated += 1;
      if (created === "existing") summary.alertsExisting += 1;
    }
  }
  await ctx.db.evaluationRun.update({ where: { id: run.id }, data: { finishedAt: now(ctx), summary: summary as unknown as Prisma.InputJsonValue } });
  await audit(ctx.db, ctx.actor, "rule.evaluate", { type: "EvaluationRun", id: run.id }, summary as unknown as Prisma.InputJsonValue);
  return summary;
}

export function alertDedupeKey(r: EvaluationResult): string {
  return sha256([r.ruleVersionId, r.outcome, r.subjectKey, ...r.matchedRecordIds].join("|"));
}

async function storeResult(
  ctx: Ctx,
  runId: string,
  ruleId: string,
  ruleIsSynthetic: boolean,
  def: RuleDefinition,
  r: EvaluationResult,
  byRecordId: Map<string, RecordView>,
): Promise<"created" | "existing" | "none"> {
  const evaluation = await ctx.db.ruleEvaluation.create({
    data: {
      runId,
      ruleVersionId: r.ruleVersionId,
      subjectKey: r.subjectKey,
      outcome: r.outcome,
      matchedRecordIds: r.matchedRecordIds,
      conditions: r.conditions as unknown as Prisma.InputJsonValue,
      missingFields: r.missingFields as unknown as Prisma.InputJsonValue,
      evidenceRefs: r.evidenceRefs,
      explanation: r.explanation,
      evaluatedAt: new Date(r.evaluatedAt),
    },
  });
  if (r.outcome === "NO_MATCH") return "none";
  const dedupeKey = alertDedupeKey(r);
  if (await ctx.db.alert.findUnique({ where: { dedupeKey }, select: { id: true } })) return "existing";
  const isSynthetic = ruleIsSynthetic || r.matchedRecordIds.some((id) => byRecordId.get(id)?.isSynthetic);
  const alert = await ctx.db.alert.create({
    data: {
      ruleId,
      ruleVersionId: r.ruleVersionId,
      evaluationId: evaluation.id,
      outcome: r.outcome,
      // Insufficient data is never cleared silently: it waits for evidence.
      status: r.outcome === "MATCH" ? "NEW" : "NEEDS_EVIDENCE",
      priority: def.reviewPriority,
      subjectKey: r.subjectKey,
      explanation: r.explanation,
      matchedRecordIds: r.matchedRecordIds,
      missingFields: r.missingFields as unknown as Prisma.InputJsonValue,
      conditions: r.conditions as unknown as Prisma.InputJsonValue,
      evidenceRefs: r.evidenceRefs,
      isSynthetic,
      dedupeKey,
    },
  });
  await audit(ctx.db, ctx.actor, "alert.create", { type: "Alert", id: alert.id }, { ruleKey: r.ruleKey, version: r.ruleVersion, outcome: r.outcome });
  return "created";
}
