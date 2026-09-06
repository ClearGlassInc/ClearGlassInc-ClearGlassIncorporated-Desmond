import { cookies } from "next/headers";
import { createHmac, timingSafeEqual } from "node:crypto";

export const SESSION_COOKIE = "cg_session";
export const AUTH_SECRET_ENV = "PREMIUM_AUTH_SECRET";

type PremiumSession = {
  sub: string;
  plan: "premium" | "operator";
  exp: number;
};

function secret(): string {
  const value = process.env[AUTH_SECRET_ENV];
  if (!value && process.env.NODE_ENV === "production") {
    throw new Error(`${AUTH_SECRET_ENV} must be set in production`);
  }
  return value || "dev-only-premium-auth-secret-change-me";
}

function base64url(input: string): string {
  return Buffer.from(input).toString("base64url");
}

function sign(payload: string): string {
  return createHmac("sha256", secret()).update(payload).digest("base64url");
}

export function createPremiumSession(session: PremiumSession): string {
  const payload = base64url(JSON.stringify(session));
  return `${payload}.${sign(payload)}`;
}

export function verifyPremiumSession(token?: string): PremiumSession | null {
  if (!token) return null;
  const [payload, signature] = token.split(".");
  if (!payload || !signature) return null;

  const expected = sign(payload);
  const supplied = Buffer.from(signature);
  const expectedBuffer = Buffer.from(expected);
  if (supplied.length !== expectedBuffer.length) return null;
  if (!timingSafeEqual(supplied, expectedBuffer)) return null;

  try {
    const session = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as PremiumSession;
    if (!session.sub || !session.plan || session.exp < Math.floor(Date.now() / 1000)) return null;
    return session.plan === "premium" || session.plan === "operator" ? session : null;
  } catch {
    return null;
  }
}

export async function getServerPremiumSession(): Promise<PremiumSession | null> {
  return verifyPremiumSession((await cookies()).get(SESSION_COOKIE)?.value);
}

export async function requirePremiumSession(): Promise<PremiumSession> {
  const session = await getServerPremiumSession();
  if (!session) {
    throw new Error("Premium authentication required");
  }
  return session;
}
