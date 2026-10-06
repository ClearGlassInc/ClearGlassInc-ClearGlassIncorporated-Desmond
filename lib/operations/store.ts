import { createHash, randomUUID } from "node:crypto";
import { canRead, type Principal } from "@/lib/security";
import { operationsConfig } from "./features";
import type {
  Assignment,
  AuditEvent,
  CustodyEvent,
  EvidenceItem,
  Incident,
  IncidentPriority,
  IncidentStatus,
  LegalHold,
  RetentionPolicy,
  Tenant,
} from "./models";

const DEMO_TENANT_ID = "clearglass-demo-tenant";
const DEMO_OPERATOR = "operator-demo";
const DEMO_REVIEWER = "reviewer-demo";

const allowedTransitions: Record<IncidentStatus, readonly IncidentStatus[]> = {
  open: ["assigned"],
  assigned: ["open", "in_review"],
  in_review: ["assigned", "resolved"],
  resolved: ["in_review", "closed"],
  closed: [],
};

export const syntheticPrincipal = (subject = DEMO_OPERATOR): Principal => ({
  subject,
  role: subject === DEMO_REVIEWER ? "workspace_admin" : "operator",
  tenantId: DEMO_TENANT_ID,
});

export const sha256Hex = (bytes: Uint8Array): string =>
  createHash("sha256").update(bytes).digest("hex");

export function canDeleteEvidence(
  evidence: EvidenceItem,
  legalHold: LegalHold | undefined,
  now = new Date(),
  policy?: RetentionPolicy,
): boolean {
  if (legalHold?.active) return false;
  if (!policy || policy.tenantId !== evidence.tenantId) return false;
  const created = Date.parse(evidence.createdAt);
  if (Number.isNaN(created)) return false;
  const expiresAt = created + policy.retentionDays * 86_400_000;
  return now.getTime() >= expiresAt;
}

type StoredData = {
  tenant: Tenant;
  incidents: Map<string, Incident>;
  assignments: Map<string, Assignment>;
  evidence: Map<string, EvidenceItem>;
  evidenceBytes: Map<string, Uint8Array>;
  custody: CustodyEvent[];
  audit: AuditEvent[];
};

const globalKey = "__clearglass_operations_store__";
type GlobalWithStore = typeof globalThis & { __clearglass_operations_store__?: OperationsStore };
const globalScope = globalThis as GlobalWithStore;

export class OperationsStore {
  private readonly data: StoredData;

  constructor() {
    this.data = {
      tenant: { id: DEMO_TENANT_ID, name: "ClearGlass Synthetic Workspace", createdAt: new Date(0).toISOString() },
      incidents: new Map(),
      assignments: new Map(),
      evidence: new Map(),
      evidenceBytes: new Map(),
      custody: [],
      audit: [],
    };
  }

  private requireEnabled() {
    if (!operationsConfig.enabled) throw new Error("operations module disabled");
    if (operationsConfig.mode === "blocked") throw new Error("operations module blocked");
    if (operationsConfig.mode === "live") {
      throw new Error("live operations persistence/auth adapter is not configured");
    }
  }

  private authorize(principal: Principal, tenantId: string) {
    if (principal.subject === "anonymous") throw new Error("authentication required");
    if (!canRead(principal, "WORKSPACE", tenantId)) throw new Error("forbidden");
    if (principal.tenantId !== tenantId) throw new Error("tenant isolation failure");
  }

  private audit(
    principal: Principal,
    action: string,
    entityType: AuditEvent["entityType"],
    entityId: string,
    metadata: AuditEvent["metadata"] = {},
  ) {
    const event: AuditEvent = {
      id: randomUUID(),
      tenantId: principal.tenantId ?? DEMO_TENANT_ID,
      actor: principal.subject,
      action,
      entityType,
      entityId,
      metadata,
      createdAt: new Date().toISOString(),
    };
    this.data.audit.push(event);
    return event;
  }

