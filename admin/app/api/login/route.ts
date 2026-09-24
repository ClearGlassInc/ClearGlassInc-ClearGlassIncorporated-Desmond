// POST /api/login — the form on /login posts an access token here.
//
// Fails closed: in production with no ADMIN_LOGIN_TOKEN / ADMIN_API_KEY, or no
// strong session secret, nobody is let in. The dev token applies only outside
// production. Comparison is constant-time, repeated failures lock out (see
// lib/login-guard.ts), and `next` can only name a path on this origin.
import { cookies, headers } from "next/headers";
import { NextResponse } from "next/server";
import { hasStrongSecret, issueSession, SESSION_COOKIE } from "@/lib/auth";
import { constantTimeEqual, loginThrottle, safeNextPath } from "@/lib/login-guard";
import { recordSecurityEvent } from "@/lib/security-events";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const isProd = process.env.APP_ENV === "production" || process.env.NODE_ENV === "production";
const NO_STORE = { "Cache-Control": "no-store" };

function expectedToken(): string | undefined {
  const configured = process.env.ADMIN_LOGIN_TOKEN || process.env.ADMIN_API_KEY;
  if (configured) return configured;
  return isProd ? undefined : "dev-admin-token";
}

export async function POST(request: Request) {
  const h = await headers();
  const fingerprint = h.get("x-request-fingerprint") || "unknown";
  const audit = { fingerprint, referrer: h.get("referer") || "direct", path: "/api/login", method: "POST" };

  const expected = expectedToken();
  if (!expected || (isProd && !hasStrongSecret())) {
    recordSecurityEvent({ event: "login_unavailable", reason: "auth_not_configured", ...audit });
    return NextResponse.json({ error: "auth not configured" }, { status: 503, headers: NO_STORE });
  }

  if (loginThrottle.isLocked(fingerprint)) {
    recordSecurityEvent({ event: "login_locked", reason: "too_many_failures", ...audit });
    // This route serves a plain HTML form, so answer with the login page and a
    // message rather than a JSON 429 the browser would print raw.
    const locked = new URL("/login", request.url);
    locked.searchParams.set("error", "locked");
    return NextResponse.redirect(locked, {
      status: 303,
      headers: { ...NO_STORE, "Retry-After": String(loginThrottle.retryAfterSeconds(fingerprint)) },
    });
  }

  const form = await request.formData();
  const token = String(form.get("token") || "");
  const next = safeNextPath(form.get("next"));

  if (!constantTimeEqual(token, expected)) {
    loginThrottle.recordFailure(fingerprint);
    recordSecurityEvent({ event: "login_denied", reason: "bad_token", ...audit });
    const back = new URL("/login", request.url);
    back.searchParams.set("error", "1");
    if (next !== "/") back.searchParams.set("next", next);
    // 303, not the default 307: a 307 makes the browser re-POST the form,
    // token included, to the redirect target.
    return NextResponse.redirect(back, { status: 303, headers: NO_STORE });
  }

  loginThrottle.reset(fingerprint);
  (await cookies()).set(SESSION_COOKIE, issueSession("admin"), {
    httpOnly: true,
    sameSite: "lax",
    secure: isProd,
    path: "/",
    maxAge: Number(process.env.ADMIN_SESSION_TTL_SECONDS || 60 * 60 * 8),
  });
  recordSecurityEvent({ event: "login_accepted", ...audit });
  return NextResponse.redirect(new URL(next, request.url), { status: 303, headers: NO_STORE });
}
