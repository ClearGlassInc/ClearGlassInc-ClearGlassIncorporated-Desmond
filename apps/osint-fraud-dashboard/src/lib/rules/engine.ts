// Deterministic, inspectable rule evaluation.
//
// Three-valued logic throughout: a condition is TRUE, FALSE or UNKNOWN. UNKNOWN
// comes from a field the source did not supply (or a blank value a comparison
// cannot use). UNKNOWN never collapses into FALSE, so missing data produces
// INSUFFICIENT_DATA rather than a quiet "no match".
//
// The engine has no I/O and takes the clock as an argument: the same inputs
// always produce the same output.

import { citedRecordIds, type Condition, type RuleDefinition, type ValueRef } from "./schema";
import { readField, type RecordField, type RecordView } from "./records";

export type Outcome = "MATCH" | "NO_MATCH" | "INSUFFICIENT_DATA";
export type Truth = "TRUE" | "FALSE" | "UNKNOWN";

export interface ConditionResult {
  id: string;
  description: string;
  result: Truth;
  expected: string;
  actual: Record<string, string | number | string[] | null>;
}

export interface MissingField {
  recordId: string;
  field: RecordField;
}

export interface EvaluationResult {
  ruleKey: string;
  ruleVersion: number;
  ruleVersionId: string;
  outcome: Outcome;
  subjectKey: string;
  matchedRecordIds: string[];
  conditions: ConditionResult[];
  missingFields: MissingField[];
  evidenceRefs: string[];
  explanation: string;
  evaluatedAt: string;
}

export interface RuleMeta {
  ruleVersionId: string;
  version: number;
}

export interface EvaluationSummary {
  results: EvaluationResult[];
  /** Records of the rule's type that a known value placed outside its scope. */
  outOfScope: number;
}

const DAY_MS = 86_400_000;

export const NOT_A_FINDING =
  "A match is a reason to review these records. It is not a finding of fraud or wrongdoing.";
export const NOT_A_CLEARANCE =
  "This is not a determination that the activity is legitimate; only the supplied records were evaluated.";
export const NOT_CLEARED = "These records have not been cleared.";

export function resolveValue(def: RuleDefinition, ref: ValueRef): number {
  if (typeof ref === "number") return ref;
  const t = def.thresholds[ref.threshold];
  if (!t) throw new Error(`Threshold "${ref.threshold}" is not defined`);
  return t.value;
}

function describeRef(def: RuleDefinition, ref: ValueRef): string {
  if (typeof ref === "number") return String(ref);
  return `${resolveValue(def, ref)} (threshold "${ref.threshold}")`;
}

function iso(d: Date): string {
  return d.toISOString();
}

