import { z } from "zod";

export const streamNames = ["public", "status", "performance", "content", "dashboard"] as const;
export type StreamName = (typeof streamNames)[number];
export type ConnectionState = "CONNECTING" | "LIVE" | "DEGRADED" | "STALE" | "OFFLINE" | "ERROR" | "DISABLED";
export type DataClassification = "PUBLIC" | "AUTHENTICATED" | "WORKSPACE" | "ADMIN" | "INTERNAL" | "SECRET";

export const freshnessSchema = z.object({
  state: z.enum(["live", "recent", "cached", "stale", "estimated", "unavailable"]),
  measuredAt: z.string().datetime().optional(), receivedAt: z.string().datetime().optional(),
  expiresAt: z.string().datetime().optional(), source: z.string().max(100).optional()
}).strict();
export type DataFreshness = z.infer<typeof freshnessSchema>;

const environmentSchema = z.enum(["development", "staging", "production"]);
const visibilitySchema = z.enum(["public", "authenticated", "internal"]);
export const liveEventSchema = z.object({
  id: z.string().min(1).max(128).regex(/^[A-Za-z0-9._:-]+$/),
  type: z.string().min(1).max(128).regex(/^[a-z][a-z0-9]*(?:\.[a-z0-9]+)+$/),
  version: z.number().int().positive().max(100),
  occurredAt: z.string().datetime(), publishedAt: z.string().datetime(),
  source: z.string().min(1).max(100), environment: environmentSchema,
  visibility: visibilitySchema, tenantId: z.string().min(1).max(128).optional(),
  correlationId: z.string().min(1).max(128), sequence: z.number().int().nonnegative(),
  payload: z.record(z.unknown())
}).strict().superRefine((event, context) => {
  if (Date.parse(event.occurredAt) > Date.parse(event.publishedAt)) context.addIssue({ code: z.ZodIssueCode.custom, message: "occurredAt must not follow publishedAt", path: ["occurredAt"] });
  if (event.visibility === "public" && event.tenantId) context.addIssue({ code: z.ZodIssueCode.custom, message: "public events cannot be tenant-scoped", path: ["tenantId"] });
});
export type LiveEvent = z.infer<typeof liveEventSchema>;

export const signalSchema = z.object({
  key: z.string().min(1).max(80), label: z.string().min(1).max(120),
  value: z.string().max(160), status: z.enum(["healthy", "degraded", "incident", "unavailable"]),
  classification: z.enum(["PUBLIC", "AUTHENTICATED", "WORKSPACE", "ADMIN", "INTERNAL", "SECRET"]),
  freshness: freshnessSchema
}).strict();
export type Signal = z.infer<typeof signalSchema>;

export const snapshotSchema = z.object({
  stream: z.enum(streamNames), generatedAt: z.string().datetime(), sequence: z.number().int().nonnegative(),
  signals: z.array(signalSchema).max(100), sourceConfigured: z.boolean()
}).strict();
export type Snapshot = z.infer<typeof snapshotSchema>;
