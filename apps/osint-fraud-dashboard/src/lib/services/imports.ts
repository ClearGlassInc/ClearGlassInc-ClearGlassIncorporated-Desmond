import type { Prisma, TransactionType } from "@/generated/prisma/client";
import { contentHash } from "../hash";
import {
  validateImport,
  type ImportRequest,
  type NormalizedEvidence,
  type NormalizedIncident,
  type NormalizedRecord,
  type NormalizedTransaction,
  type NormalizedVendor,
  type RowIssue,
} from "../import/validate";
import { audit, requirePermission, type Ctx } from "./context";

export interface ImportReport {
  recordType: string;
  format: string;
  filename: string;
  fileHash: string;
  sizeBytes: number;
  origin: string;
  totalRows: number;
  acceptedRows: number;
  rejectedRows: number;
  duplicateRows: number;
  errors: RowIssue[];
  warnings: RowIssue[];
  duplicates: { row: number; recordId: string; reason: string }[];
  mapping: Record<string, string | null>;
  committed: boolean;
}

export interface ImportOutcome {
  status: "VALIDATED" | "COMMITTED" | "REJECTED";
  batchId: string | null;
  report: ImportReport;
}

type Existing = Map<string, string | null>;

async function existingHashes(ctx: Ctx, recordType: string, ids: string[]): Promise<Existing> {
  if (ids.length === 0) return new Map();
  const where = { recordId: { in: ids } };
  const select = { recordId: true, contentHash: true } as const;
  switch (recordType) {
    case "VENDOR":
      return new Map((await ctx.db.vendor.findMany({ where, select })).map((r) => [r.recordId, r.contentHash]));
    case "TRANSACTION":
      return new Map((await ctx.db.transaction.findMany({ where, select })).map((r) => [r.recordId, r.contentHash]));
    case "EVIDENCE":
      return new Map((await ctx.db.evidence.findMany({ where, select })).map((r) => [r.recordId, r.contentHash]));
    default:
      return new Map(
        (await ctx.db.incident.findMany({ where, select: { recordId: true } })).map((r) => [r.recordId, null]),
      );
  }
}

/**
 * Validate an import and, when commit is true and nothing is wrong, store it.
 * All-or-nothing: one invalid row rejects the batch, so a case is never built
 * on a half-loaded file. Identical re-imports are reported and skipped.
 */
export async function runImport(ctx: Ctx, req: ImportRequest & { commit: boolean }): Promise<ImportOutcome> {
  await requirePermission(ctx, "import:run", { type: "ImportBatch" });
  const parsed = validateImport(req);
  const errors = [...parsed.errors];
  const warnings = [...parsed.warnings];
  const duplicates = parsed.inFileDuplicates.map((d) => ({
    row: d.row,
    recordId: d.recordId,
    reason: `Identical to row ${d.firstRow} in this file; skipped`,
  }));

  const existing = await existingHashes(ctx, req.recordType, parsed.records.map((r) => r.recordId));
  const toInsert: NormalizedRecord[] = [];
  for (const r of parsed.records) {
    if (!existing.has(r.recordId)) {
      toInsert.push(r);
      continue;
    }
    const stored = existing.get(r.recordId);
    if (stored !== null && stored === r.contentHash) {
      duplicates.push({ row: r.row, recordId: r.recordId, reason: "Already imported with identical content; skipped" });
    } else {
      errors.push({
        row: r.row,
        field: "recordId",
        message: `recordId "${r.recordId}" already exists with different content. Use a new id, or correct the stored record first`,
      });
    }
  }

  await checkReferences(ctx, req.recordType, toInsert, errors, warnings);
  await flagIdenticalContent(ctx, req.recordType, toInsert, warnings);

  // File-level problems first, then by row, so the report reads top to bottom.
  errors.sort((a, b) => (a.row ?? 0) - (b.row ?? 0));
  const rejectedRowSet = new Set(errors.filter((e) => e.row !== null).map((e) => e.row));
  const report: ImportReport = {
    recordType: req.recordType,
    format: req.format,
    filename: req.filename,
    fileHash: parsed.fileHash,
    sizeBytes: parsed.sizeBytes,
    origin: req.origin,
    totalRows: parsed.totalRows,
    acceptedRows: errors.length ? 0 : toInsert.length,
    rejectedRows: rejectedRowSet.size,
    duplicateRows: duplicates.length,
    errors,
    warnings,
    duplicates,
    mapping: parsed.mapping,
    committed: false,
  };

  if (!req.commit) {
    await audit(ctx.db, ctx.actor, "import.dry_run", { type: "ImportBatch" }, summary(report));
    return { status: errors.length ? "REJECTED" : "VALIDATED", batchId: null, report };
  }

  if (errors.length) {
    const batch = await ctx.db.importBatch.create({ data: batchData(ctx, req, report, "REJECTED") });
    await audit(ctx.db, ctx.actor, "import.rejected", { type: "ImportBatch", id: batch.id }, summary(report), "failed");
    return { status: "REJECTED", batchId: batch.id, report };
  }

  report.committed = true;
  const batchId = await ctx.db.$transaction(async (tx) => {
    const batch = await tx.importBatch.create({ data: batchData(ctx, req, report, "COMMITTED") });
    for (const r of toInsert) await insertRecord(tx, ctx, req, batch.id, r);
    await audit(tx, ctx.actor, "import.commit", { type: "ImportBatch", id: batch.id }, summary(report));
    return batch.id;
  });
  return { status: "COMMITTED", batchId, report };
}

