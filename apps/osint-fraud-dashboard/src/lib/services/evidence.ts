import { ADAPTERS, AdapterInputError } from "../osint/adapters";
import { NotFoundError, ValidationError } from "../errors";
import { cleanText } from "../text";
import { audit, now, requirePermission, type Ctx } from "./context";
import { insertEvidence } from "./imports";

/** Collect evidence through a source adapter. Returns the new evidence ids. */
export async function collectEvidence(ctx: Ctx, adapterId: string, input: Record<string, string>): Promise<{ created: string[]; skipped: string[] }> {
  await requirePermission(ctx, "evidence:create", { type: "Evidence" });
  const adapter = ADAPTERS[adapterId];
  if (!adapter) throw new ValidationError(`Unknown source adapter "${adapterId}"`);
  let items;
  try {
    items = adapter.collect(input, now(ctx));
  } catch (e) {
    if (e instanceof AdapterInputError) throw new ValidationError("Check the evidence form", e.issues);
    throw e;
  }
  const created: string[] = [];
  const skipped: string[] = [];
  for (const item of items) {
    const existing = await ctx.db.evidence.findUnique({ where: { recordId: item.recordId } });
    if (existing) {
      if (existing.contentHash !== item.contentHash) {
        throw new ValidationError(`Evidence id ${item.recordId} already exists with different content; choose another id`);
      }
      skipped.push(item.recordId);
      continue;
    }
    const id = await ctx.db.$transaction((tx) =>
      insertEvidence(tx, ctx, item, {
        origin: adapter.origin,
        isSynthetic: adapter.origin === "SYNTHETIC",
        batchId: null,
        extractionMethod: adapter.extractionMethod,
      }),
    );
    await audit(ctx.db, ctx.actor, "evidence.collect", { type: "Evidence", id }, { adapter: adapter.id, recordId: item.recordId, live: adapter.live });
    created.push(id);
  }
  return { created, skipped };
}

/** Record a statement extracted from evidence. Only reviewers may label one a reviewed finding. */
export async function addFact(ctx: Ctx, evidenceId: string, statement: string, claimStatus: string): Promise<void> {
  const allowed = ["ALLEGATION", "SOURCE_SUPPORTED_OBSERVATION", "REVIEWED_FINDING"];
  if (!allowed.includes(claimStatus)) throw new ValidationError("Unknown claim status");
  await requirePermission(ctx, claimStatus === "REVIEWED_FINDING" ? "evidence:verify" : "evidence:create", { type: "Evidence", id: evidenceId });
  const text = cleanText(statement).trim();
  if (text.length < 5 || text.length > 2000) throw new ValidationError("A statement is 5 to 2,000 characters");
  const ev = await ctx.db.evidence.findUnique({ where: { id: evidenceId }, select: { id: true } });
  if (!ev) throw new NotFoundError("Evidence not found");
  const fact = await ctx.db.extractedFact.create({
    data: { evidenceId, statement: text, claimStatus: claimStatus as "ALLEGATION" | "SOURCE_SUPPORTED_OBSERVATION" | "REVIEWED_FINDING" },
  });
  await audit(ctx.db, ctx.actor, "evidence.fact", { type: "Evidence", id: evidenceId }, { factId: fact.id, claimStatus });
}
