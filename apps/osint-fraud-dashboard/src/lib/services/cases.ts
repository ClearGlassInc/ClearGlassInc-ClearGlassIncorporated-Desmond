// Alerts and investigations: review decisions, notes, case creation.
// Nothing here contacts third parties, blocks payments or reports anyone.

import { NotFoundError, ValidationError } from "../errors";
import { isReviewState, MIN_RATIONALE, transitionLevel, type ReviewStateName } from "../review";
import { audit, now, requirePermission, type Ctx } from "./context";

async function checkTransition(
  ctx: Ctx,
  kind: "alert" | "investigation",
  id: string,
  from: ReviewStateName,
  toRaw: string,
  rationale: string,
): Promise<ReviewStateName> {
  if (!isReviewState(toRaw)) throw new ValidationError(`Unknown review state "${toRaw}"`);
  const level = transitionLevel(from, toRaw);
  if (!level) throw new ValidationError(`Cannot move from ${from} to ${toRaw}`);
  const permission = level === "triage" ? "alert:triage" : kind === "alert" ? "alert:decide" : "investigation:decide";
  await requirePermission(ctx, permission, { type: kind === "alert" ? "Alert" : "Investigation", id });
  if (rationale.trim().length < MIN_RATIONALE) {
    throw new ValidationError(`A rationale of at least ${MIN_RATIONALE} characters is required for this decision`);
  }
  return toRaw;
}

export async function decideAlert(ctx: Ctx, alertId: string, to: string, rationale: string): Promise<void> {
  await requirePermission(ctx, "workspace:view", { type: "Alert", id: alertId });
  const alert = await ctx.db.alert.findUnique({ where: { id: alertId } });
  if (!alert) throw new NotFoundError("Alert not found");
  const target = await checkTransition(ctx, "alert", alertId, alert.status, to, rationale);
  await ctx.db.$transaction(async (tx) => {
    // Optimistic check: a concurrent decision makes this one fail instead of overwriting it.
    const updated = await tx.alert.updateMany({ where: { id: alertId, status: alert.status }, data: { status: target } });
    if (updated.count !== 1) throw new ValidationError("The alert changed while you were deciding; reload and try again");
    await tx.reviewDecision.create({
      data: {
        targetType: "ALERT",
        targetId: alertId,
        fromState: alert.status,
        toState: target,
        rationale: rationale.trim(),
        ruleVersionId: alert.ruleVersionId,
        decidedById: ctx.actor.id,
      },
    });
    await audit(tx, ctx.actor, "alert.decide", { type: "Alert", id: alertId }, { from: alert.status, to: target });
  });
}

export async function decideInvestigation(ctx: Ctx, investigationId: string, to: string, rationale: string): Promise<void> {
  await requirePermission(ctx, "workspace:view", { type: "Investigation", id: investigationId });
  const inv = await ctx.db.investigation.findUnique({ where: { id: investigationId } });
  if (!inv) throw new NotFoundError("Investigation not found");
  const target = await checkTransition(ctx, "investigation", investigationId, inv.status, to, rationale);
  await ctx.db.$transaction(async (tx) => {
    const updated = await tx.investigation.updateMany({ where: { id: investigationId, status: inv.status }, data: { status: target } });
    if (updated.count !== 1) throw new ValidationError("The case changed while you were deciding; reload and try again");
    await tx.reviewDecision.create({
      data: { targetType: "INVESTIGATION", targetId: investigationId, fromState: inv.status, toState: target, rationale: rationale.trim(), decidedById: ctx.actor.id },
    });
    await audit(tx, ctx.actor, "investigation.decide", { type: "Investigation", id: investigationId }, { from: inv.status, to: target });
  });
}

async function nextCaseKey(ctx: Ctx): Promise<string> {
  const count = await ctx.db.investigation.count();
  for (let n = count + 1; ; n++) {
    const key = `CG-CASE-${String(n).padStart(4, "0")}`;
    if (!(await ctx.db.investigation.findUnique({ where: { caseKey: key }, select: { id: true } }))) return key;
  }
}

export async function createInvestigation(
  ctx: Ctx,
  input: { title: string; summary: string; priority: string; alertIds?: string[] },
): Promise<string> {
  await requirePermission(ctx, "investigation:create", { type: "Investigation" });
  const title = input.title.trim();
  const summary = input.summary.trim();
  if (title.length < 5) throw new ValidationError("A case title of at least 5 characters is required");
  if (summary.length < 10) throw new ValidationError("Summarise why the case is opened (at least 10 characters)");
  if (!["LOW", "MEDIUM", "HIGH"].includes(input.priority)) throw new ValidationError("Priority must be LOW, MEDIUM or HIGH");
  const alerts = input.alertIds?.length ? await ctx.db.alert.findMany({ where: { id: { in: input.alertIds } } }) : [];
  if (alerts.length !== (input.alertIds?.length ?? 0)) throw new ValidationError("One or more alerts do not exist");
  const caseKey = await nextCaseKey(ctx);
  return ctx.db.$transaction(async (tx) => {
    const inv = await tx.investigation.create({
      data: {
        caseKey,
        title,
        summary,
        priority: input.priority as "LOW" | "MEDIUM" | "HIGH",
        status: "NEW",
        // An open case is an inquiry. It becomes a reviewed finding only through a reviewer decision.
        claimStatus: "ANALYST_INTERPRETATION",
        ownerId: ctx.actor.id,
        isSynthetic: alerts.length > 0 && alerts.every((a) => a.isSynthetic),
      },
    });
    if (alerts.length) await tx.alert.updateMany({ where: { id: { in: alerts.map((a) => a.id) } }, data: { investigationId: inv.id } });
    await audit(tx, ctx.actor, "investigation.create", { type: "Investigation", id: inv.id }, { caseKey, alerts: alerts.map((a) => a.id) });
    return inv.id;
  });
}

