import { readFileSync } from "node:fs";
import { join } from "node:path";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";
import { ForbiddenError, ValidationError } from "@/lib/errors";
import { decideAlert, addNote } from "@/lib/services/cases";
import { createRule, decideVersion, runEvaluation } from "@/lib/services/rules";
import { runImport } from "@/lib/services/imports";
import { exportInvestigation } from "@/lib/services/exports";
import { generateCandidateLinks, reviewRelationship } from "@/lib/services/entities";
import { collectEvidence } from "@/lib/services/evidence";
import { DemoAuthProvider, DEMO_COOKIE, issueDemoToken } from "@/lib/auth/demo";
import type { SeedResult } from "@/lib/seed";
import { alertFor, as, db, resetAndSeed } from "./support";

let seed: SeedResult;
beforeAll(async () => {
  seed = await resetAndSeed();
});
afterAll(() => db.$disconnect());

const file = (name: string) => new Uint8Array(readFileSync(join(process.cwd(), "examples", "imports", name)));
const importReq = (name: string, commit: boolean) => ({
  filename: name,
  bytes: file(name),
  format: "CSV" as const,
  recordType: "TRANSACTION" as const,
  origin: "SYNTHETIC" as const,
  mapping: null,
  limits: { maxBytes: 100_000, maxRows: 1000 },
  commit,
});

describe("server-side authorization", () => {
  it("refuses every write to a read-only user and records the denial", async () => {
    const ro = as(seed, "READ_ONLY");
    const alert = await alertFor("CG-T-001", "MATCH");
    const inv = await db.investigation.findFirstOrThrow();
    const attempts = [
      () => runImport(ro, importReq("duplicate-transactions.csv", true)),
      () => decideAlert(ro, alert.id, "UNDER_REVIEW", "attempting a change"),
      () => runEvaluation(ro),
      () => createRule(ro, { definition: {}, changeSummary: "nope" }),
      () => exportInvestigation(ro, inv.id, "redacted"),
      () => generateCandidateLinks(ro),
      () => addNote(ro, inv.id, { kind: "QUESTION", body: "hello there", evidenceRecordIds: [] }),
    ];
    for (const attempt of attempts) await expect(attempt()).rejects.toThrow(ForbiddenError);
    const denials = await db.auditEvent.count({ where: { actorId: ro.actor.id, action: "security.access_denied", outcome: "denied" } });
    expect(denials).toBe(attempts.length);
  });

  it("separates proposing from approving, even for administrators", async () => {
    const def = JSON.parse(readFileSync(join(process.cwd(), "rules", "templates", "cg-t-003.v1.json"), "utf8"));
    def.ruleKey = "CG-T-903";
    const admin = as(seed, "ADMINISTRATOR");
    const { versionId } = await createRule(admin, { definition: def, changeSummary: "admin proposal" });
    await expect(decideVersion(admin, versionId, "APPROVE", "approving my own proposal")).rejects.toThrow(/Separation of duties/);
    await expect(decideVersion(as(seed, "ANALYST"), versionId, "APPROVE", "analysts cannot approve")).rejects.toThrow(ForbiddenError);
    await decideVersion(as(seed, "REVIEWER"), versionId, "APPROVE", "independent reviewer approves");
    expect((await db.ruleVersion.findUniqueOrThrow({ where: { id: versionId } })).status).toBe("ACTIVE");
  });

  it("keeps reviewer-level decisions away from analysts and requires a rationale", async () => {
    const alert = await alertFor("CG-T-002", "MATCH");
    const analyst = as(seed, "ANALYST");
    await decideAlert(analyst, alert.id, "UNDER_REVIEW", "Looking at both purchase orders.");
    await expect(decideAlert(analyst, alert.id, "CLOSED", "closing it myself")).rejects.toThrow(ForbiddenError);
    await expect(decideAlert(as(seed, "REVIEWER"), alert.id, "CLOSED", "short")).rejects.toThrow(ValidationError);
    await decideAlert(as(seed, "REVIEWER"), alert.id, "EXPLAINED_NO_FURTHER_ACTION", "Two independent departmental requirements.");
    const history = await db.reviewDecision.findMany({ where: { targetType: "ALERT", targetId: alert.id }, orderBy: { createdAt: "asc" } });
    expect(history.map((h) => `${h.fromState}->${h.toState}`)).toEqual(["NEW->UNDER_REVIEW", "UNDER_REVIEW->EXPLAINED_NO_FURTHER_ACTION"]);
    expect(history.every((h) => h.ruleVersionId === alert.ruleVersionId)).toBe(true);
  });

  it("demo auth resolves only signed tokens for demo users", async () => {
    const secret = "s".repeat(40);
    const provider = new DemoAuthProvider(db, secret);
    const analyst = seed.actors.ANALYST;
    const token = issueDemoToken(secret, analyst.id);
    expect((await provider.resolve((n) => (n === DEMO_COOKIE ? token : undefined)))?.role).toBe("ANALYST");
    expect(await provider.resolve(() => token.slice(0, -2) + "xx")).toBeNull();
    const realUser = await db.user.create({ data: { email: "real@example.org", name: "Not a demo user", role: "ADMINISTRATOR" } });
    expect(await provider.resolve(() => issueDemoToken(secret, realUser.id))).toBeNull();
  });
});

