// Runtime configuration, validated once. Anything unsafe fails closed.

export type AppEnv = "local" | "test" | "production";

export interface AppConfig {
  appEnv: AppEnv;
  demoAuthEnabled: boolean;
  sessionSecret: string | null;
  importMaxBytes: number;
  importMaxRows: number;
}

export class ConfigError extends Error {}

export function loadConfig(env: Record<string, string | undefined> = process.env): AppConfig {
  // Unset means production: demo access must be switched on deliberately.
  const rawEnv = env.APP_ENV ?? "production";
  if (rawEnv !== "local" && rawEnv !== "test" && rawEnv !== "production") {
    throw new ConfigError(`APP_ENV must be local, test or production (got "${rawEnv}")`);
  }
  const appEnv: AppEnv = rawEnv;
  const demoRequested = env.DEMO_AUTH_ENABLED === "true";
  if (demoRequested && appEnv === "production") {
    throw new ConfigError("DEMO_AUTH_ENABLED=true is refused when APP_ENV is production (or unset)");
  }
  const secret = env.SESSION_SECRET ?? null;
  if (demoRequested && (!secret || secret.length < 32)) {
    throw new ConfigError("Demo authentication needs SESSION_SECRET of at least 32 characters");
  }
  const importMaxBytes = Number(env.IMPORT_MAX_BYTES ?? 524_288);
  const importMaxRows = Number(env.IMPORT_MAX_ROWS ?? 5_000);
  if (!Number.isInteger(importMaxBytes) || importMaxBytes < 1 || importMaxBytes > 5_242_880) {
    throw new ConfigError("IMPORT_MAX_BYTES must be an integer between 1 and 5242880");
  }
  if (!Number.isInteger(importMaxRows) || importMaxRows < 1 || importMaxRows > 50_000) {
    throw new ConfigError("IMPORT_MAX_ROWS must be an integer between 1 and 50000");
  }
  return { appEnv, demoAuthEnabled: demoRequested, sessionSecret: secret, importMaxBytes, importMaxRows };
}

let cached: AppConfig | null = null;
export function config(): AppConfig {
  cached ??= loadConfig();
  return cached;
}
