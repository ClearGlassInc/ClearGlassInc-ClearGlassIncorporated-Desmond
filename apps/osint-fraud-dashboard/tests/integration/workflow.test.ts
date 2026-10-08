import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { createRule, decideVersion, runEvaluation } from "@/lib/services/rules";
import { ValidationError } from "@/lib/errors";
import { getOverview } from "@/lib/services/overview";
import type { SeedResult } from "@/lib/seed";
import { alertFor, as, db, resetAndSeed } from "./support";

let seed: SeedResult;
beforeAll(async () => {
  seed = await resetAndSeed();
});
afterAll(() => db.$disconnect());

describe("seeded synthetic fixtures", () => {
  it("produce the designed outcomes per rule", async () => {
    const rows = await db.ruleEvaluation.findMany({ include: { ruleVersion: { include: { rule: true } } } });
    const key = (r: (typeof rows)[number]) => `${r.ruleVersion.rule.ruleKey}|${r.subjectKey}`;
    const outcome = Object.fromEntries(rows.map((r) => [key(r), r.outcome]));
    // Supported rule match.
    expect(outcome["SYN-R-001|vendor:SYN-V-001"]).toBe("MATCH");
    // Legitimate transaction with similar characteristics (payment 69 days after a verified change).
    expect(outcome["SYN-R-001|vendor:SYN-V-002"]).toBe("NO_MATCH");
    // Missing critical fields.
    expect(outcome["CG-T-003|record:SYN-PAY-005"]).toBe("INSUFFICIENT_DATA");
    expect(outcome["CG-T-004|record:SYN-CO-303"]).toBe("INSUFFICIENT_DATA");
    expect(outcome["CG-T-002|vendor:SYN-V-003"]).toBe("MATCH");
    expect(outcome["CG-T-002|vendor:SYN-V-002"]).toBe("NO_MATCH");
  });

  it("raise alerts only for MATCH and INSUFFICIENT_DATA; insufficient data waits for evidence", async () => {
    const alerts = await db.alert.findMany();
    expect(alerts.every((a) => a.outcome !== "NO_MATCH")).toBe(true);
    expect(alerts.filter((a) => a.outcome === "INSUFFICIENT_DATA").every((a) => ["NEEDS_EVIDENCE"].includes(a.status))).toBe(true);
    expect(alerts.every((a) => a.isSynthetic)).toBe(true);
  });

  it("every alert explains itself and links to records that exist", async () => {
    const alerts = await db.alert.findMany();
    for (const a of alerts) {
      expect(a.explanation).toMatch(/Rule [A-Z0-9-]+ v\d+/);
      const found = await db.transaction.count({ where: { recordId: { in: a.matchedRecordIds } } });
      expect(found).toBe(a.matchedRecordIds.length);
      const ev = await db.evidence.count({ where: { recordId: { in: a.evidenceRefs } } });
      expect(ev).toBe(a.evidenceRefs.length);
    }
  });
});

describe("source-to-rule traceability", () => {
  it("links every condition of the derived rule to stored evidence or the incident", async () => {
    const v1 = await db.ruleVersion.findFirstOrThrow({ where: { rule: { ruleKey: "SYN-R-001" }, version: 1 }, include: { support: { include: { evidence: true, incident: true } } } });
    const byCondition = new Map<string | null, string[]>();
    for (const s of v1.support) {
      byCondition.set(s.conditionId, [...(byCondition.get(s.conditionId) ?? []), s.evidence?.recordId ?? s.incident!.recordId]);
    }
    expect(byCondition.get("first")?.sort()).toEqual(["SYN-EV-001", "SYN-INC-001"]);
    expect(byCondition.get("then")?.sort()).toEqual(["SYN-EV-002", "SYN-INC-001"]);
    expect(byCondition.get("window")).toEqual(["SYN-EV-005"]);
    expect(byCondition.get("threshold:windowDays")).toEqual(["SYN-EV-005"]);
  });

  it("refuses a rule that cites evidence that does not exist", async () => {
    const def = JSON.parse(JSON.stringify((await db.ruleVersion.findFirstOrThrow({ where: { rule: { ruleKey: "SYN-R-001" }, version: 1 } })).definition));
    def.ruleKey = "SYN-R-404";
    def.supportingEvidenceIds = ["SYN-EV-DOES-NOT-EXIST"];
    await expect(createRule(as(seed, "ANALYST"), { definition: def, changeSummary: "bad citation" })).rejects.toThrow(ValidationError);
  });
});

describe("rule versioning", () => {
  it("keeps old alerts on the old version, runs only approved versions, and does not duplicate alerts", async () => {
    const before = await alertFor("SYN-R-001", "MATCH", "vendor:SYN-V-001");
    expect(before.ruleVersion.version).toBe(1);
    const v2 = await db.ruleVersion.findFirstOrThrow({ where: { rule: { ruleKey: "SYN-R-001" }, version: 2 } });
    expect(v2.status).toBe("PENDING_APPROVAL");
    expect(await db.ruleEvaluation.count({ where: { ruleVersionId: v2.id } })).toBe(0); // pending versions never ran

    await decideVersion(as(seed, "REVIEWER"), v2.id, "APPROVE", "Policy wording supports a 10 day window.");
    const v1 = await db.ruleVersion.findFirstOrThrow({ where: { rule: { ruleKey: "SYN-R-001" }, version: 1 } });
    expect(v1.status).toBe("SUPERSEDED");

    const run = await runEvaluation(as(seed, "ANALYST"));
    const after = await db.alert.findMany({ where: { rule: { ruleKey: "SYN-R-001" } }, include: { ruleVersion: true } });
    expect(after.map((a) => a.ruleVersion.version).sort()).toEqual([1, 2]);
    expect(await db.alert.findUniqueOrThrow({ where: { id: before.id } })).toMatchObject({ ruleVersionId: before.ruleVersionId, status: before.status });

    const again = await runEvaluation(as(seed, "ANALYST"));
    expect(again.alertsCreated).toBe(0);
    expect(again.alertsExisting).toBe(run.alertsCreated + run.alertsExisting);
  });
});

describe("overview", () => {
  it("derives every count from stored records", async () => {
    const o = await getOverview(as(seed, "READ_ONLY"));
    expect(o.records.transactions).toBe(await db.transaction.count());
    expect(o.records.evidence).toBe(await db.evidence.count());
    expect(o.alerts.awaitingReview).toBe(await db.alert.count({ where: { status: { in: ["NEW", "NEEDS_EVIDENCE", "UNDER_REVIEW", "ESCALATED_FOR_REVIEW"] } } }));
    expect(o.evidence.complete).toBe((await db.evidence.findMany()).filter((e) => e.missingFields.length === 0).length);
    expect(o.records.synthetic).toBe(o.records.transactions + o.records.vendors + o.records.evidence + o.records.incidents);
  });
});
