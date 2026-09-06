import { NextRequest, NextResponse } from "next/server";
const SESSION_COOKIE = "cg_session";

const PROTECTED_PREFIXES = ["/premium", "/api/premium", "/api/assets/sign"];
const burstWindowMs = 60_000;
const burstThreshold = 40;
const bursts = new Map<string, { count: number; resetAt: number }>();

function isProtected(pathname: string) {
  return PROTECTED_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

function decodeBase64Url(value: string) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  return atob(normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "="));
}

async function sha256(input: string) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(input));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

function requestIp(request: NextRequest) {
  return request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || request.headers.get("x-real-ip") || "unknown";
}

async function hasPremiumSession(request: NextRequest) {
  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (!token) return false;
  const [payload, signature] = token.split(".");
  if (!payload || !signature) return false;
  const secret = process.env.PREMIUM_AUTH_SECRET || "dev-only-premium-auth-secret-change-me";
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const expected = Array.from(new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(payload))), (b) =>
    b.toString(16).padStart(2, "0"),
  ).join("");
  const suppliedBytes = Uint8Array.from(decodeBase64Url(signature), (c) => c.charCodeAt(0));
  const supplied = Array.from(suppliedBytes, (b) => b.toString(16).padStart(2, "0")).join("");
  if (expected !== supplied) return false;
  try {
    const session = JSON.parse(decodeBase64Url(payload)) as { plan?: string; exp?: number };
    return Boolean((session.plan === "premium" || session.plan === "operator") && session.exp && session.exp > Date.now() / 1000);
  } catch {
    return false;
  }
}

export async function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (!isProtected(pathname)) return NextResponse.next();

  const fingerprint = await sha256(`${requestIp(request)}:${request.headers.get("user-agent") || "unknown"}`);
  const now = Date.now();
  const current = bursts.get(fingerprint);
  const bucket = current && current.resetAt > now ? { count: current.count + 1, resetAt: current.resetAt } : { count: 1, resetAt: now + burstWindowMs };
  bursts.set(fingerprint, bucket);

  console.info(
    JSON.stringify({
      source: "clearglass-storefront",
      event: bucket.count > burstThreshold ? "protected_route_unusual_burst" : "protected_route_request",
      fingerprint,
      path: pathname,
      referrer: request.headers.get("referer"),
      timestamp: new Date(now).toISOString(),
      burstCount: bucket.count,
    }),
  );

  if (await hasPremiumSession(request)) return NextResponse.next();

  const login = new URL("/login", request.url);
  login.searchParams.set("next", `${pathname}${search}`);
  return NextResponse.redirect(login);
}

export const config = {
  matcher: ["/premium/:path*", "/api/premium/:path*", "/api/assets/sign"],
};
