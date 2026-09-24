// Run: node --experimental-strip-types --test admin/tests/login-guard.test.mjs
// (tests/test_admin_login_guard.py runs this inside the root pytest gate.)
import assert from "node:assert/strict";
import test from "node:test";

import { LoginThrottle, constantTimeEqual, safeNextPath } from "../lib/login-guard.ts";
import { isProtected } from "../lib/route-policy.ts";

const ORIGIN = "https://admin.example";

test("next may only name a path on this origin", () => {
  const offSite = [
    "//evil.example",
    "/\\evil.example",
    "/\t/evil.example",
    "/\n/evil.example",
    "\\\\evil.example",
    "https://evil.example/",
    "javascript:alert(1)",
    "",
    undefined,
    null,
    42,
  ];
  for (const value of offSite) {
    const next = safeNextPath(value);
    assert.equal(next, "/", `${JSON.stringify(value)} must fall back to /`);
  }
  // Whatever comes back must resolve on the admin origin.
  for (const value of offSite) {
    assert.equal(new URL(safeNextPath(value), ORIGIN).origin, ORIGIN);
  }
});

test("a same-origin path survives with its query and fragment", () => {
  assert.equal(safeNextPath("/approvals"), "/approvals");
  assert.equal(safeNextPath("/revenue?stage=QUALIFIED#leads"), "/revenue?stage=QUALIFIED#leads");
  assert.equal(safeNextPath("/%2F%2Fevil.example"), "/%2F%2Fevil.example");
  assert.equal(new URL(safeNextPath("/%2F%2Fevil.example"), ORIGIN).origin, ORIGIN);
});

test("token comparison matches only the exact token", () => {
  assert.equal(constantTimeEqual("correct-horse-battery", "correct-horse-battery"), true);
  assert.equal(constantTimeEqual("correct-horse-batterx", "correct-horse-battery"), false);
  assert.equal(constantTimeEqual("", "correct-horse-battery"), false);
  assert.equal(constantTimeEqual("correct-horse-battery-and-more", "correct-horse-battery"), false);
});

test("the sixth failure inside the window is refused, then the lock expires", () => {
  const throttle = new LoginThrottle(5, 50, 15 * 60_000);
  const t0 = 1_000_000;
  for (let i = 0; i < 5; i++) {
    assert.equal(throttle.isLocked("client-a", t0 + i), false, `attempt ${i + 1} must be allowed`);
    throttle.recordFailure("client-a", t0 + i);
  }
  assert.equal(throttle.isLocked("client-a", t0 + 10), true);
  assert.ok(throttle.retryAfterSeconds("client-a", t0 + 10) > 0);
  // Another client is not affected by client-a's failures.
  assert.equal(throttle.isLocked("client-b", t0 + 10), false);
  // Once the first failure leaves the window, one more attempt is allowed.
  assert.equal(throttle.isLocked("client-a", t0 + 15 * 60_000), false);
});

test("a success clears that client's count", () => {
  const throttle = new LoginThrottle(5, 50, 60_000);
  for (let i = 0; i < 4; i++) throttle.recordFailure("client-a", i);
  throttle.reset("client-a");
  for (let i = 0; i < 4; i++) throttle.recordFailure("client-a", 10 + i);
  assert.equal(throttle.isLocked("client-a", 20), false);
});

test("rotating the client key does not escape the global ceiling", () => {
  const throttle = new LoginThrottle(5, 50, 60_000);
  for (let i = 0; i < 50; i++) throttle.recordFailure(`spoofed-${i}`, i);
  assert.equal(throttle.isLocked("fresh-client", 100), true);
  assert.equal(throttle.isLocked("fresh-client", 60_000 + 100), false);
});

test("admin pages need a session unless explicitly public", () => {
  for (const path of ["/", "/revenue", "/playbooks", "/approvals", "/audit", "/premium", "/api/premium", "/some-new-page"]) {
    assert.equal(isProtected(path), true, `${path} must require a session`);
  }
  for (const path of ["/login", "/api/login", "/api/auth/login", "/healthz", "/_next/static/chunk.js"]) {
    assert.equal(isProtected(path), false, `${path} must stay reachable without a session`);
  }
  // A public prefix must not open look-alike paths.
  assert.equal(isProtected("/login-admin"), true);
  assert.equal(isProtected("/healthzz"), true);
});
