// POST /api/auth/login — exchange an operator password for a session cookie.
//
// The password is checked against ADMIN_DASHBOARD_PASSWORD (env). On success we
// mint a signed session (lib/auth) and set it as an httpOnly, Secure, SameSite
// cookie the browser cannot read from JavaScript — so an XSS bug can't exfil it.
//
// Fail-closed: in production with no strong AUTH_SECRET or no configured
// password, we refuse to authenticate anyone rather than hand out sessions
// signed by the insecure dev default. This mirrors the control plane, which
// fails closed at startup when APP_ENV=production and ADMIN_API_KEY is unset.
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { SESSION_COOKIE, SESSION_TTL_SECONDS, createSession, hasStrongSecret } from "@/lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const isProd = process.env.APP_ENV === "production" || process.env.NODE_ENV === "production";

function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i++) mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return mismatch === 0;
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const expected = process.env.ADMIN_DASHBOARD_PASSWORD;

  // Refuse to run insecurely in production.
  if (isProd && (!expected || !hasStrongSecret())) {
    return NextResponse.json(
      { error: "auth not configured" },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }
  // In dev with nothing configured, accept the well-known dev password so the
  // cockpit is usable locally without setup.
  const devPassword = "dev";
  const effectiveExpected = expected || (isProd ? undefined : devPassword);
  if (!effectiveExpected) {
    return NextResponse.json({ error: "auth not configured" }, { status: 503 });
  }

  // Accept JSON or form posts (the login page uses a plain <form>, no JS needed).
  // Both `password` and `next` are assigned in every branch below before use.
  let password: string;
  let next: string;
  const contentType = req.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    const body = (await req.json().catch(() => ({}))) as { password?: string; next?: string };
    password = body.password ?? "";
    next = sanitizeNext(body.next);
  } else {
    const form = await req.formData();
    password = String(form.get("password") ?? "");
    next = sanitizeNext(form.get("next"));
  }

  if (!safeEqual(password, effectiveExpected)) {
    // Redirect back to login with an error flag for the no-JS form flow; JSON
    // clients get a 401.
    if (contentType.includes("application/json")) {
      return NextResponse.json({ error: "invalid credentials" }, { status: 401 });
    }
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    url.searchParams.set("error", "1");
    if (next && next !== "/") url.searchParams.set("next", next);
    return NextResponse.redirect(url, { status: 303 });
  }

  const token = await createSession("admin", SESSION_TTL_SECONDS);
  const res =
    contentType.includes("application/json")
      ? NextResponse.json({ ok: true, next })
      : NextResponse.redirect(new URL(next, req.nextUrl.origin), { status: 303 });

  res.cookies.set(SESSION_COOKIE, token, {
    httpOnly: true,
    secure: isProd,
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
  });
  res.headers.set("Cache-Control", "no-store");
  return res;
}

// Only allow same-origin relative redirects to prevent open-redirect abuse.
function sanitizeNext(value: unknown): string {
  const s = typeof value === "string" ? value : "";
  if (s.startsWith("/") && !s.startsWith("//")) return s;
  return "/";
}