  createIncident(
    principal: Principal,
    input: { title: string; description?: string; category: string; priority: IncidentPriority },
  ): Incident {
    this.requireEnabled();
    this.authorize(principal, principal.tenantId ?? DEMO_TENANT_ID);
    const title = input.title.trim();
    const category = input.category.trim();
    if (!title || !category) throw new Error("incident title and category are required");
    const now = new Date().toISOString();
    const incident: Incident = {
      id: randomUUID(),
      tenantId: principal.tenantId ?? DEMO_TENANT_ID,
      title,
      description: (input.description ?? "").trim(),
      category,
      priority: input.priority,
      status: "open",
      createdBy: principal.subject,
      createdAt: now,
      updatedAt: now,
    };
    this.data.incidents.set(incident.id, incident);
    this.audit(principal, "incident.created", "incident", incident.id, { priority: incident.priority });
    return incident;
  }

  assignIncident(principal: Principal, incidentId: string, assignee: string): Assignment {
    this.requireEnabled();
    const incident = this.getIncident(principal, incidentId);
    if (!assignee.trim()) throw new Error("assignee is required");
    if (!allowedTransitions[incident.status].includes("assigned")) throw new Error("invalid incident transition");
    const now = new Date().toISOString();
    const assignment: Assignment = {
      id: randomUUID(),
      tenantId: incident.tenantId,
      incidentId: incident.id,
      assignedBy: principal.subject,
      assignee: assignee.trim(),
      createdAt: now,
    };
    this.data.assignments.set(assignment.id, assignment);
    const previous = incident.status;
    incident.assignedTo = assignment.assignee;
    incident.status = "assigned";
    incident.updatedAt = now;
    this.audit(principal, "incident.assigned", "assignment", assignment.id, { incidentId: incident.id, assignee: assignment.assignee });
    this.audit(principal, "incident.status_changed", "incident", incident.id, { from: previous, to: incident.status });
    return assignment;
  }

  ingestEvidence(
    principal: Principal,
    incidentId: string,
    input: { filename: string; contentType: string; bytes: Uint8Array },
  ): EvidenceItem {
    this.requireEnabled();
    if (!operationsConfig.features.evidence) throw new Error("evidence module disabled");
    const incident = this.getIncident(principal, incidentId);
    if (!input.filename.trim()) throw new Error("filename is required");
    if (!input.contentType.trim()) throw new Error("content type is required");
    if (input.bytes.byteLength > operationsConfig.maxEvidenceBytes) throw new Error("evidence exceeds configured size limit");

    const now = new Date().toISOString();
    const id = randomUUID();
    const sha256 = sha256Hex(input.bytes);
    const item: EvidenceItem = {
      id,
      tenantId: incident.tenantId,
      incidentId: incident.id,
      filename: input.filename.trim(),
      contentType: input.contentType.trim().toLowerCase(),
      sizeBytes: input.bytes.byteLength,
      sha256,
      storageKey: `mock://evidence/${id}/original`,
      status: "quarantined",
      createdBy: principal.subject,
      createdAt: now,
      version: 1,
    };

    this.data.evidence.set(item.id, item);
    this.data.evidenceBytes.set(item.id, new Uint8Array(input.bytes));
    this.data.custody.push({
      id: randomUUID(),
      tenantId: item.tenantId,
      evidenceId: item.id,
      actor: principal.subject,
      action: "ingested",
      evidenceSha256: item.sha256,
      createdAt: now,
    });
    this.audit(principal, "evidence.ingested", "evidence", item.id, { sha256: item.sha256, sizeBytes: item.sizeBytes, status: item.status });
    return item;
  }

  releaseAfterMockScan(principal: Principal, evidenceId: string): EvidenceItem {
    this.requireEnabled();
    const evidence = this.data.evidence.get(evidenceId);
    if (!evidence) throw new Error("evidence not found");
    this.authorize(principal, evidence.tenantId);
    if (evidence.status !== "quarantined") throw new Error("evidence is not awaiting scan");
    evidence.status = "available";
    this.audit(principal, "evidence.scan_completed", "evidence", evidence.id, { result: "synthetic-pass" });
    return evidence;
  }