function summary(r: ImportReport): Prisma.InputJsonValue {
  return {
    recordType: r.recordType,
    filename: r.filename,
    fileHash: r.fileHash,
    totalRows: r.totalRows,
    acceptedRows: r.acceptedRows,
    rejectedRows: r.rejectedRows,
    duplicateRows: r.duplicateRows,
    errorCount: r.errors.length,
  };
}

function batchData(ctx: Ctx, req: ImportRequest, report: ImportReport, status: "COMMITTED" | "REJECTED") {
  return {
    format: req.format,
    recordType: req.recordType,
    filename: req.filename.slice(0, 255),
    fileHash: report.fileHash,
    sizeBytes: report.sizeBytes,
    origin: req.origin,
    isSynthetic: req.origin === "SYNTHETIC",
    status,
    totalRows: report.totalRows,
    acceptedRows: report.acceptedRows,
    rejectedRows: report.rejectedRows,
    duplicateRows: report.duplicateRows,
    report: report as unknown as Prisma.InputJsonValue,
    submittedById: ctx.actor.id,
  } as const;
}

async function checkReferences(
  ctx: Ctx,
  recordType: string,
  records: NormalizedRecord[],
  errors: RowIssue[],
  warnings: RowIssue[],
): Promise<void> {
  if (recordType === "VENDOR") {
    const refs = (records as NormalizedVendor[]).filter((r) => r.organizationRecordId);
    const found = new Set(
      (
        await ctx.db.organization.findMany({
          where: { recordId: { in: refs.map((r) => r.organizationRecordId!) } },
          select: { recordId: true },
        })
      ).map((o) => o.recordId),
    );
    for (const r of refs) {
      if (!found.has(r.organizationRecordId!)) {
        errors.push({ row: r.row, field: "organizationRecordId", message: `Organization "${r.organizationRecordId}" is not in the workspace` });
      }
    }
  }
  if (recordType === "TRANSACTION") {
    const txs = records as NormalizedTransaction[];
    const ev = new Set(
      (
        await ctx.db.evidence.findMany({
          where: { recordId: { in: txs.flatMap((t) => (t.evidenceRecordId ? [t.evidenceRecordId] : [])) } },
          select: { recordId: true },
        })
      ).map((e) => e.recordId),
    );
    const vendors = new Set(
      (
        await ctx.db.vendor.findMany({
          where: { recordId: { in: txs.flatMap((t) => (t.vendorRecordId ? [t.vendorRecordId] : [])) } },
          select: { recordId: true },
        })
      ).map((v) => v.recordId),
    );
    for (const t of txs) {
      if (t.evidenceRecordId && !ev.has(t.evidenceRecordId)) {
        errors.push({ row: t.row, field: "evidenceRecordId", message: `Evidence "${t.evidenceRecordId}" is not in the workspace; import it first` });
      }
      if (t.vendorRecordId && !vendors.has(t.vendorRecordId)) {
        warnings.push({
          row: t.row,
          field: "vendorRecordId",
          message: `Vendor "${t.vendorRecordId}" is not in the workspace. Rules still group on this identifier`,
        });
      }
    }
  }
  if (recordType === "INCIDENT") {
    const incidents = records as NormalizedIncident[];
    const wanted = incidents.flatMap((i) => [...i.evidenceRecordIds, ...i.steps.flatMap((s) => (s.evidenceRecordId ? [s.evidenceRecordId] : []))]);
    const found = new Set((await ctx.db.evidence.findMany({ where: { recordId: { in: wanted } }, select: { recordId: true } })).map((e) => e.recordId));
    for (const i of incidents) {
      for (const id of i.evidenceRecordIds) {
        if (!found.has(id)) errors.push({ row: i.row, field: "evidenceRecordIds", message: `Evidence "${id}" is not in the workspace; import it first` });
      }
      i.steps.forEach((s, n) => {
        if (s.evidenceRecordId && !found.has(s.evidenceRecordId)) {
          errors.push({ row: i.row, field: `steps.${n}.evidenceRecordId`, message: `Evidence "${s.evidenceRecordId}" is not in the workspace` });
        }
      });
    }
  }
}

