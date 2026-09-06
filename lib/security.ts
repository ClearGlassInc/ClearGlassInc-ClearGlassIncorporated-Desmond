import type { DataClassification, LiveEvent, StreamName } from "./contracts";
import { fabricConfig } from "./config";

export type Principal = { subject: string; role: "anonymous" | "user" | "member" | "workspace_admin" | "billing_admin" | "platform_admin" | "operator"; tenantId?: string };
const rank: Record<DataClassification, number> = { PUBLIC: 0, AUTHENTICATED: 1, WORKSPACE: 2, ADMIN: 3, INTERNAL: 4, SECRET: 5 };
const clearance: Record<Principal["role"], number> = { anonymous: 0, user: 1, member: 2, workspace_admin: 3, billing_admin: 3, platform_admin: 4, operator: 4 };

export function canRead(principal: Principal, classification: DataClassification, tenantId?: string): boolean {
  if (classification === "SECRET" || clearance[principal.role] < rank[classification]) return false;
  return !tenantId || (!!principal.tenantId && principal.tenantId === tenantId);
}
export function authorizeStream(principal: Principal, stream: StreamName, requestedTenant?: string): boolean {
  if (stream !== "dashboard") return principal.role === "anonymous" || clearance[principal.role] >= 0;
  return principal.role !== "anonymous" && !!requestedTenant && principal.tenantId === requestedTenant && clearance[principal.role] >= 2;
}
export function validateOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  return !origin || fabricConfig.allowedOrigins.has(origin);
}
export function redactForLog(event: LiveEvent): Record<string, unknown> {
  return { id: event.id, type: event.type, version: event.version, source: event.source, environment: event.environment, visibility: event.visibility, correlationId: event.correlationId, sequence: event.sequence, occurredAt: event.occurredAt, publishedAt: event.publishedAt, payload: "[REDACTED]" };
}
