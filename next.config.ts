import type { NextConfig } from "next";

const securityHeaders = [
  /* script-src previously read `'self'` with no nonce and no 'unsafe-inline'.
     The App Router injects inline bootstrap scripts for hydration, so every
     one was refused ("Refused to execute inline script...") and React never
     hydrated — no client component in this app could run at all. Verified in
     Chromium: 0 of the shell components mounted and data-cgm-motion was null.

     'unsafe-inline' restores hydration and matches the posture the deployed
     static site already ships in `_headers`. The stricter alternative is a
     per-request nonce with 'strict-dynamic' set from middleware, but Next can
     only stamp a nonce onto dynamically rendered responses — these routes are
     statically prerendered, so adopting it means opting them into dynamic
     rendering. That is a rendering-strategy decision, not a config tweak, so
     it is left to the owner rather than made here. */
  { key: "Content-Security-Policy", value: "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; upgrade-insecure-requests" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains; preload" }
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  async headers() { return [{ source: "/:path*", headers: securityHeaders }]; }
};

export default nextConfig;
