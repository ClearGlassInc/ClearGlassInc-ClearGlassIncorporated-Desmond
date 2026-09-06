const allowedEnvironments = new Set(["development", "test", "production"]);
const nodeEnvironment = process.env.NODE_ENV ?? "development";
if (!allowedEnvironments.has(nodeEnvironment)) throw new Error("Invalid NODE_ENV");
function optionalPrefixed(name: string, prefix: string): string | undefined {
  const value = process.env[name];
  if (value && !value.startsWith(prefix)) throw new Error(`${name} has an invalid format`);
  return value;
}
export const env = {
  NODE_ENV: nodeEnvironment,
  DATABASE_URL: process.env.DATABASE_URL,
  STRIPE_SECRET_KEY: optionalPrefixed("STRIPE_SECRET_KEY", "sk_"),
  STRIPE_WEBHOOK_SECRET: optionalPrefixed("STRIPE_WEBHOOK_SECRET", "whsec_"),
  COMMERCE_APPROVED: process.env.COMMERCE_APPROVED === "true" ? "true" : undefined,
} as const;
