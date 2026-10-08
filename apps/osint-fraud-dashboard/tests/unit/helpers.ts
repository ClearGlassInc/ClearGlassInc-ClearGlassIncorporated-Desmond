import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import type { RecordField, RecordView, TransactionTypeName, FieldValue } from "@/lib/rules/records";
import { ruleDefinitionSchema, type RuleDefinition } from "@/lib/rules/schema";

const TEMPLATE_DIR = join(__dirname, "..", "..", "rules", "templates");

export function template(ruleKey: string): RuleDefinition {
  const file = readdirSync(TEMPLATE_DIR).find((f) => f.startsWith(ruleKey.toLowerCase()));
  if (!file) throw new Error(`no template ${ruleKey}`);
  return ruleDefinitionSchema.parse(JSON.parse(readFileSync(join(TEMPLATE_DIR, file), "utf8")));
}

/** Build a record. Only keys present in `values` count as supplied by the source. */
export function rec(recordId: string, type: TransactionTypeName, values: Partial<Record<RecordField, FieldValue>>): RecordView {
  return {
    id: `db-${recordId}`,
    recordId,
    type,
    values,
    provided: new Set(Object.keys(values) as RecordField[]),
    evidenceRecordId: null,
    isSynthetic: true,
  };
}

export const d = (s: string) => new Date(s);
export const META = { ruleVersionId: "rv-test", version: 1 };
export const NOW = new Date("2026-10-08T12:00:00Z");
