export type IncidentPriority = "low" | "medium" | "high" | "critical";
export type IncidentStatus = "open" | "assigned" | "in_review" | "resolved" | "closed";

export type Tenant = {
  id: string;
  name: string;
  createdAt: string;
};

export type Incident = {
  id: string;
  tenantId: string;
  title: string;
  description: string;
  category: string;
  priority: IncidentPriority;
  status: IncidentStatus;
  createdBy: string;
  assignedTo?: string;
  createdAt: string;
  updatedAt: string;
};

export type Assignment = {
  id: string;
  tenantId: string;
  incidentId: string;
  assignedBy: string;
  assignee: string;
  createdAt: string;
};

export type EvidenceStatus = "quarantined" | "available" | "rejected" | "held";

export type EvidenceItem = {
  id: string;
  tenantId: string;
  incidentId: string;
  filename: string;
  contentType: string;
  sizeBytes: number;
  sha256: string;
  storageKey: string;
  status: EvidenceStatus;
  createdBy: string;
  createdAt: string;
  version: number;
};

export type CustodyAction = "ingested" | "verified" | "accessed" | "exported" | "held";

export type CustodyEvent = {
  id: string;
  tenantId: string;
  evidenceId: string;
  actor: string;
  action: CustodyAction;
  evidenceSha256: string;
  createdAt: string;
};

export type AuditEvent = {
  id: string;
  tenantId: string;
  actor: string;
  action: string;
  entityType: "incident" | "assignment" | "evidence" | "custody" | "system";
  entityId: string;
  metadata: Record<string, string | number | boolean | null>;
  createdAt: string;
};

export type RetentionPolicy = {
  id: string;
  tenantId: string;
  name: string;
  retentionDays: number;
  createdAt: string;
};

export type LegalHold = {
  id: string;
  tenantId: string;
  reason: string;
  placedBy: string;
  placedAt: string;
  active: boolean;
};

export type IntegrationConfig = {
  id: string;
  tenantId: string;
  provider: string;
  capability: string;
  enabled: boolean;
  mode: "mock" | "live";
};

export type BackgroundJob = {
  id: string;
  tenantId: string;
  kind: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  error?: string;
};
