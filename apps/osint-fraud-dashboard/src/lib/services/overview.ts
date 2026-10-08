import { OPEN_STATES } from "../review";
import { requirePermission, type Ctx } from "./context";

export interface Overview {
  records: { transactions: number; vendors: number; evidence: number; incidents: number; synthetic: number; publicSource: number; internal: number };
  alerts: { awaitingReview: number; byState: Record<string, number>; insufficientData: number };
  evidence: { total: number; complete: number; incomplete: number; verified: number; unverified: number };
  ingestion: { batches: number; rejectedBatches: number; rejectedRows: number; duplicateRows: number };
  rules: { active: number; pendingApproval: number };
  investigations: { open: number };
}

/** Every number on the overview is counted from stored records. Nothing is estimated. */
export async function getOverview(ctx: Ctx): Promise<Overview> {
  await requirePermission(ctx, "workspace:view");
  const db = ctx.db;
  const [transactions, vendors, evidence, incidents] = await Promise.all([db.transaction.count(), db.vendor.count(), db.evidence.count(), db.incident.count()]);
  const [synInc, synTx, synVendor, synEv, pubEv, intEv, pubTx, intTx] = await Promise.all([
    db.incident.count({ where: { isSynthetic: true } }),
    db.transaction.count({ where: { isSynthetic: true } }),
    db.vendor.count({ where: { isSynthetic: true } }),
    db.evidence.count({ where: { isSynthetic: true } }),
    db.evidence.count({ where: { origin: "PUBLIC_SOURCE" } }),
    db.evidence.count({ where: { origin: "INTERNAL_RECORD" } }),
    db.transaction.count({ where: { origin: "PUBLIC_SOURCE" } }),
    db.transaction.count({ where: { origin: "INTERNAL_RECORD" } }),
  ]);
  const byStateRows = await db.alert.groupBy({ by: ["status"], _count: { _all: true } });
  const byState = Object.fromEntries(byStateRows.map((r) => [r.status, r._count._all]));
  const awaitingReview = OPEN_STATES.reduce((s, k) => s + (byState[k] ?? 0), 0);
  const insufficientData = await db.alert.count({ where: { outcome: "INSUFFICIENT_DATA", status: { in: OPEN_STATES } } });
  const [complete, verified] = await Promise.all([
    db.evidence.count({ where: { missingFields: { isEmpty: true } } }),
    db.evidence.count({ where: { verificationStatus: "VERIFIED" } }),
  ]);
  const batches = await db.importBatch.aggregate({ _count: { _all: true }, _sum: { rejectedRows: true, duplicateRows: true } });
  const rejectedBatches = await db.importBatch.count({ where: { status: "REJECTED" } });
  const [active, pending, open] = await Promise.all([
    db.ruleVersion.count({ where: { status: "ACTIVE" } }),
    db.ruleVersion.count({ where: { status: "PENDING_APPROVAL" } }),
    db.investigation.count({ where: { status: { in: OPEN_STATES } } }),
  ]);
  return {
    records: { transactions, vendors, evidence, incidents, synthetic: synInc + synTx + synVendor + synEv, publicSource: pubEv + pubTx, internal: intEv + intTx },
    alerts: { awaitingReview, byState, insufficientData },
    evidence: { total: evidence, complete, incomplete: evidence - complete, verified, unverified: evidence - verified },
    ingestion: {
      batches: batches._count._all,
      rejectedBatches,
      rejectedRows: batches._sum.rejectedRows ?? 0,
      duplicateRows: batches._sum.duplicateRows ?? 0,
    },
    rules: { active, pendingApproval: pending },
    investigations: { open },
  };
}
