import { cookies, headers } from "next/headers";
import { NextResponse } from "next/server";
import { issueSession, SESSION_COOKIE } from "@/lib/auth";
import { recordSecurityEvent } from "@/lib/security-events";

export async function POST(request: Request) {
  const form = await request.formData();
  const token = String(form.get("token") || "");
  const next = String(form.get("next") || "/");
  const expected = process.env.ADMIN_LOGIN_TOKEN || process.env.ADMIN_API_KEY || "dev-admin-token";
  const h = await headers();

  if (token !== expected) {
    recordSecurityEvent({ event: "login_denied", fingerprint: h.get("x-request-fingerprint") || "unknown", referrer: h.get("referer") || "direct", path: "/api/login", method: "POST", reason: "bad_token" });
    return NextResponse.redirect(new URL("/login", request.url));
  }

  (await cookies()).set(SESSION_COOKIE, issueSession("admin"), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: Number(process.env.ADMIN_SESSION_TTL_SECONDS || 60 * 60 * 8),
  });
  recordSecurityEvent({ event: "login_accepted", fingerprint: h.get("x-request-fingerprint") || "unknown", referrer: h.get("referer") || "direct", path: "/api/login", method: "POST" });
  return NextResponse.redirect(new URL(next.startsWith("/") ? next : "/", request.url));
}
