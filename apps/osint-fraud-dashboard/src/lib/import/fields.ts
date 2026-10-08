// Canonical import fields per record type, and the column-to-field mapping.

export type ImportRecordTypeName = "VENDOR" | "TRANSACTION" | "EVIDENCE" | "INCIDENT";

export const CANONICAL_FIELDS: Record<Exclude<ImportRecordTypeName, "INCIDENT">, readonly string[]> = {
  VENDOR: ["recordId", "name", "taxId", "domain", "address", "organizationRecordId"],
  TRANSACTION: [
    "recordId",
    "type",
    "vendorRecordId",
    "amount",
    "currency",
    "occurredAt",
    "recordedAt",
    "approvedAt",
    "workStartedAt",
    "approvedBy",
    "poReference",
    "invoiceReference",
    "documents",
    "description",
    "evidenceRecordId",
  ],
  EVIDENCE: [
    "recordId",
    "title",
    "excerpt",
    "url",
    "sourceTitle",
    "sourcePublisher",
    "sourceKind",
    "documentLocation",
    "publishedAt",
    "observedAt",
    "collectedAt",
    "accessClassification",
    "limitations",
  ],
};

/** Fields a reviewer expects on each transaction type; absent ones are listed as missing. */
export const EXPECTED_TRANSACTION_FIELDS: Record<string, readonly string[]> = {
  PAYMENT: ["vendorRecordId", "amount", "occurredAt", "approvedAt", "poReference"],
  PURCHASE_ORDER: ["vendorRecordId", "amount", "occurredAt", "documents"],
  BANK_DETAIL_CHANGE: ["vendorRecordId", "occurredAt"],
  CHANGE_ORDER: ["vendorRecordId", "amount", "approvedAt", "workStartedAt"],
  INVOICE: ["vendorRecordId", "amount", "occurredAt", "invoiceReference"],
  CONTRACT: ["vendorRecordId", "amount", "occurredAt", "documents"],
};

/** Provenance fields whose absence makes evidence incomplete. */
export const EVIDENCE_PROVENANCE_FIELDS = ["url", "documentLocation", "publishedAt", "collectedAt", "sourcePublisher"] as const;

function normaliseHeader(header: string): string {
  return header.trim().toLowerCase().replace(/[\s_\-]+/g, "");
}

export interface Mapping {
  /** source column -> canonical field, or null when ignored */
  columns: Record<string, string | null>;
  unmapped: string[];
  errors: string[];
}

/**
 * Build the mapping for a header row. An explicit mapping wins; otherwise a
 * column maps to the canonical field whose name matches ignoring case, spaces,
 * underscores and hyphens (po_reference -> poReference).
 */
export function buildMapping(
  headers: string[],
  canonical: readonly string[],
  explicit: Record<string, string> | null,
): Mapping {
  const columns: Record<string, string | null> = {};
  const unmapped: string[] = [];
  const errors: string[] = [];
  const byNormalised = new Map(canonical.map((f) => [normaliseHeader(f), f]));
  const seen = new Map<string, string>();

  if (explicit) {
    for (const [col, field] of Object.entries(explicit)) {
      if (!headers.includes(col)) errors.push(`Mapping names column "${col}", which is not in the file`);
      if (!canonical.includes(field)) errors.push(`Mapping target "${field}" is not a field of this record type`);
    }
  }
  for (const h of headers) {
    if (h.trim() === "") {
      errors.push("A column has an empty header");
      continue;
    }
    const target = explicit && h in explicit ? explicit[h] : byNormalised.get(normaliseHeader(h)) ?? null;
    if (!target || !canonical.includes(target)) {
      columns[h] = null;
      unmapped.push(h);
      continue;
    }
    const prior = seen.get(target);
    if (prior) errors.push(`Columns "${prior}" and "${h}" both map to "${target}"`);
    seen.set(target, h);
    columns[h] = target;
  }
  return { columns, unmapped, errors };
}
