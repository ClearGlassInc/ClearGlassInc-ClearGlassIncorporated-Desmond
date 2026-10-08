import { describe, expect, it } from "vitest";
import { can, canReadClassification, permissionsFor } from "@/lib/auth/roles";
import { issueDemoToken, verifyDemoToken } from "@/lib/auth/demo";
import { loadConfig } from "@/lib/config";
import { assertOutboundAllowed, manualUrlAdapter, mockRegistryAdapter, ADAPTERS } from "@/lib/osint/adapters";
import { redactExport, redactText, type InvestigationExport } from "@/lib/export/redact";
import { cleanText, safeHref } from "@/lib/text";
import { transitionLevel } from "@/lib/review";

const SECRET = "x".repeat(40);

describe("role matrix", () => {
  it("read-only can view and nothing else", () => {
    expect(permissionsFor("READ_ONLY")).toEqual(["workspace:view"]);
  });
  it("analysts propose but cannot approve; reviewers approve but cannot import", () => {
    expect(can("ANALYST", "rule:propose")).toBe(true);
    expect(can("ANALYST", "rule:approve")).toBe(false);
    expect(can("REVIEWER", "rule:approve")).toBe(true);
    expect(can("REVIEWER", "import:run")).toBe(false);
    expect(can("ANALYST", "export:unredacted")).toBe(false);
    expect(can("ADMINISTRATOR", "export:unredacted")).toBe(true);
  });
  it("hides restricted excerpts from read-only users", () => {
    expect(canReadClassification("READ_ONLY", "PUBLIC")).toBe(true);
    expect(canReadClassification("READ_ONLY", "RESTRICTED")).toBe(false);
    expect(canReadClassification("ANALYST", "RESTRICTED")).toBe(true);
  });
  it("analysts cannot make reviewer-level case decisions", () => {
    expect(transitionLevel("UNDER_REVIEW", "ESCALATED_FOR_REVIEW")).toBe("triage");
    expect(transitionLevel("UNDER_REVIEW", "CLOSED")).toBe("decide");
    expect(transitionLevel("NEW", "CLOSED")).toBeNull();
  });
});

describe("demo authentication", () => {
  it("is off by default and refused in production", () => {
    expect(loadConfig({}).demoAuthEnabled).toBe(false);
    expect(loadConfig({}).appEnv).toBe("production");
    expect(() => loadConfig({ DEMO_AUTH_ENABLED: "true", SESSION_SECRET: SECRET })).toThrow(/refused/);
    expect(() => loadConfig({ APP_ENV: "production", DEMO_AUTH_ENABLED: "true", SESSION_SECRET: SECRET })).toThrow(/refused/);
    expect(() => loadConfig({ APP_ENV: "local", DEMO_AUTH_ENABLED: "true", SESSION_SECRET: "short" })).toThrow(/32 characters/);
    expect(loadConfig({ APP_ENV: "local", DEMO_AUTH_ENABLED: "true", SESSION_SECRET: SECRET }).demoAuthEnabled).toBe(true);
  });
  it("rejects tampered, foreign-key and expired tokens", () => {
    const now = Date.UTC(2026, 9, 8);
    const token = issueDemoToken(SECRET, "user-1", now);
    expect(verifyDemoToken(SECRET, token, now)).toBe("user-1");
    expect(verifyDemoToken(SECRET, token.replace("user-1", "user-2"), now)).toBeNull();
    expect(verifyDemoToken("y".repeat(40), token, now)).toBeNull();
    expect(verifyDemoToken(SECRET, token, now + 9 * 3600 * 1000)).toBeNull();
    expect(verifyDemoToken(SECRET, "garbage", now)).toBeNull();
  });
});

describe("untrusted content", () => {
  it("never produces a link for non-http(s) URLs", () => {
    expect(safeHref("javascript:alert(1)")).toBeNull();
    expect(safeHref("data:text/html,<script>")).toBeNull();
    expect(safeHref("https://user:pw@example.org")).toBeNull();
    expect(safeHref("https://example.org/a?b=1")).toBe("https://example.org/a?b=1");
  });
  it("strips control characters but keeps markup as text", () => {
    expect(cleanText("a\u0000b<script>")).toBe("ab<script>");
  });
});

