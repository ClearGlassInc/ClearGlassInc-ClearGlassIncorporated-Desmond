import "server-only";

import { createHmac, randomBytes, timingSafeEqual } from "crypto";
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { recordSecurityEvent } from "@/lib/security-events";
import { SESSION_COOKIE } from "@/lib/constants";

export { SESSION_COOKIE };
export const SESSION_TTL_SECONDS = Number(process.env.ADMIN_SESSION_TTL_SECONDS || 60 * 60 * 8);

export interface AdminSession {
  sub: string;
  roles: string[];
  exp: number;
  nonce: string;
}

// The signing key, resolved from (in order) ADMIN_SESSION_SECRET, AUTH_SECRET
// (the name documented in PREMIUM_PROTECTION.md / .env.example), or ADMIN_API_KEY.
function configuredSecret(): string | undefined {
  return (
    process.env.ADMIN_SESSION_SECRET ||
    process.env.AUTH_SECRET ||
    process.env.ADMIN_API_KEY ||
    undefined
  );
}

function secret(): string {
  const value = configuredSecret();
  if (!value && process.env.NODE_ENV === "production") {
    throw new Error("ADMIN_SESSION_SECRET, AUTH_SECRET or ADMIN_API_KEY is required in production");
  }
  return value || "dev-only-admin-session-secret-change-me";
}

// True only when a real, sufficiently long signing secret is configured — i.e.
// we are NOT falling back to the insecure dev default. The hardened login route
// uses this to fail closed in production rather than mint dev-signed sessions.
export function hasStrongSecret(): boolean {
  const value = configuredSecret();
  return typeof value === "string" && value.length >= 16;
}

function b64url(input: Buffer | string): string {
  return Buffer.from(input).toString("base64url");
}

function sign(payload: string): string {
  return createHmac("sha256", secret()).update(payload).digest("base64url");
}

export function issueSession(
  sub: string,
  roles: string[] = ["premium"],
  ttlSeconds: number = SESSION_TTL_SECONDS,
): string {
  const session: AdminSession = {
    sub,
    roles,
    exp: Math.floor(Date.now() / 1000) + ttlSeconds,
    nonce: randomBytes(16).toString("base64url"),
  };
  const payload = b64url(JSON.stringify(session));
  return `${payload}.${sign(payload)}`;
}

// Async alias used by the hardened /api/auth/login flow (kept async so callers
// can `await` it uniformly even if signing later moves to WebCrypto/subtle).
export async function createSession(
  sub: string,
  ttlSeconds: number = SESSION_TTL_SECONDS,
  roles: string[] = ["premium"],
): Promise<string> {
  return issueSession(sub, roles, ttlSeconds);
}

export function verifySessionToken(token: string | undefined): AdminSession | null {
  if (!token) return null;
  const [payload, mac] = token.split(".");
  if (!payload || !mac) return null;
  const expected = sign(payload);
  const macBuffer = Buffer.from(mac);
  const expectedBuffer = Buffer.from(expected);
  const valid = macBuffer.length === expectedBuffer.length && timingSafeEqual(macBuffer, expectedBuffer);
  if (!valid) return null;

  const session = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as AdminSession;
  if (!session.exp || session.exp < Math.floor(Date.now() / 1000)) return null;
  return session;
}

export async function getSession(): Promise<AdminSession | null> {
  return verifySessionToken((await cookies()).get(SESSION_COOKIE)?.value);
}

export async function requirePremiumSession(): Promise<AdminSession> {
  const session = await getSession();
  if (!session || !session.roles.includes("premium")) {
    const h = await headers();
    recordSecurityEvent({
      event: "unauthorized_ssr_access",
      fingerprint: h.get("x-request-fingerprint") || "unknown",
      referrer: h.get("referer") || "direct",
      path: h.get("x-pathname") || "unknown",
      method: "GET",
      reason: session ? "missing_premium_role" : "missing_session",
    });
    redirect("/login");
  }
  return session;
}
