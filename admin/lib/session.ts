import "server-only";

// Server-only session helpers for SSR pages and route handlers — the
// defense-in-depth backstop that re-checks a request AFTER middleware has
// already gated it at the edge (see PREMIUM_PROTECTION.md). Token minting and
// verification live in lib/auth.ts; the cookie name lives in lib/constants.ts so
// the edge middleware can read it without importing this server-only module.
import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { recordSecurityEvent } from "@/lib/security-events";
import { verifySessionToken, type AdminSession } from "@/lib/auth";
import { SESSION_COOKIE } from "@/lib/constants";

export { SESSION_COOKIE };
export type { AdminSession };

// Read and verify the current admin session from the request cookie.
// Returns null when the cookie is absent, tampered, or expired.
export async function getSession(): Promise<AdminSession | null> {
  return verifySessionToken((await cookies()).get(SESSION_COOKIE)?.value);
}

// Require any valid session for an SSR page or route handler. On failure we log
// a structured security event and redirect to /login (preserving `next` so the
// operator lands back where they were after signing in).
export async function requireSession(next = "/"): Promise<AdminSession> {
  const session = await getSession();
  if (!session) {
    const h = await headers();
    recordSecurityEvent({
      event: "unauthorized_ssr_access",
      fingerprint: h.get("x-request-fingerprint") || "unknown",
      referrer: h.get("referer") || "direct",
      path: h.get("x-pathname") || next,
      method: "GET",
      reason: "missing_session",
    });
    const target = next.startsWith("/") && !next.startsWith("//") ? next : "/";
    redirect(`/login?next=${encodeURIComponent(target)}`);
  }
  return session;
}
