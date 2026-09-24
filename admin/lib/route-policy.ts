// Which admin paths need a session cookie. Kept free of Next.js imports so the
// edge middleware and `node --test` can both load it.
//
// Default deny. The old allow-list protected "/" as a prefix, but "/" matched
// only the root: a new page such as /revenue or /playbooks shipped reachable
// without a session unless someone remembered to list it. Now every path needs
// a session except the ones named here.
const PUBLIC_PATHS = [
  "/login",
  "/api/login",
  "/api/auth/login",
  "/api/auth/logout",
  "/healthz",
  "/_next",
  "/favicon.ico",
  "/clearglass-seal-192.png",
];

export function isProtected(pathname: string): boolean {
  return !PUBLIC_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
}