export async function linkAlert(ctx: Ctx, alertId: string, investigationId: string): Promise<void> {
  await requirePermission(ctx, "alert:triage", { type: "Alert", id: alertId });
  const [alert, inv] = await Promise.all([
    ctx.db.alert.findUnique({ where: { id: alertId } }),
    ctx.db.investigation.findUnique({ where: { id: investigationId } }),
  ]);
  if (!alert || !inv) throw new NotFoundError("Alert or investigation not found");
  await ctx.db.alert.update({ where: { id: alertId }, data: { investigationId } });
  await audit(ctx.db, ctx.actor, "alert.link", { type: "Alert", id: alertId }, { investigationId });
}

/** Add a note. Evidence ids are verified; notes about interpretation are labelled as such. */
export async function addNote(
  ctx: Ctx,
  investigationId: string,
  input: { kind: string; body: string; evidenceRecordIds: string[] },
): Promise<string> {
  await requirePermission(ctx, "investigation:note", { type: "Investigation", id: investigationId });
  if (!["OBSERVATION", "INTERPRETATION", "QUESTION"].includes(input.kind)) throw new ValidationError("Note kind must be OBSERVATION, INTERPRETATION or QUESTION");
  const body = input.body.trim();
  if (body.length < 3 || body.length > 10_000) throw new ValidationError("A note is 3 to 10,000 characters");
  const ids = [...new Set(input.evidenceRecordIds.map((s) => s.trim()).filter(Boolean))];
  if (input.kind === "OBSERVATION" && ids.length === 0) {
    throw new ValidationError("An observation must cite at least one evidence record; use INTERPRETATION or QUESTION otherwise");
  }
  const evidence = await ctx.db.evidence.findMany({ where: { recordId: { in: ids } }, select: { id: true, recordId: true } });
  const unknown = ids.filter((id) => !evidence.some((e) => e.recordId === id));
  if (unknown.length) throw new ValidationError("Unknown evidence ids", unknown);
  const inv = await ctx.db.investigation.findUnique({ where: { id: investigationId }, select: { id: true } });
  if (!inv) throw new NotFoundError("Investigation not found");
  const note = await ctx.db.investigationNote.create({
    data: {
      investigationId,
      authorId: ctx.actor.id,
      kind: input.kind as "OBSERVATION" | "INTERPRETATION" | "QUESTION",
      body,
      evidence: { create: evidence.map((e) => ({ evidenceId: e.id })) },
    },
  });
  await audit(ctx.db, ctx.actor, "investigation.note", { type: "Investigation", id: investigationId }, { noteId: note.id, evidence: ids });
  return note.id;
}

/** Mark evidence verified/disputed/rejected. Reviewer-only and recorded as a decision. */
export async function verifyEvidence(ctx: Ctx, evidenceId: string, status: string, rationale: string): Promise<void> {
  await requirePermission(ctx, "evidence:verify", { type: "Evidence", id: evidenceId });
  if (!["UNVERIFIED", "PARTIALLY_VERIFIED", "VERIFIED", "DISPUTED", "REJECTED"].includes(status)) throw new ValidationError("Unknown verification status");
  if (rationale.trim().length < MIN_RATIONALE) throw new ValidationError(`A rationale of at least ${MIN_RATIONALE} characters is required`);
  const ev = await ctx.db.evidence.findUnique({ where: { id: evidenceId } });
  if (!ev) throw new NotFoundError("Evidence not found");
  const s = status as "UNVERIFIED" | "PARTIALLY_VERIFIED" | "VERIFIED" | "DISPUTED" | "REJECTED";
  await ctx.db.$transaction(async (tx) => {
    await tx.evidence.update({ where: { id: evidenceId }, data: { verificationStatus: s, verifiedById: ctx.actor.id, verifiedAt: now(ctx) } });
    await tx.reviewDecision.create({
      data: { targetType: "EVIDENCE", targetId: evidenceId, fromState: ev.verificationStatus, toState: s, rationale: rationale.trim(), decidedById: ctx.actor.id },
    });
    await audit(tx, ctx.actor, "evidence.verify", { type: "Evidence", id: evidenceId }, { from: ev.verificationStatus, to: s });
  });
}