async function flagIdenticalContent(ctx: Ctx, recordType: string, records: NormalizedRecord[], warnings: RowIssue[]): Promise<void> {
  if (recordType === "INCIDENT" || records.length === 0) return;
  const hashes = records.map((r) => r.contentHash);
  const select = { recordId: true, contentHash: true } as const;
  const where = { contentHash: { in: hashes } };
  const rows =
    recordType === "EVIDENCE"
      ? await ctx.db.evidence.findMany({ where, select })
      : recordType === "VENDOR"
        ? await ctx.db.vendor.findMany({ where, select })
        : await ctx.db.transaction.findMany({ where, select });
  const byHash = new Map(rows.map((r) => [r.contentHash, r.recordId]));
  for (const r of records) {
    const other = byHash.get(r.contentHash);
    if (other && other !== r.recordId) {
      warnings.push({ row: r.row, field: null, message: `Content is identical to stored record "${other}" under a different id; check for a duplicate` });
    }
  }
}

async function insertRecord(
  tx: Prisma.TransactionClient,
  ctx: Ctx,
  req: ImportRequest,
  batchId: string,
  r: NormalizedRecord,
): Promise<void> {
  const origin = req.origin;
  const isSynthetic = origin === "SYNTHETIC";
  switch (r.kind) {
    case "VENDOR": {
      const org = r.organizationRecordId
        ? await tx.organization.findUnique({ where: { recordId: r.organizationRecordId }, select: { id: true } })
        : null;
      await tx.vendor.create({
        data: {
          recordId: r.recordId,
          name: r.name,
          taxId: r.taxId,
          domain: r.domain,
          address: r.address,
          organizationId: org?.id ?? null,
          origin,
          providedFields: r.provided,
          isSynthetic,
          importBatchId: batchId,
          contentHash: r.contentHash,
        },
      });
      return;
    }
    case "TRANSACTION": {
      const vendor = r.vendorRecordId
        ? await tx.vendor.findUnique({ where: { recordId: r.vendorRecordId }, select: { id: true } })
        : null;
      const ev = r.evidenceRecordId
        ? await tx.evidence.findUnique({ where: { recordId: r.evidenceRecordId }, select: { id: true } })
        : null;
      await tx.transaction.create({
        data: {
          recordId: r.recordId,
          type: r.type as TransactionType,
          vendorRecordId: r.vendorRecordId,
          vendorId: vendor?.id ?? null,
          amount: r.amount,
          currency: r.currency,
          occurredAt: r.occurredAt,
          recordedAt: r.recordedAt,
          approvedAt: r.approvedAt,
          workStartedAt: r.workStartedAt,
          approvedBy: r.approvedBy,
          poReference: r.poReference,
          invoiceReference: r.invoiceReference,
          documents: r.documents,
          description: r.description,
          providedFields: r.provided.filter((f) => f !== "recordId" && f !== "type" && f !== "evidenceRecordId"),
          missingFields: r.missing,
          origin,
          isSynthetic,
          evidenceId: ev?.id ?? null,
          importBatchId: batchId,
          contentHash: r.contentHash,
        },
      });
      return;
    }
    case "EVIDENCE":
      await insertEvidence(tx, ctx, r, {
        origin,
        isSynthetic,
        batchId,
        extractionMethod: req.format === "CSV" ? "CSV_IMPORT" : "JSON_IMPORT",
      });
      return;
    case "INCIDENT": {
      const evidence = await tx.evidence.findMany({
        where: { recordId: { in: [...r.evidenceRecordIds, ...r.steps.flatMap((s) => (s.evidenceRecordId ? [s.evidenceRecordId] : []))] } },
        select: { id: true, recordId: true },
      });
      const idOf = new Map(evidence.map((e) => [e.recordId, e.id]));
      await tx.incident.create({
        data: {
          recordId: r.recordId,
          title: r.title,
          summary: r.summary,
          claimStatus: r.claimStatus,
          origin,
          isSynthetic,
          documentedAt: r.documentedAt,
          evidence: { create: r.evidenceRecordIds.map((id) => ({ evidenceId: idOf.get(id)! })) },
          steps: {
            create: r.steps.map((s, i) => ({
              kind: s.kind,
              position: i + 1,
              text: s.text,
              evidenceId: s.evidenceRecordId ? idOf.get(s.evidenceRecordId)! : null,
              // Validation guarantees an uncited step is either an EVIDENCE_GAP or flagged as an assumption.
              isAssumption: s.isAssumption,
              occurredAt: s.occurredAt,
            })),
          },
        },
      });
      return;
    }
  }
}

