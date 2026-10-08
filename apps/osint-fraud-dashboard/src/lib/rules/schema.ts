import { z } from "zod";
import { RECORD_FIELDS, TRANSACTION_TYPES, type RecordField } from "./records";

// Every condition must say why it exists: evidence, an incident, or an
// explicitly labelled analyst assumption. Nothing is allowed to be silent.
export const supportSchema = z
  .object({
    evidenceIds: z.array(z.string().min(1)).default([]),
    incidentIds: z.array(z.string().min(1)).default([]),
    assumption: z.string().min(10, "An assumption must be stated in at least 10 characters").nullable().default(null),
  })
  .refine((s) => s.evidenceIds.length + s.incidentIds.length > 0 || s.assumption !== null, {
    message: "Cite supporting evidence or an incident, or state an explicit analyst assumption",
  });
export type Support = z.infer<typeof supportSchema>;

export const thresholdSchema = z
  .object({
    value: z.number().finite(),
    unit: z.enum(["days", "currency", "count"]),
    rationale: z.string().min(10, "Every threshold needs a rationale"),
    basis: z.enum(["ANALYST_ASSUMPTION", "POLICY_DOCUMENT", "EVIDENCE"]),
    evidenceIds: z.array(z.string().min(1)).default([]),
  })
  .refine((t) => t.basis === "ANALYST_ASSUMPTION" || t.evidenceIds.length > 0, {
    message: "A threshold based on a policy document or evidence must cite the evidence id",
  });
export type Threshold = z.infer<typeof thresholdSchema>;

const fieldSchema = z.enum(RECORD_FIELDS);
const recordTypeSchema = z.enum(TRANSACTION_TYPES);
const valueRefSchema = z.union([z.number().finite(), z.object({ threshold: z.string().min(1) })]);
export type ValueRef = z.infer<typeof valueRefSchema>;

const conditionBase = {
  id: z.string().regex(/^[a-z][a-z0-9_]{0,39}$/, "Condition ids are lower_snake_case"),
  description: z.string().min(5),
  support: supportSchema,
};

export const conditionSchema = z.discriminatedUnion("op", [
  z.object({ ...conditionBase, op: z.literal("is_blank"), field: fieldSchema }),
  z.object({
    ...conditionBase,
    op: z.literal("date_after"),
    field: fieldSchema,
    otherField: fieldSchema,
    graceDays: valueRefSchema.default(0),
  }),
  z.object({
    ...conditionBase,
    op: z.literal("list_missing_any"),
    field: fieldSchema,
    required: z.array(z.string().min(1)).min(1),
  }),
  z.object({ ...conditionBase, op: z.literal("gte"), field: fieldSchema, value: valueRefSchema }),
  z.object({ ...conditionBase, op: z.literal("lt"), field: fieldSchema, value: valueRefSchema }),
]);
export type Condition = z.infer<typeof conditionSchema>;

const slot = <T extends z.ZodRawShape>(shape: T) =>
  z.object({ ...shape, description: z.string().min(5), support: supportSchema });

export const patternSchema = z.discriminatedUnion("kind", [
  z.object({
    kind: z.literal("record_checks"),
    recordType: recordTypeSchema,
    applicability: z.array(conditionSchema).default([]),
    conditions: z.array(conditionSchema).min(1),
  }),
  z.object({
    kind: z.literal("sequence_within_window"),
    groupBy: z.literal("vendorRecordId"),
    first: slot({ recordType: recordTypeSchema }),
    then: slot({ recordType: recordTypeSchema }),
    window: slot({ days: valueRefSchema }),
  }),
  z.object({
    kind: z.literal("aggregate_within_window"),
    groupBy: z.literal("vendorRecordId"),
    recordType: recordTypeSchema,
    eachBelow: slot({ value: valueRefSchema }).optional(),
    minCount: slot({ value: valueRefSchema }),
    sumAtLeast: slot({ value: valueRefSchema }),
    window: slot({ days: valueRefSchema }),
  }),
]);
export type Pattern = z.infer<typeof patternSchema>;