describe("imports", () => {
  it("skips identical re-imports and in-file duplicates, imports the rest", async () => {
    const out = await runImport(as(seed, "ANALYST"), importReq("duplicate-transactions.csv", true));
    expect(out.status).toBe("COMMITTED");
    expect(out.report).toMatchObject({ totalRows: 3, acceptedRows: 1, duplicateRows: 2, rejectedRows: 0 });
    expect(out.report.duplicates.map((d) => d.reason)).toEqual([
      "Identical to row 2 in this file; skipped",
      "Already imported with identical content; skipped",
    ]);
    expect(await db.transaction.count({ where: { recordId: "SYN-PAY-900" } })).toBe(1);
  });

  it("rejects an invalid batch as a whole with actionable errors, and counts it on the overview", async () => {
    const before = await db.transaction.count();
    const amountBefore = (await db.transaction.findUniqueOrThrow({ where: { recordId: "SYN-PAY-002" } })).amount?.toString();
    const out = await runImport(as(seed, "ANALYST"), importReq("invalid-transactions.csv", true));
    expect(out.status).toBe("REJECTED");
    const msgs = out.report.errors.map((e) => `${e.row}:${e.field}:${e.message}`);
    expect(msgs).toEqual(
      expect.arrayContaining([
        expect.stringMatching(/^1:recordId:.*already exists with different content/),
        expect.stringMatching(/^2:type:"REFUND" is not one of/),
        expect.stringMatching(/^3:amount:/),
        expect.stringMatching(/^3:occurredAt:.*ISO 8601/),
        expect.stringMatching(/^4:recordId:Required/),
        expect.stringMatching(/^5:null:Has 5 cells; the header has 7/),
      ]),
    );
    expect(await db.transaction.count()).toBe(before);
    expect((await db.transaction.findUniqueOrThrow({ where: { recordId: "SYN-PAY-002" } })).amount?.toString()).toBe(amountBefore);
    const batch = await db.importBatch.findUniqueOrThrow({ where: { id: out.batchId! } });
    expect(batch.rejectedRows).toBe(out.report.rejectedRows);
  });

  it("stores malicious markup verbatim as data; nothing is interpreted", async () => {
    const ev = await db.evidence.findUniqueOrThrow({ where: { recordId: "SYN-EV-004" } });
    expect(ev.excerpt.startsWith("<script>alert('stored-xss-test')</script>")).toBe(true);
    expect(ev.title).toContain("<img src=x onerror=alert(1)>");
  });
});

describe("entity resolution review", () => {
  it("keeps the rejected incorrect link rejected when candidates are regenerated", async () => {
    const out = await generateCandidateLinks(as(seed, "ANALYST"));
    expect(out.created).toBe(0);
    const wrong = await db.relationship.findFirstOrThrow({ where: { basis: "CANDIDATE_NAME_SIMILARITY" } });
    expect(wrong.status).toBe("REJECTED");
  });

  it("supports confirming and reversing a link, keeping the history", async () => {
    const link = await db.relationship.findFirstOrThrow({ where: { basis: "CANDIDATE_SHARED_ADDRESS" } });
    const reviewer = as(seed, "REVIEWER");
    await expect(reviewRelationship(reviewer, link.id, "REVERSE", "cannot reverse a candidate")).rejects.toThrow(ValidationError);
    await expect(reviewRelationship(as(seed, "ANALYST"), link.id, "CONFIRM", "analysts cannot confirm")).rejects.toThrow(ForbiddenError);
    await reviewRelationship(reviewer, link.id, "CONFIRM", "Both records list the same business-centre address.");
    expect((await db.relationship.findUniqueOrThrow({ where: { id: link.id } })).claimStatus).toBe("REVIEWED_FINDING");
    await reviewRelationship(reviewer, link.id, "REVERSE", "The fixture addresses differ by suite; reversing.");
    const now = await db.relationship.findUniqueOrThrow({ where: { id: link.id } });
    expect(now.status).toBe("REVERSED");
    expect(await db.reviewDecision.count({ where: { targetType: "RELATIONSHIP", targetId: link.id } })).toBe(2);
  });
});

describe("exports", () => {
  it("redacts names, approvers, contact details and restricted excerpts, and audits the export", async () => {
    const inv = await db.investigation.findFirstOrThrow();
    const out = await exportInvestigation(as(seed, "ANALYST"), inv.id, "redacted");
    const text = JSON.stringify(out);
    expect(text).not.toContain("Demo Analyst");
    expect(text).not.toContain("Demo Reviewer");
    expect(text).not.toContain("Person A (synthetic)");
    expect(out.evidence.find((e) => e.recordId === "SYN-EV-001")?.excerpt).toBe("[WITHHELD: CONFIDENTIAL]");
    expect(out.containsSyntheticData).toBe(true);
    expect(out.disclaimers.join(" ")).toMatch(/not a finding of fraud/);
    expect(await db.auditEvent.count({ where: { action: "export.investigation", targetId: inv.id } })).toBe(1);
    await expect(exportInvestigation(as(seed, "ANALYST"), inv.id, "unredacted")).rejects.toThrow(ForbiddenError);
    const full = await exportInvestigation(as(seed, "ADMINISTRATOR"), inv.id, "unredacted");
    expect(JSON.stringify(full)).toContain("Demo Analyst");
  });
});

describe("OSINT collection", () => {
  it("records a manual public-source excerpt without any outbound request", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const out = await collectEvidence(as(seed, "ANALYST"), "manual-url", {
      url: "https://example.org/public-notice",
      title: "Public notice",
      excerpt: "The notice lists the contract award date as 2026-02-01.",
      sourceTitle: "Example Gazette",
    });
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
    const ev = await db.evidence.findUniqueOrThrow({ where: { id: out.created[0] } });
    expect(ev).toMatchObject({ origin: "PUBLIC_SOURCE", extractionMethod: "MANUAL_EXCERPT", accessClassification: "PUBLIC", isSynthetic: false });
    await expect(collectEvidence(as(seed, "ANALYST"), "manual-url", { url: "javascript:alert(1)", title: "x", excerpt: "x".repeat(20), sourceTitle: "s" })).rejects.toThrow(
      ValidationError,
    );
  });
});
