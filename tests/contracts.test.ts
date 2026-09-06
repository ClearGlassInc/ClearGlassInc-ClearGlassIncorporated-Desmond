import assert from "node:assert/strict";
import test from "node:test";
import { EventGuard } from "../lib/events";
import { canRead, authorizeStream, redactForLog } from "../lib/security";

const base = { id: "evt-1", type: "status.updated", version: 1, occurredAt: "2026-08-08T15:00:00.000Z", publishedAt: "2026-08-08T15:00:01.000Z", source: "development-disabled-source", environment: "development" as const, visibility: "public" as const, correlationId: "corr-1", sequence: 1, payload: { status: "healthy", secret: "must-not-log" } };

test("accepts a valid event and rejects duplicate/replayed events", () => { const guard = new EventGuard(); assert.equal(guard.validate(base).id, "evt-1"); assert.throws(() => guard.validate(base), /duplicate/); assert.throws(() => guard.validate({ ...base, id: "evt-2", sequence: 0 }), /replayed|out-of-order/); });
test("rejects unknown sources, malformed timestamps, and public tenant data", () => { assert.throws(() => new EventGuard().validate({ ...base, source: "unknown" }), /unknown/); assert.throws(() => new EventGuard().validate({ ...base, occurredAt: "today" })); assert.throws(() => new EventGuard().validate({ ...base, tenantId: "workspace-a" })); });
test("redacts all payload contents from structured logs", () => { const event = new EventGuard().validate(base); const log = redactForLog(event); assert.equal(log.payload, "[REDACTED]"); assert.doesNotMatch(JSON.stringify(log), /must-not-log/); });
test("enforces classification and tenant isolation", () => { const member = { subject: "user-1", role: "member" as const, tenantId: "workspace-a" }; assert.equal(canRead(member, "WORKSPACE", "workspace-a"), true); assert.equal(canRead(member, "WORKSPACE", "workspace-b"), false); assert.equal(canRead(member, "SECRET", "workspace-a"), false); assert.equal(authorizeStream(member, "dashboard", "workspace-a"), true); assert.equal(authorizeStream(member, "dashboard", "workspace-b"), false); assert.equal(authorizeStream({ subject: "anon", role: "anonymous" }, "dashboard", "workspace-a"), false); });
