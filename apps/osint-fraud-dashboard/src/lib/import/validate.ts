// Pure import validation: bytes in, normalised records and an actionable
// report out. No database access here; services/imports.ts adds the checks
// that need it (duplicates against stored records, references) and commits.

import { z } from "zod";
import { contentHash, sha256 } from "../hash";
import { cleanText, parsePublicUrl } from "../text";
import { parseCsv, CsvError } from "./csv";
import {
  buildMapping,
  CANONICAL_FIELDS,
  EVIDENCE_PROVENANCE_FIELDS,
  EXPECTED_TRANSACTION_FIELDS,
  type ImportRecordTypeName,
} from "./fields";

export type ImportFormatName = "CSV" | "JSON";
export type ImportOriginName = "PUBLIC_SOURCE" | "INTERNAL_RECORD" | "SYNTHETIC";

export interface RowIssue {
  row: number | null;
  line?: number;
  field: string | null;
  message: string;
}

export interface ImportRequest {
  filename: string;
  bytes: Uint8Array;
  format: ImportFormatName;
  recordType: ImportRecordTypeName;
  origin: ImportOriginName;
  mapping: Record<string, string> | null;
  limits: { maxBytes: number; maxRows: number };
}

export interface NormalizedBase {
  row: number;
  recordId: string;
  provided: string[];
  missing: string[];
  contentHash: string;
}
export interface NormalizedVendor extends NormalizedBase {
  kind: "VENDOR";
  name: string;
  taxId: string | null;
  domain: string | null;
  address: string | null;
  organizationRecordId: string | null;
}
export interface NormalizedTransaction extends NormalizedBase {
  kind: "TRANSACTION";
  type: string;
  vendorRecordId: string | null;
  amount: number | null;
  currency: string | null;
  occurredAt: Date | null;
  recordedAt: Date | null;
  approvedAt: Date | null;
  workStartedAt: Date | null;
  approvedBy: string | null;
  poReference: string | null;
  invoiceReference: string | null;
  documents: string[];
  description: string | null;
  evidenceRecordId: string | null;
}
export interface NormalizedEvidence extends NormalizedBase {
  kind: "EVIDENCE";
  title: string;
  excerpt: string;
  url: string | null;
  sourceTitle: string;
  sourcePublisher: string | null;
  sourceKind: "PUBLIC_WEB" | "PUBLIC_RECORD" | "INTERNAL_SYSTEM" | "ANALYST_PROVIDED";
  documentLocation: string | null;
  publishedAt: Date | null;
  observedAt: Date | null;
  collectedAt: Date | null;
  accessClassification: "PUBLIC" | "INTERNAL" | "CONFIDENTIAL" | "RESTRICTED";
  limitations: string | null;
}
export interface NormalizedIncidentStep {
  kind: "OBSERVATION" | "ACTOR" | "EVENT" | "EVIDENCE_GAP" | "CONTRADICTION";
  text: string;
  evidenceRecordId: string | null;
  isAssumption: boolean;
  occurredAt: Date | null;
}
export interface NormalizedIncident extends NormalizedBase {
  kind: "INCIDENT";
  title: string;
  summary: string;
  claimStatus: "ALLEGATION" | "SOURCE_SUPPORTED_OBSERVATION";
  documentedAt: Date | null;
  evidenceRecordIds: string[];
  steps: NormalizedIncidentStep[];
}
export type NormalizedRecord = NormalizedVendor | NormalizedTransaction | NormalizedEvidence | NormalizedIncident;

export interface ParsedImport {
  fileHash: string;
  sizeBytes: number;
  totalRows: number;
  records: NormalizedRecord[];
  errors: RowIssue[];
  warnings: RowIssue[];
  inFileDuplicates: { row: number; recordId: string; firstRow: number }[];
  mapping: Record<string, string | null>;
  unmappedColumns: string[];
}

// ---------------------------------------------------------------- field parsers

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const ISO_DATETIME = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d{1,3})?)?(Z|[+-]\d{2}:\d{2})$/;

