import { z } from "zod";

export const EvidenceRecord = z.object({
  id: z.string().min(1),
  source: z.enum(["camera_a", "camera_b", "document", "sensor", "analyst"]),
  capturedAt: z.string().datetime(),
  sha256: z.string().regex(/^[a-f0-9]{64}$/),
  metadata: z.record(z.string()),
  independent: z.boolean().default(false),
});

export const ForensicCase = z.object({
  caseId: z.string().min(3).max(128),
  claim: z.string().min(1).max(4000),
  evidence: z.array(EvidenceRecord).min(1),
  humanGateRequired: z.boolean().default(true),
});

export type Evidence = z.infer<typeof EvidenceRecord>;
export type Case = z.infer<typeof ForensicCase>;

export type IntegrityResult = {
  score: number;
  status: "verified" | "review" | "insufficient";
  reasons: string[];
};

/** Deterministic consistency checks; never alters source evidence. */
export function assessIntegrity(input: Case): IntegrityResult {
  const reasons: string[] = [];
  const sources = new Set(input.evidence.map((e) => e.source));
  let score = 50;

  if (sources.has("camera_a")) score += 15;
  if (sources.has("camera_b")) score += 15;
  if (sources.has("camera_a") && sources.has("camera_b")) score += 10;
  if (input.evidence.every((e) => e.sha256.length === 64)) score += 5;
  if (input.evidence.some((e) => e.independent)) score += 5;

  if (!sources.has("camera_a") || !sources.has("camera_b")) {
    reasons.push("Independent dual-channel capture is incomplete.");
  }
  if (!input.evidence.some((e) => e.independent)) {
    reasons.push("No independently attested evidence source is present.");
  }
  if (input.humanGateRequired) reasons.push("Human authorization remains required for material conclusions.");

  const bounded = Math.min(100, Math.max(0, score));
  return {
    score: bounded,
    status: bounded >= 85 && reasons.length <= 1 ? "verified" : bounded >= 60 ? "review" : "insufficient",
    reasons,
  };
}
