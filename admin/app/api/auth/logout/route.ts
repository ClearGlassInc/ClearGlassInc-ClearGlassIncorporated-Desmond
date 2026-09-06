// POST /api/auth/logout — clear the session cookie and return to /login.
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { SESSION_COOKIE } from "@/lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: NextRequest): Promise<NextResponse> {
  const res = NextResponse.redirect(new URL("/login", req.nextUrl.origin), { status: 303 });
  // Expire the cookie immediately.
  res.cookies.set(SESSION_COOKIE, "", {
    httpOnly: true,
    secure: process.env.APP_ENV === "production" || process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
  res.headers.set("Cache-Control", "no-store");
  return res;
}