describe("source adapters and outbound fetching", () => {
  it("no shipped adapter claims to be live", () => {
    expect(Object.values(ADAPTERS).every((a) => a.live === false)).toBe(true);
  });
  it("manual adapter records the URL as a citation and refuses unsafe schemes", () => {
    const now = new Date("2026-10-08T00:00:00Z");
    const [ev] = manualUrlAdapter.collect(
      { url: "https://example.org/notice", title: "Public notice", excerpt: "The notice states the award date.", sourceTitle: "Example Gazette" },
      now,
    );
    expect(ev.url).toBe("https://example.org/notice");
    expect(ev.collectedAt).toEqual(now);
    expect(ev.missing).toEqual(["documentLocation", "publishedAt", "sourcePublisher"]);
    expect(() => manualUrlAdapter.collect({ url: "file:///etc/passwd", title: "x", excerpt: "x".repeat(20), sourceTitle: "s" }, now)).toThrow();
  });
  it("mock adapter only returns synthetic, labelled fixtures", () => {
    const out = mockRegistryAdapter.collect({ query: "paving" }, new Date("2026-10-08T00:00:00Z"));
    expect(out).toHaveLength(1);
    expect(out[0].excerpt).toMatch(/^SYNTHETIC REGISTRY ENTRY/);
  });
  it("outbound guard refuses everything unless explicitly allowlisted", () => {
    const allow = ["registry.example.org"];
    expect(() => assertOutboundAllowed("https://registry.example.org/x", [])).toThrow(/allowlist/);
    expect(assertOutboundAllowed("https://registry.example.org/x", allow).hostname).toBe("registry.example.org");
    for (const bad of [
      "http://registry.example.org/x",
      "https://127.0.0.1/",
      "https://2130706433/",
      "https://[::1]/",
      "https://localhost/",
      "https://169.254.169.254/latest/meta-data",
      "https://registry.example.org:8443/",
      "https://u:p@registry.example.org/",
    ]) {
      expect(() => assertOutboundAllowed(bad, [...allow, "localhost", "127.0.0.1"]), bad).toThrow(/refused/);
    }
  });
});

describe("export redaction", () => {
  it("masks emails, phones and account numbers in free text", () => {
    expect(redactText("Contact jane@example.org or 905-555-0199, acct 12345678901")).toBe(
      "Contact [REDACTED EMAIL] or [REDACTED PHONE], acct [REDACTED NUMBER]",
    );
  });

  it("replaces names with roles, removes approvers, withholds restricted excerpts", () => {
    const person = { label: "Avery Analyst", role: "ANALYST" };
    const data: InvestigationExport = {
      exportVersion: 1,
      generatedAt: "2026-10-08T00:00:00.000Z",
      redaction: { mode: "unredacted", applied: [], notice: "" },
      disclaimers: [],
      containsSyntheticData: true,
      investigation: { caseKey: "CG-CASE-0001", title: "t", summary: "email a@b.co", status: "NEW", claimStatus: "ANALYST_INTERPRETATION", owner: person },
      alerts: [],
      notes: [{ kind: "OBSERVATION", body: "Called 416-555-0100", author: person, createdAt: "", evidenceRecordIds: [] }],
      decisions: [{ target: "ALERT:1", from: "NEW", to: "UNDER_REVIEW", rationale: "Reviewed by Avery", decidedBy: person, at: "" }],
      evidence: [
        { recordId: "E1", title: "t", excerpt: "secret detail", url: null, accessClassification: "RESTRICTED", verificationStatus: "UNVERIFIED", contentHash: "h", isSynthetic: true, origin: "SYNTHETIC" },
        { recordId: "E2", title: "t", excerpt: "public detail", url: null, accessClassification: "PUBLIC", verificationStatus: "UNVERIFIED", contentHash: "h", isSynthetic: true, origin: "SYNTHETIC" },
      ],
      transactions: [{ recordId: "T1", type: "PAYMENT", vendorRecordId: "V1", approvedBy: "Pat Approver", description: null }],
    };
    const out = redactExport(data);
    const text = JSON.stringify(out);
    expect(text).not.toContain("Avery Analyst");
    expect(text).not.toContain("Pat Approver");
    expect(text).not.toContain("secret detail");
    expect(text).not.toContain("416-555-0100");
    expect(out.evidence[0].excerpt).toBe("[WITHHELD: RESTRICTED]");
    expect(out.evidence[1].excerpt).toBe("public detail");
    expect(out.investigation.owner).toEqual({ label: "[ANALYST user]", role: "ANALYST" });
    expect(out.redaction.mode).toBe("redacted");
  });
});
