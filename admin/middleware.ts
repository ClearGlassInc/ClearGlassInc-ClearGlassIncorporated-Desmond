import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE } from "@/lib/constants";

const PROTECTED_PREFIXES = ["/", "/approvals", "/audit", "/premium", "/api/premium", "/api/assets"];
const PUBLIC_PREFIXES = ["/login", "/api/login", "/_next", "/favicon.ico"];
const WINDOW_MS = 60_000;
const BURST_THRESHOLD = Number(process.env.ROUTE_BURST_THRESHOLD || 60);
const burstBuckets = new Map<string, number[]>();

function isProtected(pathname: string): boolean {
  if (PUBLIC_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`))) return false;
  return PROTECTED_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

async function hmac(value: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(process.env.REQUEST_FINGERPRINT_SECRET || "dev-only-fingerprint-secret"),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value));
  return Buffer.from(signature).toString("base64url");
}

function burstCount(fingerprint: string): number {
  const now = Date.now();
  const hits = (burstBuckets.get(fingerprint) || []).filter((hit) => now - hit <= WINDOW_MS);
  hits.push(now);
  burstBuckets.set(fingerprint, hits);
  return hits.length;
}

export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const fingerprint = await hmac([
    request.headers.get("x-forwarded-for") || "unknown-ip",
    request.headers.get("user-agent") || "unknown-agent",
  ].join("|"));
  const count = burstCount(fingerprint);

  console.info(JSON.stringify({
    severity: count > BURST_THRESHOLD ? "warn" : "info",
    event: "route_request",
    at: new Date().toISOString(),
    fingerprint,
    referrer: request.headers.get("referer") || "direct",
    path: pathname,
    method: request.method,
    burstCount: count,
  }));

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-request-fingerprint", fingerprint);
  requestHeaders.set("x-pathname", pathname);

  if (isProtected(pathname) && !request.cookies.get(SESSION_COOKIE)?.value) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", pathname);
    return NextResponse.redirect(login, { headers: requestHeaders });
  }

  return NextResponse.next({ request: { headers: requestHeaders } });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