export function parseIsoDate(raw: string): Date | null {
  const s = raw.trim();
  if (ISO_DATE.test(s)) {
    const d = new Date(`${s}T00:00:00Z`);
    return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === s ? d : null;
  }
  if (ISO_DATETIME.test(s)) {
    const d = new Date(s);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  return null;
}

// .optional() matters: in zod 4 a key absent from the row is otherwise "required".
// Absent keys reach the transforms as undefined and become null (unknown).
const raw = z.union([z.string(), z.number(), z.boolean(), z.null(), z.array(z.unknown())]).optional();

function blank(v: unknown): boolean {
  return v === undefined || v === null || (typeof v === "string" && v.trim() === "");
}

const text = (max: number) =>
  raw.transform((v, ctx) => {
    if (blank(v)) return null;
    if (typeof v !== "string") {
      ctx.addIssue({ code: "custom", message: "Expected text" });
      return z.NEVER;
    }
    const t = cleanText(v).trim();
    if (t.length > max) {
      ctx.addIssue({ code: "custom", message: `Longer than ${max} characters` });
      return z.NEVER;
    }
    return t;
  });

const requiredText = (max: number) =>
  text(max).transform((v, ctx) => {
    if (v === null) {
      ctx.addIssue({ code: "custom", message: "Required" });
      return z.NEVER;
    }
    return v;
  });

const recordIdSchema = requiredText(80).refine((v) => /^[A-Za-z0-9][A-Za-z0-9._:\-]{0,79}$/.test(v), {
  message: "Record ids use letters, digits, '.', '_', ':' or '-' (max 80)",
});

const optionalRef = text(80).refine((v) => v === null || /^[A-Za-z0-9][A-Za-z0-9._:\-]{0,79}$/.test(v), {
  message: "Not a valid record id",
});

const isoDateField = raw.transform((v, ctx) => {
  if (blank(v)) return null;
  const d = typeof v === "string" ? parseIsoDate(v) : null;
  if (!d) {
    ctx.addIssue({
      code: "custom",
      message: `"${String(v)}" is not ISO 8601. Use YYYY-MM-DD or YYYY-MM-DDTHH:mm:ssZ (a time needs Z or an offset)`,
    });
    return z.NEVER;
  }
  return d;
});

const amountField = raw.transform((v, ctx) => {
  if (blank(v)) return null;
  if (typeof v === "number" && Number.isFinite(v)) return Math.round(v * 100) / 100;
  if (typeof v === "string" && /^-?\d+(\.\d{1,2})?$/.test(v.trim())) return Number(v.trim());
  ctx.addIssue({ code: "custom", message: `"${String(v)}" is not a plain decimal amount (no currency symbols or thousands separators, max 2 decimals)` });
  return z.NEVER;
});

const listField = raw.transform((v, ctx) => {
  if (blank(v)) return [] as string[];
  const items = Array.isArray(v) ? v : typeof v === "string" ? v.split(";") : null;
  if (!items || items.some((i) => typeof i !== "string")) {
    ctx.addIssue({ code: "custom", message: "Expected a list: a JSON array of strings, or values separated by ';' in CSV" });
    return z.NEVER;
  }
  return (items as string[]).map((i) => cleanText(i).trim().toLowerCase()).filter(Boolean);
});

const enumField = <T extends string>(values: readonly T[], fallback: T | null) =>
  raw.transform((v, ctx): T => {
    if (blank(v)) {
      if (fallback !== null) return fallback;
      ctx.addIssue({ code: "custom", message: `Required; one of ${values.join(", ")}` });
      return z.NEVER;
    }
    const s = String(v).trim().toUpperCase().replace(/[\s-]+/g, "_");
    if (!(values as readonly string[]).includes(s)) {
      ctx.addIssue({ code: "custom", message: `"${String(v)}" is not one of ${values.join(", ")}` });
      return z.NEVER;
    }
    return s as T;
  });

const urlField = text(2048).transform((v, ctx) => {
  if (v === null) return null;
  const parsed = parsePublicUrl(v);
  if (!parsed.ok) {
    ctx.addIssue({ code: "custom", message: parsed.error });
    return z.NEVER;
  }
  return parsed.url;
});

const domainField = text(253).transform((v, ctx) => {
  if (v === null) return null;
  const d = v.toLowerCase().replace(/^https?:\/\//, "").replace(/\/.*$/, "");
  if (!/^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,62}$/.test(d)) {
    ctx.addIssue({ code: "custom", message: `"${v}" is not a domain name` });
    return z.NEVER;
  }
  return d;
});

const currencyField = text(40).transform((v, ctx) => {
  if (v === null) return null;
  if (!/^[A-Za-z]{3}$/.test(v)) {
    ctx.addIssue({ code: "custom", message: "Use a three-letter ISO 4217 code such as CAD" });
    return z.NEVER;
  }
  return v.toUpperCase();
});

// ---------------------------------------------------------------- row schemas

const vendorSchema = z.object({
  recordId: recordIdSchema,
  name: requiredText(200),
  taxId: text(64),
  domain: domainField,
  address: text(400),
  organizationRecordId: optionalRef,
});

const TX_TYPES = ["PURCHASE_ORDER", "INVOICE", "PAYMENT", "BANK_DETAIL_CHANGE", "CHANGE_ORDER", "CONTRACT"] as const;
const transactionSchema = z.object({
  recordId: recordIdSchema,
  type: enumField(TX_TYPES, null),
  vendorRecordId: optionalRef,
  amount: amountField,
  currency: currencyField,
  occurredAt: isoDateField,
  recordedAt: isoDateField,
  approvedAt: isoDateField,
  workStartedAt: isoDateField,
  approvedBy: text(200),
  poReference: text(80),
  invoiceReference: text(80),
  documents: listField,
  description: text(2000),
  evidenceRecordId: optionalRef,
});

const SOURCE_KINDS = ["PUBLIC_WEB", "PUBLIC_RECORD", "INTERNAL_SYSTEM", "ANALYST_PROVIDED"] as const;
const CLASSIFICATIONS = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"] as const;
const evidenceSchema = z.object({
  recordId: recordIdSchema,
  title: requiredText(300),
  excerpt: requiredText(20_000),
  url: urlField,
  sourceTitle: requiredText(300),
  sourcePublisher: text(200),
  sourceKind: enumField(SOURCE_KINDS, "ANALYST_PROVIDED"),
  documentLocation: text(300),
  publishedAt: isoDateField,
  observedAt: isoDateField,
  collectedAt: isoDateField,
  accessClassification: raw,
  limitations: text(2000),
});

const STEP_KINDS = ["OBSERVATION", "ACTOR", "EVENT", "EVIDENCE_GAP", "CONTRADICTION"] as const;
const incidentSchema = z.object({
  recordId: recordIdSchema,
  title: requiredText(300),
  summary: requiredText(5000),
  claimStatus: enumField(["ALLEGATION", "SOURCE_SUPPORTED_OBSERVATION"] as const, "ALLEGATION"),
  documentedAt: isoDateField,
  evidenceRecordIds: z.array(z.string().min(1).max(80)).default([]),
  steps: z
    .array(
      z.object({
        kind: enumField(STEP_KINDS, null),
        text: requiredText(2000),
        evidenceRecordId: optionalRef.optional().transform((v) => v ?? null),
        isAssumption: z.boolean().default(false),
        occurredAt: isoDateField.optional().transform((v) => v ?? null),
      }),
    )
    .min(1, "An incident needs at least one documented observation, event or evidence gap"),
});

// ---------------------------------------------------------------- driver

function issuesFrom(error: z.ZodError, row: number, line?: number): RowIssue[] {
  return error.issues.map((i) => ({ row, line, field: i.path.length ? i.path.join(".") : null, message: i.message }));
}

function decodeUtf8(bytes: Uint8Array): string | null {
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  } catch {
    return null;
  }
}