  verifyEvidence(principal: Principal, evidenceId: string): { matches: boolean; recordedSha256: string; computedSha256: string } {
    this.requireEnabled();
    const evidence = this.data.evidence.get(evidenceId);
    if (!evidence) throw new Error("evidence not found");
    this.authorize(principal, evidence.tenantId);
    const bytes = this.data.evidenceBytes.get(evidence.id);
    if (!bytes) throw new Error("evidence bytes unavailable");
    const computedSha256 = sha256Hex(bytes);
    const matches = computedSha256 === evidence.sha256;
    const now = new Date().toISOString();
    this.data.custody.push({
      id: randomUUID(),
      tenantId: evidence.tenantId,
      evidenceId: evidence.id,
      actor: principal.subject,
      action: "verified",
      evidenceSha256: computedSha256,
      createdAt: now,
    });
    this.audit(principal, "evidence.verified", "evidence", evidence.id, { matches, computedSha256 });
    return { matches, recordedSha256: evidence.sha256, computedSha256 };
  }

  updateStatus(principal: Principal, incidentId: string, status: IncidentStatus): Incident {
    this.requireEnabled();
    const incident = this.getIncident(principal, incidentId);
    if (!allowedTransitions[incident.status].includes(status)) throw new Error("invalid incident transition");
    const previous = incident.status;
    incident.status = status;
    incident.updatedAt = new Date().toISOString();
    this.audit(principal, "incident.status_changed", "incident", incident.id, { from: previous, to: status });
    return incident;
  }

  getIncident(principal: Principal, incidentId: string) {
    this.requireEnabled();
    const incident = this.data.incidents.get(incidentId);
    if (!incident) throw new Error("incident not found");
    this.authorize(principal, incident.tenantId);
    return incident;
  }

  getSnapshot(principal: Principal, incidentId: string) {
    const incident = this.getIncident(principal, incidentId);
    const evidence = [...this.data.evidence.values()].filter((e) => e.incidentId === incident.id);
    const custody = this.data.custody.filter((e) => evidence.some((item) => item.id === e.evidenceId));
    const audit = this.data.audit.filter((event) => event.tenantId === incident.tenantId);
    return { tenant: this.data.tenant, incident, evidence, custody, audit };
  }

  async runSyntheticVerticalSlice() {
    this.requireEnabled();
    const operator = syntheticPrincipal();
    const reviewer = syntheticPrincipal(DEMO_REVIEWER);
    const incident = this.createIncident(operator, {
      title: "Synthetic evidence intake drill",
      description: "Synthetic test data only. No real person, device, or external source.",
      category: "platform-test",
      priority: "medium",
    });
    const assignment = this.assignIncident(operator, incident.id, reviewer.subject);
    const bytes = new TextEncoder().encode("CLEARGLASS SYNTHETIC EVIDENCE v1");
    const evidence = this.ingestEvidence(operator, incident.id, {
      filename: "synthetic-evidence.txt",
      contentType: "text/plain",
      bytes,
    });
    const scanned = this.releaseAfterMockScan(operator, evidence.id);
    const verification = this.verifyEvidence(reviewer, scanned.id);
    const updated = this.updateStatus(operator, incident.id, "in_review");
    const snapshot = this.getSnapshot(reviewer, incident.id);
    return {
      mode: operationsConfig.mode,
      synthetic: true,
      incident: updated,
      assignment,
      evidence: scanned,
      verification,
      audit: snapshot.audit,
      custody: snapshot.custody,
    };
  }
}

export function getOperationsStore(): OperationsStore {
  if (!globalScope[globalKey]) globalScope[globalKey] = new OperationsStore();
  return globalScope[globalKey]!;
}
