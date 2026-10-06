export type OperationsMode = "mock" | "live" | "blocked";

const envBool = (name: string, fallback = false): boolean => {
  const value = process.env[name];
  return value === undefined ? fallback : value === "true";
};

const modeFromEnvironment = (): OperationsMode => {
  const requested = process.env.CLEARGLASS_OPERATIONS_MODE;
  if (requested === "mock" || requested === "live" || requested === "blocked") return requested;
  return process.env.NODE_ENV === "production" ? "blocked" : "mock";
};

export const operationsConfig = {
  enabled:
    process.env.NODE_ENV !== "production"
      ? envBool("CLEARGLASS_OPERATIONS_ENABLED", true)
      : envBool("CLEARGLASS_OPERATIONS_ENABLED", false) &&
        envBool("CLEARGLASS_OPERATIONS_APPROVED", false),
  mode: modeFromEnvironment(),
  maxEvidenceBytes: Number(process.env.CLEARGLASS_OPERATIONS_MAX_EVIDENCE_BYTES ?? 10 * 1024 * 1024),
  features: {
    voice: envBool("CLEARGLASS_OPERATIONS_VOICE_ENABLED"),
    dispatch: envBool("CLEARGLASS_OPERATIONS_DISPATCH_ENABLED"),
    records: envBool("CLEARGLASS_OPERATIONS_RECORDS_ENABLED"),
    evidence: envBool("CLEARGLASS_OPERATIONS_EVIDENCE_ENABLED", true),
    forensicAnalysis: envBool("CLEARGLASS_OPERATIONS_FORENSICS_ENABLED"),
    lpr: envBool("CLEARGLASS_OPERATIONS_LPR_ENABLED"),
    biometricVerification: envBool("CLEARGLASS_OPERATIONS_BIOMETRIC_ENABLED"),
  },
} as const;

export const sensitiveFeatures = [
  "voice",
  "dispatch",
  "forensicAnalysis",
  "lpr",
  "biometricVerification",
] as const;

export type SensitiveFeature = (typeof sensitiveFeatures)[number];