interface RawRow {
  row: number;
  line?: number;
  values: Record<string, unknown>;
}

export function validateImport(req: ImportRequest): ParsedImport {
  const errors: RowIssue[] = [];
  const warnings: RowIssue[] = [];
  const fileHash = sha256(Buffer.from(req.bytes));
  const empty: ParsedImport = {
    fileHash,
    sizeBytes: req.bytes.byteLength,
    totalRows: 0,
    records: [],
    errors,
    warnings,
    inFileDuplicates: [],
    mapping: {},
    unmappedColumns: [],
  };
  const fileError = (message: string) => {
    errors.push({ row: null, field: null, message });
    return empty;
  };

  const ext = req.filename.toLowerCase().split(".").pop();
  if (req.format === "CSV" && ext !== "csv") return fileError("A CSV import needs a .csv file");
  if (req.format === "JSON" && ext !== "json") return fileError("A JSON import needs a .json file");
  if (req.recordType === "INCIDENT" && req.format !== "JSON") return fileError("Incidents are imported as JSON only");
  if (req.bytes.byteLength === 0) return fileError("The file is empty");
  if (req.bytes.byteLength > req.limits.maxBytes) {
    return fileError(`The file is ${req.bytes.byteLength} bytes; the limit is ${req.limits.maxBytes}`);
  }
  const textContent = decodeUtf8(req.bytes);
  if (textContent === null) return fileError("The file is not valid UTF-8 text");

  let rows: RawRow[];
  let headers: string[];
  if (req.format === "CSV") {
    let parsed;
    try {
      parsed = parseCsv(textContent);
    } catch (e) {
      return fileError(e instanceof CsvError ? `CSV syntax error at ${e.message}` : "CSV could not be parsed");
    }
    if (parsed.length < 2) return fileError("The CSV needs a header row and at least one data row");
    headers = parsed[0].cells.map((h) => h.trim());
    rows = [];
    for (const [i, r] of parsed.slice(1).entries()) {
      if (r.cells.length !== headers.length) {
        errors.push({ row: i + 1, line: r.line, field: null, message: `Has ${r.cells.length} cells; the header has ${headers.length}` });
        continue;
      }
      rows.push({ row: i + 1, line: r.line, values: Object.fromEntries(headers.map((h, j) => [h, r.cells[j]])) });
    }
  } else {
    let data: unknown;
    try {
      data = JSON.parse(textContent);
    } catch (e) {
      return fileError(`JSON syntax error: ${e instanceof Error ? e.message : "invalid JSON"}`);
    }
    if (!Array.isArray(data)) return fileError("The JSON file must contain an array of records");
    rows = [];
    const keys = new Set<string>();
    for (const [i, item] of data.entries()) {
      if (!item || typeof item !== "object" || Array.isArray(item)) {
        errors.push({ row: i + 1, field: null, message: "Each item must be a JSON object" });
        continue;
      }
      Object.keys(item).forEach((k) => keys.add(k));
      rows.push({ row: i + 1, values: item as Record<string, unknown> });
    }
    headers = [...keys];
  }

  empty.totalRows = rows.length + errors.filter((e) => e.row !== null).length;
  if (empty.totalRows > req.limits.maxRows) return fileError(`The file has ${empty.totalRows} rows; the limit is ${req.limits.maxRows}`);

  // Incidents are nested JSON and are not column-mapped.
  const canonical =
    req.recordType === "INCIDENT"
      ? ["recordId", "title", "summary", "claimStatus", "documentedAt", "evidenceRecordIds", "steps"]
      : CANONICAL_FIELDS[req.recordType];
  const mapping = buildMapping(headers, canonical, req.recordType === "INCIDENT" ? null : req.mapping);
  empty.mapping = mapping.columns;
  empty.unmappedColumns = mapping.unmapped;
  for (const m of mapping.errors) errors.push({ row: null, field: null, message: m });
  for (const col of mapping.unmapped) warnings.push({ row: null, field: col, message: "Column is not mapped to a field and will be ignored" });
  if (!Object.values(mapping.columns).includes("recordId")) {
    errors.push({ row: null, field: "recordId", message: "No column maps to recordId; every record needs a stable id" });
  }
  if (mapping.errors.length || !Object.values(mapping.columns).includes("recordId")) return empty;

  const seen = new Map<string, { row: number; hash: string }>();
  for (const r of rows) {
    const values: Record<string, unknown> = {};
    for (const [col, field] of Object.entries(mapping.columns)) {
      if (field && col in r.values) values[field] = r.values[col];
    }
    // A CSV column that exists is "supplied" even when the cell is empty; a
    // JSON key is supplied when present. Absent keys stay unknown.
    const provided = Object.keys(values).sort();
    const normalised = normalise(req, r, values, provided, errors);
    if (!normalised) continue;
    const prior = seen.get(normalised.recordId);
    if (prior) {
      if (prior.hash === normalised.contentHash) {
        empty.inFileDuplicates.push({ row: r.row, recordId: normalised.recordId, firstRow: prior.row });
      } else {
        errors.push({
          row: r.row,
          line: r.line,
          field: "recordId",
          message: `recordId "${normalised.recordId}" already appears on row ${prior.row} with different content`,
        });
      }
      continue;
    }
    seen.set(normalised.recordId, { row: r.row, hash: normalised.contentHash });
    empty.records.push(normalised);
  }
  return empty;
}

