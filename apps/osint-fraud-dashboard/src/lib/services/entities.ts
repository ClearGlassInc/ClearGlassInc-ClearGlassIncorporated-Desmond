import { proposeLinks, type ResolvableEntity } from "../entities/resolve";
import { NotFoundError, ValidationError } from "../errors";
import { MIN_RATIONALE } from "../review";
import { audit, requirePermission, type Ctx } from "./context";

/** Generate candidate links. Links a reviewer already decided are left as they are. */
export async function generateCandidateLinks(ctx: Ctx): Promise<{ proposed: number; created: number }> {
  await requirePermission(ctx, "entity:propose", { type: "Relationship" });
  const [vendors, orgs] = await Promise.all([ctx.db.vendor.findMany(), ctx.db.organization.findMany()]);
  const entities: ResolvableEntity[] = [
    ...vendors.map((v) => ({
      kind: "VENDOR" as const,
      id: v.id,
      recordId: v.recordId,
      name: v.name,
      identifier: v.taxId,
      domain: v.domain,
      address: v.address,
      organizationId: v.organizationId,
    })),
    ...orgs.map((o) => ({
      kind: "ORGANIZATION" as const,
      id: o.id,
      recordId: o.recordId,
      name: o.name,
      identifier: o.registrationNumber,
      domain: o.domain,
      address: o.address,
    })),
  ];
  const synthetic = new Set([...vendors.filter((v) => v.isSynthetic).map((v) => v.id), ...orgs.filter((o) => o.isSynthetic).map((o) => o.id)]);
  const links = proposeLinks(entities);
  let created = 0;
  for (const l of links) {
    const key = { fromKind: l.fromKind, fromId: l.fromId, toKind: l.toKind, toId: l.toId, relationType: l.relationType, basis: l.basis };
    const existing = await ctx.db.relationship.findUnique({ where: { fromKind_fromId_toKind_toId_relationType_basis: key } });
    if (existing) continue;
    await ctx.db.relationship.create({
      data: {
        ...key,
        basisDetail: l.basisDetail,
        status: l.status,
        claimStatus: l.status === "CONFIRMED" ? "SOURCE_SUPPORTED_OBSERVATION" : "ANALYST_INTERPRETATION",
        isSynthetic: synthetic.has(l.fromId) || synthetic.has(l.toId),
      },
    });
    created += 1;
  }
  await audit(ctx.db, ctx.actor, "entity.candidates", { type: "Relationship" }, { proposed: links.length, created });
  return { proposed: links.length, created };
}

const MOVES: Record<string, { from: string[]; to: "CONFIRMED" | "REJECTED" | "REVERSED" | "CANDIDATE" }> = {
  CONFIRM: { from: ["CANDIDATE"], to: "CONFIRMED" },
  REJECT: { from: ["CANDIDATE"], to: "REJECTED" },
  // Reversal undoes an approved merge/link but keeps the row and its history.
  REVERSE: { from: ["CONFIRMED"], to: "REVERSED" },
  REOPEN: { from: ["REJECTED", "REVERSED"], to: "CANDIDATE" },
};

export async function reviewRelationship(ctx: Ctx, relationshipId: string, action: string, rationale: string): Promise<void> {
  await requirePermission(ctx, "entity:review", { type: "Relationship", id: relationshipId });
  const move = MOVES[action];
  if (!move) throw new ValidationError(`Unknown action "${action}"`);
  if (rationale.trim().length < MIN_RATIONALE) throw new ValidationError(`A rationale of at least ${MIN_RATIONALE} characters is required`);
  const rel = await ctx.db.relationship.findUnique({ where: { id: relationshipId } });
  if (!rel) throw new NotFoundError("Relationship not found");
  if (!move.from.includes(rel.status)) throw new ValidationError(`Cannot ${action.toLowerCase()} a ${rel.status} link`);
  await ctx.db.$transaction(async (tx) => {
    await tx.relationship.update({
      where: { id: relationshipId },
      data: {
        status: move.to,
        claimStatus: move.to === "CONFIRMED" ? "REVIEWED_FINDING" : rel.basis === "EXPLICIT_IDENTIFIER" && move.to === "CANDIDATE" ? "SOURCE_SUPPORTED_OBSERVATION" : "ANALYST_INTERPRETATION",
      },
    });
    await tx.reviewDecision.create({
      data: { targetType: "RELATIONSHIP", targetId: relationshipId, fromState: rel.status, toState: move.to, rationale: rationale.trim(), decidedById: ctx.actor.id },
    });
    await audit(tx, ctx.actor, "entity.review", { type: "Relationship", id: relationshipId }, { action, from: rel.status, to: move.to });
  });
}
