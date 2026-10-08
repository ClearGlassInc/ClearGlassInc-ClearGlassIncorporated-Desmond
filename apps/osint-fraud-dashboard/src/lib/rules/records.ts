// The record shape the rule engine reads. It is deliberately flat and carries
// the list of fields the source actually supplied, so the engine can tell
// "the source said this is empty" apart from "the source never said".

export const TRANSACTION_TYPES = [
  "PURCHASE_ORDER",
  "INVOICE",
  "PAYMENT",
  "BANK_DETAIL_CHANGE",
  "CHANGE_ORDER",
  "CONTRACT",
] as const;
export type TransactionTypeName = (typeof TRANSACTION_TYPES)[number];

export const RECORD_FIELDS = [
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
] as const;
export type RecordField = (typeof RECORD_FIELDS)[number];

export const DATE_FIELDS: ReadonlySet<RecordField> = new Set([
  "occurredAt",
  "recordedAt",
  "approvedAt",
  "workStartedAt",
]);
export const NUMBER_FIELDS: ReadonlySet<RecordField> = new Set(["amount"]);
export const LIST_FIELDS: ReadonlySet<RecordField> = new Set(["documents"]);

export type FieldValue = string | number | Date | string[] | null;

export interface RecordView {
  /** Database id, used for links. */
  id: string;
  /** Stable record id from the source, used in explanations and alerts. */
  recordId: string;
  type: TransactionTypeName;
  values: Partial<Record<RecordField, FieldValue>>;
  provided: ReadonlySet<RecordField>;
  evidenceRecordId: string | null;
  isSynthetic: boolean;
}

/** UNKNOWN: the source did not supply the field. BLANK: it did, and it is empty. */
export type FieldState =
  | { state: "UNKNOWN" }
  | { state: "BLANK" }
  | { state: "VALUE"; value: Exclude<FieldValue, null> };

export function readField(record: RecordView, field: RecordField): FieldState {
  if (!record.provided.has(field)) return { state: "UNKNOWN" };
  const value = record.values[field];
  if (value === null || value === undefined) return { state: "BLANK" };
  if (typeof value === "string" && value.trim() === "") return { state: "BLANK" };
  if (Array.isArray(value) && value.length === 0) return { state: "BLANK" };
  return { state: "VALUE", value };
}

export function isTransactionType(value: string): value is TransactionTypeName {
  return (TRANSACTION_TYPES as readonly string[]).includes(value);
}