function normalise(
  req: ImportRequest,
  r: RawRow,
  values: Record<string, unknown>,
  provided: string[],
  errors: RowIssue[],
): NormalizedRecord | null {
  switch (req.recordType) {
    case "VENDOR": {
      const p = vendorSchema.safeParse(values);
      if (!p.success) return void errors.push(...issuesFrom(p.error, r.row, r.line)), null;
      const missing = ["taxId", "domain", "address"].filter((f) => p.data[f as keyof typeof p.data] === null);
      return { kind: "VENDOR", row: r.row, provided, missing, contentHash: contentHash({ t: "VENDOR", ...p.data }), ...p.data };
    }
    case "TRANSACTION": {
      const p = transactionSchema.safeParse(values);
      if (!p.success) return void errors.push(...issuesFrom(p.error, r.row, r.line)), null;
      const d = p.data;
      const expected = EXPECTED_TRANSACTION_FIELDS[d.type] ?? [];
      const missing = expected.filter((f) => {
        const v = d[f as keyof typeof d];
        return !provided.includes(f) || v === null || (Array.isArray(v) && v.length === 0);
      });
      return {
        kind: "TRANSACTION",
        row: r.row,
        provided,
        missing,
        contentHash: contentHash({ t: "TRANSACTION", ...d, provided }),
        ...d,
      };
    }
    case "EVIDENCE": {
      const p = evidenceSchema.safeParse(values);
      if (!p.success) return void errors.push(...issuesFrom(p.error, r.row, r.line)), null;
      const defaultClass = req.origin === "INTERNAL_RECORD" ? "INTERNAL" : "PUBLIC";
      const cls = enumField(CLASSIFICATIONS, defaultClass).safeParse(p.data.accessClassification);
      if (!cls.success) return void errors.push(...issuesFrom(cls.error, r.row, r.line).map((i) => ({ ...i, field: "accessClassification" }))), null;
      if (req.origin === "PUBLIC_SOURCE" && cls.data !== "PUBLIC") {
        errors.push({ row: r.row, line: r.line, field: "accessClassification", message: "A public-source import can only hold PUBLIC evidence; import internal material as an internal record" });
        return null;
      }
      const data = { ...p.data, accessClassification: cls.data };
      const missing = EVIDENCE_PROVENANCE_FIELDS.filter((f) => data[f] === null);
      return {
        kind: "EVIDENCE",
        row: r.row,
        provided,
        missing,
        // Hash the collected material itself, not our import bookkeeping.
        contentHash: contentHash({ excerpt: data.excerpt, url: data.url, documentLocation: data.documentLocation, publishedAt: data.publishedAt }),
        ...data,
      };
    }
    case "INCIDENT": {
      const p = incidentSchema.safeParse(values);
      if (!p.success) return void errors.push(...issuesFrom(p.error, r.row, r.line)), null;
      const bad = p.data.steps.findIndex((s) => !s.evidenceRecordId && !s.isAssumption && s.kind !== "EVIDENCE_GAP");
      if (bad >= 0) {
        errors.push({
          row: r.row,
          field: `steps.${bad}`,
          message: "Step has no evidenceRecordId. Cite evidence, or set isAssumption: true so it is shown as an analyst assumption",
        });
        return null;
      }
      return { kind: "INCIDENT", row: r.row, provided, missing: [], contentHash: contentHash({ t: "INCIDENT", ...p.data }), ...p.data };
    }
  }
}