export async function insertEvidence(
  tx: Prisma.TransactionClient,
  ctx: Ctx,
  r: Omit<NormalizedEvidence, "kind" | "row">,
  opts: {
    origin: "PUBLIC_SOURCE" | "INTERNAL_RECORD" | "SYNTHETIC" | "ANALYST_ENTERED";
    isSynthetic: boolean;
    batchId: string | null;
    extractionMethod: "CSV_IMPORT" | "JSON_IMPORT" | "MANUAL_EXCERPT" | "MOCK_ADAPTER" | "SYNTHETIC_FIXTURE";
  },
): Promise<string> {
  const sourceKey = `SRC-${contentHash({ t: r.sourceTitle, p: r.sourcePublisher, k: r.sourceKind, o: opts.origin }).slice(0, 16)}`;
  const source = await tx.source.upsert({
    where: { recordId: sourceKey },
    update: {},
    create: {
      recordId: sourceKey,
      kind: opts.isSynthetic ? "SYNTHETIC_FIXTURE" : r.sourceKind,
      title: r.sourceTitle,
      publisher: r.sourcePublisher,
      url: r.url ? new URL(r.url).origin : null,
      origin: opts.origin,
      accessClassification: r.accessClassification,
      isSynthetic: opts.isSynthetic,
    },
  });
  const ev = await tx.evidence.create({
    data: {
      recordId: r.recordId,
      sourceId: source.id,
      title: r.title,
      excerpt: r.excerpt,
      url: r.url,
      documentLocation: r.documentLocation,
      publishedAt: r.publishedAt,
      observedAt: r.observedAt,
      // Left null when the source did not say; ingestedAt records when we stored it.
      collectedAt: r.collectedAt,
      contentHash: r.contentHash,
      accessClassification: r.accessClassification,
      extractionMethod: opts.extractionMethod,
      origin: opts.origin,
      limitations: r.limitations,
      providedFields: r.provided,
      missingFields: r.missing,
      isSynthetic: opts.isSynthetic,
      importBatchId: opts.batchId,
    },
  });
  return ev.id;
}
