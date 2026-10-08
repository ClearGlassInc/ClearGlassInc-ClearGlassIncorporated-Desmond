// DEMO AUTHENTICATION - LOCAL DEVELOPMENT ONLY.
//
// Signs a user id into an HMAC cookie. There is no password: anyone who can
// reach the app can pick a demo user. loadConfig() refuses to enable it when
// APP_ENV is production or unset, and it only resolves users flagged isDemo.

import { createHmac, timingSafeEqual } from "node:crypto";
import type { Db } from "../db";
import type { Actor, AuthProvider } from "./actor";
import type { RoleName } from "./roles";

export const DEMO_COOKIE = "cg_osint_demo_session";
const TTL_SECONDS = 8 * 60 * 60;

function sign(secret: string, payload: string): string {
  return createHmac("sha256", secret).update(payload).digest("base64url");
}

export function issueDemoToken(secret: string, userId: string, now = Date.now()): string {
  const payload = `${userId}.${Math.floor(now / 1000) + TTL_SECONDS}`;
  return `${payload}.${sign(secret, payload)}`;
}

export function verifyDemoToken(secret: string, token: string, now = Date.now()): string | null {
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [userId, exp, mac] = parts;
  const expected = Buffer.from(sign(secret, `${userId}.${exp}`));
  const given = Buffer.from(mac);
  if (expected.length !== given.length || !timingSafeEqual(expected, given)) return null;
  if (!/^\d+$/.test(exp) || Number(exp) * 1000 < now) return null;
  return userId;
}

export const DEMO_TTL_SECONDS = TTL_SECONDS;

export class DemoAuthProvider implements AuthProvider {
  readonly name = "demo";
  readonly isDemo = true;
  constructor(
    private readonly db: Db,
    private readonly secret: string,
  ) {}

  async resolve(cookie: (name: string) => string | undefined): Promise<Actor | null> {
    const token = cookie(DEMO_COOKIE);
    if (!token) return null;
    const userId = verifyDemoToken(this.secret, token);
    if (!userId) return null;
    const user = await this.db.user.findFirst({ where: { id: userId, isDemo: true } });
    if (!user) return null;
    return { id: user.id, email: user.email, name: user.name, role: user.role as RoleName, isDemo: true };
  }
}

/** Used when no provider is configured: nobody is signed in, every protected action is denied. */
export class UnconfiguredAuthProvider implements AuthProvider {
  readonly name = "none";
  readonly isDemo = false;
  async resolve(): Promise<Actor | null> {
    return null;
  }
}
