// Server-side permission matrix. The UI hides controls a role cannot use, but
// every service function checks this table itself: hiding is not enforcement.

export const ROLES = ["ADMINISTRATOR", "ANALYST", "REVIEWER", "READ_ONLY"] as const;
export type RoleName = (typeof ROLES)[number];

export const PERMISSIONS = [
  "workspace:view",
  "evidence:view-restricted",
  "evidence:create",
  "evidence:verify",
  "import:run",
  "investigation:create",
  "investigation:note",
  "investigation:decide",
  "alert:triage",
  "alert:decide",
  "rule:propose",
  "rule:approve",
  "rule:evaluate",
  "entity:propose",
  "entity:review",
  "export:redacted",
  "export:unredacted",
  "audit:view",
] as const;
export type Permission = (typeof PERMISSIONS)[number];

const MATRIX: Record<RoleName, ReadonlySet<Permission>> = {
  READ_ONLY: new Set(["workspace:view"]),
  ANALYST: new Set([
    "workspace:view",
    "evidence:view-restricted",
    "evidence:create",
    "import:run",
    "investigation:create",
    "investigation:note",
    "alert:triage",
    "rule:propose",
    "rule:evaluate",
    "entity:propose",
    "export:redacted",
  ]),
  REVIEWER: new Set([
    "workspace:view",
    "evidence:view-restricted",
    "evidence:verify",
    "investigation:note",
    "investigation:decide",
    "alert:triage",
    "alert:decide",
    "rule:approve",
    "entity:review",
    "export:redacted",
    "audit:view",
  ]),
  ADMINISTRATOR: new Set(PERMISSIONS),
};

export function can(role: RoleName, permission: Permission): boolean {
  return MATRIX[role].has(permission);
}

export function permissionsFor(role: RoleName): Permission[] {
  return PERMISSIONS.filter((p) => MATRIX[role].has(p));
}

/** Classifications a role may read the excerpt of. Metadata stays visible. */
export function canReadClassification(role: RoleName, classification: string): boolean {
  if (classification === "PUBLIC" || classification === "INTERNAL") return true;
  return can(role, "evidence:view-restricted");
}