function asDate(value: unknown): Date | null {
  if (value instanceof Date && !Number.isNaN(value.getTime())) return value;
  return null;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function display(value: unknown): string | number | string[] | null {
  if (value instanceof Date) return iso(value);
  if (Array.isArray(value)) return value.map(String);
  if (typeof value === "number" || typeof value === "string") return value;
  return null;
}

/** Evaluate one condition against one record. Exported for tests and the rule editor preview. */
export function evaluateCondition(
  def: RuleDefinition,
  c: Condition,
  record: RecordView,
  missing: MissingField[],
): ConditionResult {
  const base = { id: c.id, description: c.description };
  const note = (field: RecordField) => {
    if (!missing.some((m) => m.recordId === record.recordId && m.field === field)) {
      missing.push({ recordId: record.recordId, field });
    }
  };

  switch (c.op) {
    case "is_blank": {
      const f = readField(record, c.field);
      if (f.state === "UNKNOWN") {
        note(c.field);
        return { ...base, result: "UNKNOWN", expected: `${c.field} supplied and blank`, actual: { [c.field]: "(not supplied by source)" } };
      }
      return {
        ...base,
        result: f.state === "BLANK" ? "TRUE" : "FALSE",
        expected: `${c.field} supplied and blank`,
        actual: { [c.field]: f.state === "BLANK" ? "(blank)" : display(f.value) },
      };
    }
    case "date_after": {
      const grace = resolveValue(def, c.graceDays);
      const a = readField(record, c.field);
      const b = readField(record, c.otherField);
      const da = a.state === "VALUE" ? asDate(a.value) : null;
      const db = b.state === "VALUE" ? asDate(b.value) : null;
      const expected = `${c.field} later than ${c.otherField} + ${describeRef(def, c.graceDays)} day(s)`;
      if (!da) note(c.field);
      if (!db) note(c.otherField);
      if (!da || !db) {
        return {
          ...base,
          result: "UNKNOWN",
          expected,
          actual: { [c.field]: da ? iso(da) : "(not available)", [c.otherField]: db ? iso(db) : "(not available)" },
        };
      }
      const diffDays = (da.getTime() - db.getTime()) / DAY_MS;
      return {
        ...base,
        result: da.getTime() > db.getTime() + grace * DAY_MS ? "TRUE" : "FALSE",
        expected,
        actual: { [c.field]: iso(da), [c.otherField]: iso(db), differenceDays: Math.round(diffDays * 100) / 100 },
      };
    }
    case "list_missing_any": {
      const f = readField(record, c.field);
      const expected = `${c.field} is missing at least one of: ${c.required.join(", ")}`;
      if (f.state === "UNKNOWN") {
        note(c.field);
        return { ...base, result: "UNKNOWN", expected, actual: { [c.field]: "(not supplied by source)" } };
      }
      const present = f.state === "VALUE" && Array.isArray(f.value) ? f.value.map((v) => v.toLowerCase().trim()) : [];
      const absent = c.required.filter((r) => !present.includes(r.toLowerCase().trim()));
      return { ...base, result: absent.length > 0 ? "TRUE" : "FALSE", expected, actual: { [c.field]: present, absent } };
    }
    case "gte":
    case "lt": {
      const limit = resolveValue(def, c.value);
      const f = readField(record, c.field);
      const n = f.state === "VALUE" ? asNumber(f.value) : null;
      const expected = `${c.field} ${c.op === "gte" ? ">=" : "<"} ${describeRef(def, c.value)}`;
      if (n === null) {
        note(c.field);
        return { ...base, result: "UNKNOWN", expected, actual: { [c.field]: f.state === "UNKNOWN" ? "(not supplied by source)" : "(blank)" } };
      }
      return { ...base, result: (c.op === "gte" ? n >= limit : n < limit) ? "TRUE" : "FALSE", expected, actual: { [c.field]: n } };
    }
  }
}

/** Kleene AND: any FALSE wins, then any UNKNOWN, else TRUE. */
export function and(values: Truth[]): Truth {
  if (values.includes("FALSE")) return "FALSE";
  if (values.includes("UNKNOWN")) return "UNKNOWN";
  return "TRUE";
}

function evidenceRefs(def: RuleDefinition, records: RecordView[]): string[] {
  const refs = new Set(citedRecordIds(def).evidenceIds);
  for (const r of records) if (r.evidenceRecordId) refs.add(r.evidenceRecordId);
  return [...refs].sort();
}

function describeMissing(missing: MissingField[]): string {
  return missing.map((m) => `${m.recordId}.${m.field}`).join(", ");
}

export function evaluateRule(
  def: RuleDefinition,
  meta: RuleMeta,
  records: RecordView[],
  now: Date,
): EvaluationSummary {
  switch (def.pattern.kind) {
    case "record_checks":
      return evaluateRecordChecks(def, meta, records, now);
    case "sequence_within_window":
      return evaluateSequence(def, meta, records, now);
    case "aggregate_within_window":
      return evaluateAggregate(def, meta, records, now);
  }
}

function result(
  def: RuleDefinition,
  meta: RuleMeta,
  now: Date,
  r: Omit<EvaluationResult, "ruleKey" | "ruleVersion" | "ruleVersionId" | "evaluatedAt">,
): EvaluationResult {
  return {
    ruleKey: def.ruleKey,
    ruleVersion: meta.version,
    ruleVersionId: meta.ruleVersionId,
    evaluatedAt: iso(now),
    ...r,
    matchedRecordIds: [...r.matchedRecordIds].sort(),
  };
}

function evaluateRecordChecks(def: RuleDefinition, meta: RuleMeta, records: RecordView[], now: Date): EvaluationSummary {
  if (def.pattern.kind !== "record_checks") throw new Error("unreachable");
  const pattern = def.pattern;
  const results: EvaluationResult[] = [];
  let outOfScope = 0;
  const label = `Rule ${def.ruleKey} v${meta.version}`;

  for (const record of records.filter((r) => r.type === pattern.recordType)) {
    const missing: MissingField[] = [];
    const scope = pattern.applicability.map((c) => evaluateCondition(def, c, record, missing));
    const inScope = and(scope.map((s) => s.result));
    if (inScope === "FALSE") {
      outOfScope += 1;
      continue;
    }
    const checks = pattern.conditions.map((c) => evaluateCondition(def, c, record, missing));
    const conditions = [...scope, ...checks];
    const verdict = and([inScope, ...checks.map((c) => c.result)]);
    const subjectKey = `record:${record.recordId}`;
    const refs = evidenceRefs(def, [record]);

    if (verdict === "TRUE") {
      const met = checks.map((c) => `${c.description} (${formatActual(c.actual)})`).join("; ");
      results.push(
        result(def, meta, now, {
          outcome: "MATCH",
          subjectKey,
          matchedRecordIds: [record.recordId],
          conditions,
          missingFields: missing,
          evidenceRefs: refs,
          explanation: `${label} matched ${record.type} ${record.recordId}: ${met}. ${NOT_A_FINDING}`,
        }),
      );
    } else if (verdict === "FALSE") {
      const unmet = conditions.filter((c) => c.result === "FALSE").map((c) => c.description).join("; ");
      results.push(
        result(def, meta, now, {
          outcome: "NO_MATCH",
          subjectKey,
          matchedRecordIds: [record.recordId],
          conditions,
          missingFields: missing,
          evidenceRefs: refs,
          explanation: `${label} did not match ${record.recordId}: not met - ${unmet}. ${NOT_A_CLEARANCE}`,
        }),
      );
    } else {
      results.push(
        result(def, meta, now, {
          outcome: "INSUFFICIENT_DATA",
          subjectKey,
          matchedRecordIds: [record.recordId],
          conditions,
          missingFields: missing,
          evidenceRefs: refs,
          explanation: `${label} could not evaluate ${record.recordId}: missing ${describeMissing(missing)}. ${NOT_CLEARED}`,
        }),
      );
    }
  }
  return { results, outOfScope };
}

function formatActual(actual: ConditionResult["actual"]): string {
  return Object.entries(actual)
    .map(([k, v]) => `${k}=${Array.isArray(v) ? `[${v.join(", ")}]` : v}`)
    .join(", ");
}

interface Grouped {
  groups: Map<string, RecordView[]>;
  ungroupable: RecordView[];
}

function groupByVendor(records: RecordView[]): Grouped {
  const groups = new Map<string, RecordView[]>();
  const ungroupable: RecordView[] = [];
  for (const r of records) {
    const f = readField(r, "vendorRecordId");
    if (f.state !== "VALUE") {
      ungroupable.push(r);
      continue;
    }
    const key = String(f.value);
    const list = groups.get(key) ?? [];
    list.push(r);
    groups.set(key, list);
  }
  return { groups: new Map([...groups.entries()].sort(([a], [b]) => a.localeCompare(b))), ungroupable };
}

function ungroupableResults(def: RuleDefinition, meta: RuleMeta, now: Date, records: RecordView[]): EvaluationResult[] {
  return records.map((r) =>
    result(def, meta, now, {
      outcome: "INSUFFICIENT_DATA",
      subjectKey: `record:${r.recordId}`,
      matchedRecordIds: [r.recordId],
      conditions: [],
      missingFields: [{ recordId: r.recordId, field: "vendorRecordId" }],
      evidenceRefs: evidenceRefs(def, [r]),
      explanation:
        `Rule ${def.ruleKey} v${meta.version} could not evaluate ${r.recordId}: no explicit vendor identifier was supplied, ` +
        `so it cannot be grouped. Names are not used to guess the vendor. ${NOT_CLEARED}`,
    }),
  );
}

function evaluateSequence(def: RuleDefinition, meta: RuleMeta, records: RecordView[], now: Date): EvaluationSummary {
  if (def.pattern.kind !== "sequence_within_window") throw new Error("unreachable");
  const p = def.pattern;
  const windowDays = resolveValue(def, p.window.days);
  const relevant = records.filter((r) => r.type === p.first.recordType || r.type === p.then.recordType);
  const { groups, ungroupable } = groupByVendor(relevant);
  const results = ungroupableResults(def, meta, now, ungroupable);
  const label = `Rule ${def.ruleKey} v${meta.version}`;

  for (const [vendor, group] of groups) {
    const missing: MissingField[] = [];
    const timed = (type: string) =>
      group
        .filter((r) => r.type === type)
        .flatMap((r) => {
          const f = readField(r, "occurredAt");
          const d = f.state === "VALUE" ? asDate(f.value) : null;
          if (!d) {
            missing.push({ recordId: r.recordId, field: "occurredAt" });
            return [];
          }
          return [{ r, t: d.getTime() }];
        });
    const firsts = timed(p.first.recordType);
    const thens = timed(p.then.recordType);

    // A pair matches when then.t is strictly after first.t and no more than windowDays later.
    const pairs: { first: RecordView; then: RecordView; days: number }[] = [];
    for (const t of thens) {
      for (const f of firsts) {
        const delta = t.t - f.t;
        if (delta > 0 && delta <= windowDays * DAY_MS) pairs.push({ first: f.r, then: t.r, days: delta / DAY_MS });
      }
    }
    pairs.sort((a, b) => a.days - b.days || a.first.recordId.localeCompare(b.first.recordId));

    const firstCount = group.filter((r) => r.type === p.first.recordType).length;
    const thenCount = group.filter((r) => r.type === p.then.recordType).length;
    const closest = pairs[0];
    const conditions: ConditionResult[] = [
      {
        id: "first",
        description: p.first.description,
        result: firstCount === 0 ? "FALSE" : firsts.length > 0 ? "TRUE" : "UNKNOWN",
        expected: `at least one ${p.first.recordType} for vendor ${vendor}`,
        actual: { count: firstCount, withTimestamp: firsts.length },
      },
      {
        id: "then",
        description: p.then.description,
        result: thenCount === 0 ? "FALSE" : thens.length > 0 ? "TRUE" : "UNKNOWN",
        expected: `at least one ${p.then.recordType} for vendor ${vendor}`,
        actual: { count: thenCount, withTimestamp: thens.length },
      },
      {
        id: "window",
        description: p.window.description,
        result: pairs.length > 0 ? "TRUE" : missing.length > 0 ? "UNKNOWN" : "FALSE",
        expected: `${p.then.recordType} after ${p.first.recordType} within ${describeRef(def, p.window.days)} day(s), end inclusive`,
        actual: closest
          ? { closestPairDays: Math.round(closest.days * 100) / 100, pairs: pairs.map((x) => `${x.first.recordId}->${x.then.recordId}`) }
          : { closestPairDays: null, pairs: [] },
      },
    ];

    const subjectKey = `vendor:${vendor}`;
    // Kleene AND over the three conditions: no BANK_DETAIL_CHANGE at all is a
    // definite FALSE even if some other record lacks a timestamp.
    const verdict = and(conditions.map((c) => c.result));
    if (verdict === "TRUE") {
      const ids = [...new Set(pairs.flatMap((x) => [x.first.recordId, x.then.recordId]))];
      const involved = group.filter((r) => ids.includes(r.recordId));
      results.push(
        result(def, meta, now, {
          outcome: "MATCH",
          subjectKey,
          matchedRecordIds: ids,
          conditions,
          missingFields: missing,
          evidenceRefs: evidenceRefs(def, involved),
          explanation:
            `${label} matched vendor ${vendor}: ${p.then.recordType} ${closest.then.recordId} occurred ` +
            `${Math.round(closest.days * 100) / 100} day(s) after ${p.first.recordType} ${closest.first.recordId} ` +
            `(window ${windowDays} day(s)). ${NOT_A_FINDING}`,
        }),
      );
    } else if (verdict === "UNKNOWN") {
      results.push(
        result(def, meta, now, {
          outcome: "INSUFFICIENT_DATA",
          subjectKey,
          matchedRecordIds: group.map((r) => r.recordId),
          conditions,
          missingFields: missing,
          evidenceRefs: evidenceRefs(def, group),
          explanation: `${label} could not evaluate vendor ${vendor}: missing ${describeMissing(missing)}. ${NOT_CLEARED}`,
        }),
      );
    } else {
      const reason =
        firstCount === 0
          ? `no ${p.first.recordType} is recorded for this vendor in the supplied records`
          : thenCount === 0
            ? `no ${p.then.recordType} is recorded for this vendor in the supplied records`
            : `no ${p.then.recordType} within ${windowDays} day(s) after a ${p.first.recordType}`;
      results.push(
        result(def, meta, now, {
          outcome: "NO_MATCH",
          subjectKey,
          matchedRecordIds: group.map((r) => r.recordId),
          conditions,
          missingFields: missing,
          evidenceRefs: evidenceRefs(def, group),
          explanation: `${label} did not match vendor ${vendor}: ${reason}. ${NOT_A_CLEARANCE}`,
        }),
      );
    }
  }
  return { results, outOfScope: 0 };
}

function evaluateAggregate(def: RuleDefinition, meta: RuleMeta, records: RecordView[], now: Date): EvaluationSummary {
  if (def.pattern.kind !== "aggregate_within_window") throw new Error("unreachable");
  const p = def.pattern;
  const windowDays = resolveValue(def, p.window.days);
  const minCount = resolveValue(def, p.minCount.value);
  const sumAtLeast = resolveValue(def, p.sumAtLeast.value);
  const eachBelow = p.eachBelow ? resolveValue(def, p.eachBelow.value) : null;
  const { groups, ungroupable } = groupByVendor(records.filter((r) => r.type === p.recordType));
  const results = ungroupableResults(def, meta, now, ungroupable);
  const label = `Rule ${def.ruleKey} v${meta.version}`;

  for (const [vendor, group] of groups) {
    const missing: MissingField[] = [];
    let excludedAtOrAbove = 0;
    const known: { r: RecordView; t: number; amount: number }[] = [];
    for (const r of group) {
      const tf = readField(r, "occurredAt");
      const af = readField(r, "amount");
      const d = tf.state === "VALUE" ? asDate(tf.value) : null;
      const amount = af.state === "VALUE" ? asNumber(af.value) : null;
      if (!d) missing.push({ recordId: r.recordId, field: "occurredAt" });
      if (amount === null) missing.push({ recordId: r.recordId, field: "amount" });
      if (!d || amount === null) continue;
      if (eachBelow !== null && amount >= eachBelow) {
        excludedAtOrAbove += 1;
        continue;
      }
      known.push({ r, t: d.getTime(), amount });
    }
    known.sort((a, b) => a.t - b.t || a.r.recordId.localeCompare(b.r.recordId));

    // Every window starts at a record and is end-inclusive: [t_i, t_i + windowDays].
    let best: { members: typeof known; sum: number } | null = null;
    let qualifying = 0;
    for (let i = 0; i < known.length; i++) {
      const end = known[i].t + windowDays * DAY_MS;
      const members = known.filter((k, j) => j >= i && k.t <= end);
      const sum = Math.round(members.reduce((s, k) => s + k.amount, 0) * 100) / 100;
      if (members.length >= minCount && sum >= sumAtLeast) {
        qualifying += 1;
        if (!best || sum > best.sum) best = { members, sum };
      }
    }

    const largest = known.reduce<{ count: number; sum: number }>((acc, _k, i) => {
      const end = known[i].t + windowDays * DAY_MS;
      const members = known.filter((k, j) => j >= i && k.t <= end);
      const sum = Math.round(members.reduce((s, k) => s + k.amount, 0) * 100) / 100;
      return sum > acc.sum ? { count: members.length, sum } : acc;
    }, { count: 0, sum: 0 });

    const shown = best ? { count: best.members.length, sum: best.sum } : largest;
    const unknownTail = missing.length > 0 ? "UNKNOWN" : "FALSE";
    const conditions: ConditionResult[] = [];
    if (p.eachBelow && eachBelow !== null) {
      conditions.push({
        id: "eachBelow",
        description: p.eachBelow.description,
        result: known.length > 0 ? "TRUE" : unknownTail,
        expected: `each ${p.recordType} amount < ${describeRef(def, p.eachBelow.value)}`,
        actual: { recordsBelow: known.length, recordsAtOrAbove: excludedAtOrAbove },
      });
    }
    conditions.push(
      {
        id: "minCount",
        description: p.minCount.description,
        result: best ? "TRUE" : shown.count >= minCount ? "TRUE" : unknownTail,
        expected: `at least ${describeRef(def, p.minCount.value)} records in one window`,
        actual: { count: shown.count },
      },
      {
        id: "sumAtLeast",
        description: p.sumAtLeast.description,
        result: best ? "TRUE" : shown.sum >= sumAtLeast ? "TRUE" : unknownTail,
        expected: `window total >= ${describeRef(def, p.sumAtLeast.value)}`,
        actual: { total: shown.sum },
      },
      {
        id: "window",
        description: p.window.description,
        result: best ? "TRUE" : unknownTail,
        expected: `records within ${describeRef(def, p.window.days)} day(s) of the first, end inclusive`,
        actual: { qualifyingWindows: qualifying },
      },
    );

    const subjectKey = `vendor:${vendor}`;
    if (best) {
      const ids = best.members.map((m) => m.r.recordId);
      results.push(
        result(def, meta, now, {
          outcome: "MATCH",
          subjectKey,
          matchedRecordIds: ids,
          conditions,
          missingFields: missing,
          evidenceRefs: evidenceRefs(def, best.members.map((m) => m.r)),
          explanation:
            `${label} matched vendor ${vendor}: ${best.members.length} ${p.recordType} record(s)` +
            (eachBelow !== null ? ` each below ${eachBelow}` : "") +
            ` totalling ${best.sum} within ${windowDays} day(s) (configured total ${sumAtLeast}). ${NOT_A_FINDING}`,
        }),
      );
    } else if (missing.length > 0) {
      results.push(
        result(def, meta, now, {
          outcome: "INSUFFICIENT_DATA",
          subjectKey,
          matchedRecordIds: group.map((r) => r.recordId),
          conditions,
          missingFields: missing,
          evidenceRefs: evidenceRefs(def, group),
          explanation: `${label} could not evaluate vendor ${vendor}: missing ${describeMissing(missing)}. ${NOT_CLEARED}`,
        }),
      );
    } else {
      results.push(
        result(def, meta, now, {
          outcome: "NO_MATCH",
          subjectKey,
          matchedRecordIds: group.map((r) => r.recordId),
          conditions,
          missingFields: [],
          evidenceRefs: evidenceRefs(def, group),
          explanation:
            `${label} did not match vendor ${vendor}: no ${windowDays}-day window reached ${minCount} record(s) ` +
            `totalling ${sumAtLeast} (largest window total ${largest.sum}). ${NOT_A_CLEARANCE}`,
        }),
      );
    }
  }
  return { results, outOfScope: 0 };
}