export const ruleDefinitionSchema = z
  .object({
    schemaVersion: z.literal(1),
    ruleKey: z.string().regex(/^[A-Z][A-Z0-9-]{2,39}$/, "Rule keys look like CG-R-001"),
    name: z.string().min(5).max(120),
    description: z.string().min(20),
    illustrative: z.boolean(),
    disclaimer: z.string().nullable().default(null),
    supportingIncidentIds: z.array(z.string().min(1)).default([]),
    supportingEvidenceIds: z.array(z.string().min(1)).default([]),
    requiredFields: z.array(fieldSchema).min(1),
    entityMatching: z.enum(["explicit_vendor_record_id", "per_record"]),
    thresholds: z.record(z.string().regex(/^[a-zA-Z][a-zA-Z0-9]{0,39}$/), thresholdSchema).default({}),
    pattern: patternSchema,
    missingDataBehavior: z.literal("INSUFFICIENT_DATA"),
    benignExplanations: z.array(z.string().min(5)).min(1, "List at least one known benign explanation"),
    falsePositiveConsiderations: z.array(z.string().min(5)).min(1),
    reviewPriority: z.enum(["LOW", "MEDIUM", "HIGH"]),
  })
  .superRefine((def, ctx) => {
    if (/\bTODO\b/.test(JSON.stringify(def))) {
      ctx.addIssue({ code: "custom", path: [], message: "Replace every TODO placeholder (values, rationales, descriptions) before proposing the rule" });
    }
    if (def.illustrative && !def.disclaimer) {
      ctx.addIssue({ code: "custom", path: ["disclaimer"], message: "Illustrative rules must carry a disclaimer" });
    }
    if (!def.illustrative && def.supportingIncidentIds.length + def.supportingEvidenceIds.length === 0) {
      ctx.addIssue({
        code: "custom",
        path: ["supportingEvidenceIds"],
        message: "A rule that is not illustrative must cite the incidents or evidence it is derived from",
      });
    }
    for (const name of referencedThresholds(def.pattern)) {
      if (!(name in def.thresholds)) {
        ctx.addIssue({ code: "custom", path: ["thresholds", name], message: `Threshold "${name}" is referenced but not defined` });
      }
    }
    const required = new Set(def.requiredFields);
    for (const field of referencedFields(def.pattern)) {
      if (!required.has(field)) {
        ctx.addIssue({ code: "custom", path: ["requiredFields"], message: `Field "${field}" is used by the pattern but not listed in requiredFields` });
      }
    }
    const grouped = def.pattern.kind !== "record_checks";
    if (grouped !== (def.entityMatching === "explicit_vendor_record_id")) {
      ctx.addIssue({
        code: "custom",
        path: ["entityMatching"],
        message: grouped ? "Grouped patterns match entities on the explicit vendor record id" : "Per-record checks use per_record matching",
      });
    }
    const ids = conditionSupport(def.pattern).map((c) => c.id);
    const dupes = ids.filter((id, i) => ids.indexOf(id) !== i);
    if (dupes.length) ctx.addIssue({ code: "custom", path: ["pattern"], message: `Duplicate condition ids: ${dupes.join(", ")}` });
  });
export type RuleDefinition = z.infer<typeof ruleDefinitionSchema>;

function refName(ref: ValueRef | undefined): string[] {
  return ref !== undefined && typeof ref === "object" ? [ref.threshold] : [];
}

function conditionThresholds(c: Condition): string[] {
  if (c.op === "date_after") return refName(c.graceDays);
  if (c.op === "gte" || c.op === "lt") return refName(c.value);
  return [];
}

export function referencedThresholds(pattern: Pattern): string[] {
  switch (pattern.kind) {
    case "record_checks":
      return [...pattern.applicability, ...pattern.conditions].flatMap(conditionThresholds);
    case "sequence_within_window":
      return refName(pattern.window.days);
    case "aggregate_within_window":
      return [
        ...refName(pattern.eachBelow?.value),
        ...refName(pattern.minCount.value),
        ...refName(pattern.sumAtLeast.value),
        ...refName(pattern.window.days),
      ];
  }
}

export function referencedFields(pattern: Pattern): RecordField[] {
  switch (pattern.kind) {
    case "record_checks":
      return [...pattern.applicability, ...pattern.conditions].flatMap((c) =>
        c.op === "date_after" ? [c.field, c.otherField] : [c.field],
      );
    case "sequence_within_window":
      return ["vendorRecordId", "occurredAt"];
    case "aggregate_within_window":
      return ["vendorRecordId", "occurredAt", "amount"];
  }
}

export interface ConditionSupport {
  id: string;
  description: string;
  role: "applicability" | "condition";
  support: Support;
}

/** Every condition of a rule with the evidence, incident or assumption behind it. */
export function conditionSupport(pattern: Pattern): ConditionSupport[] {
  switch (pattern.kind) {
    case "record_checks":
      return [
        ...pattern.applicability.map((c) => ({ id: c.id, description: c.description, role: "applicability" as const, support: c.support })),
        ...pattern.conditions.map((c) => ({ id: c.id, description: c.description, role: "condition" as const, support: c.support })),
      ];
    case "sequence_within_window":
      return (["first", "then", "window"] as const).map((k) => ({
        id: k,
        description: pattern[k].description,
        role: "condition" as const,
        support: pattern[k].support,
      }));
    case "aggregate_within_window": {
      const slots = (["eachBelow", "minCount", "sumAtLeast", "window"] as const).filter((k) => pattern[k] !== undefined);
      return slots.map((k) => ({
        id: k,
        description: pattern[k]!.description,
        role: "condition" as const,
        support: pattern[k]!.support,
      }));
    }
  }
}

/** All evidence and incident record ids a rule definition cites, anywhere. */
export function citedRecordIds(def: RuleDefinition): { evidenceIds: string[]; incidentIds: string[] } {
  const evidence = new Set(def.supportingEvidenceIds);
  const incidents = new Set(def.supportingIncidentIds);
  for (const c of conditionSupport(def.pattern)) {
    c.support.evidenceIds.forEach((id) => evidence.add(id));
    c.support.incidentIds.forEach((id) => incidents.add(id));
  }
  for (const t of Object.values(def.thresholds)) t.evidenceIds.forEach((id) => evidence.add(id));
  return { evidenceIds: [...evidence].sort(), incidentIds: [...incidents].sort() };
}

/** Human-readable zod issues, one line each, with the JSON path that failed. */
export function formatIssues(error: z.ZodError): string[] {
  return error.issues.map((i) => `${i.path.length ? i.path.join(".") : "(root)"}: ${i.message}`);
}
