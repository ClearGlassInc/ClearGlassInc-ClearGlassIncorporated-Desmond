import { describe, expect, it } from "vitest";
import { evaluateRule, NOT_A_CLEARANCE, NOT_A_FINDING, NOT_CLEARED } from "@/lib/rules/engine";
import { d, META, NOW, rec, template } from "./helpers";

describe("sequence: banking-detail change followed by payment (CG-T-001, window 14 days)", () => {
  const def = template("CG-T-001");

  it("matches a payment 7 days after a bank change and explains it", () => {
    const out = evaluateRule(
      def,
      META,
      [
        rec("BC-1", "BANK_DETAIL_CHANGE", { vendorRecordId: "V-1", occurredAt: d("2026-03-02T10:00:00Z") }),
        rec("PAY-1", "PAYMENT", { vendorRecordId: "V-1", occurredAt: d("2026-03-09T10:00:00Z"), amount: 48000 }),
      ],
      NOW,
    );
    expect(out.results).toHaveLength(1);
    const r = out.results[0];
    expect(r.outcome).toBe("MATCH");
    expect(r.subjectKey).toBe("vendor:V-1");
    expect(r.matchedRecordIds).toEqual(["BC-1", "PAY-1"]);
    expect(r.ruleVersion).toBe(1);
    expect(r.evaluatedAt).toBe(NOW.toISOString());
    expect(r.explanation).toContain("7 day(s) after BANK_DETAIL_CHANGE BC-1");
    expect(r.explanation).toContain(NOT_A_FINDING);
    expect(r.conditions.map((c) => [c.id, c.result])).toEqual([
      ["first", "TRUE"],
      ["then", "TRUE"],
      ["window", "TRUE"],
    ]);
  });

  it("treats exactly the window length as inside, one millisecond more as outside", () => {
    const change = rec("BC-1", "BANK_DETAIL_CHANGE", { vendorRecordId: "V-1", occurredAt: d("2026-03-01T00:00:00Z") });
    const atEdge = rec("PAY-EDGE", "PAYMENT", { vendorRecordId: "V-1", occurredAt: d("2026-03-15T00:00:00Z") });
    const past = rec("PAY-PAST", "PAYMENT", { vendorRecordId: "V-1", occurredAt: d("2026-03-15T00:00:00.001Z") });
    expect(evaluateRule(def, META, [change, atEdge], NOW).results[0].outcome).toBe("MATCH");
    expect(evaluateRule(def, META, [change, past], NOW).results[0].outcome).toBe("NO_MATCH");
  });

  it("does not match a payment at the same instant or before the change", () => {
    const change = rec("BC-1", "BANK_DETAIL_CHANGE", { vendorRecordId: "V-1", occurredAt: d("2026-03-10T00:00:00Z") });
    const same = rec("PAY-SAME", "PAYMENT", { vendorRecordId: "V-1", occurredAt: d("2026-03-10T00:00:00Z") });
    const before = rec("PAY-BEFORE", "PAYMENT", { vendorRecordId: "V-1", occurredAt: d("2026-03-09T00:00:00Z") });
    expect(evaluateRule(def, META, [change, same, before], NOW).results[0].outcome).toBe("NO_MATCH");
  });

  it("returns NO_MATCH, not 'safe', for a legitimate-looking pattern outside the window", () => {
    const out = evaluateRule(
      def,
      META,
      [
        rec("BC-2", "BANK_DETAIL_CHANGE", { vendorRecordId: "V-2", occurredAt: d("2026-01-10T00:00:00Z") }),
        rec("PAY-2", "PAYMENT", { vendorRecordId: "V-2", occurredAt: d("2026-03-20T00:00:00Z") }),
      ],
      NOW,
    );
    const r = out.results[0];
    expect(r.outcome).toBe("NO_MATCH");
    expect(r.explanation).toContain(NOT_A_CLEARANCE);
    expect(r.explanation.toLowerCase()).not.toContain("safe");
  });

  it("does not group by name: records without a vendor identifier are INSUFFICIENT_DATA", () => {
    const out = evaluateRule(
      def,
      META,
      [
        rec("BC-3", "BANK_DETAIL_CHANGE", { occurredAt: d("2026-03-02T00:00:00Z"), description: "Example Paving Ltd" }),
        rec("PAY-3", "PAYMENT", { vendorRecordId: "", occurredAt: d("2026-03-03T00:00:00Z") }),
      ],
      NOW,
    );
    expect(out.results.map((r) => r.outcome)).toEqual(["INSUFFICIENT_DATA", "INSUFFICIENT_DATA"]);
    expect(out.results[0].missingFields).toEqual([{ recordId: "BC-3", field: "vendorRecordId" }]);
    expect(out.results[0].explanation).toContain(NOT_CLEARED);
  });

  it("returns INSUFFICIENT_DATA when a timestamp is missing and nothing else matched", () => {
    const out = evaluateRule(
      def,
      META,
      [
        rec("BC-4", "BANK_DETAIL_CHANGE", { vendorRecordId: "V-4", occurredAt: d("2026-03-02T00:00:00Z") }),
        rec("PAY-4", "PAYMENT", { vendorRecordId: "V-4" }),
      ],
      NOW,
    );
    expect(out.results[0].outcome).toBe("INSUFFICIENT_DATA");
    expect(out.results[0].missingFields).toEqual([{ recordId: "PAY-4", field: "occurredAt" }]);
  });

  it("returns NO_MATCH when no bank change exists, even if a payment lacks a timestamp", () => {
    const out = evaluateRule(def, META, [rec("PAY-5", "PAYMENT", { vendorRecordId: "V-5" })], NOW);
    expect(out.results[0].outcome).toBe("NO_MATCH");
    expect(out.results[0].missingFields).toEqual([{ recordId: "PAY-5", field: "occurredAt" }]);
    expect(out.results[0].explanation).toContain("no BANK_DETAIL_CHANGE is recorded for this vendor in the supplied records");
  });

  it("is deterministic", () => {
    const records = [
      rec("PAY-1", "PAYMENT", { vendorRecordId: "V-1", occurredAt: d("2026-03-09T10:00:00Z") }),
      rec("BC-1", "BANK_DETAIL_CHANGE", { vendorRecordId: "V-1", occurredAt: d("2026-03-02T10:00:00Z") }),
    ];
    expect(evaluateRule(def, META, records, NOW)).toEqual(evaluateRule(def, META, [...records].reverse(), NOW));
  });
});

describe("aggregate: purchases near a threshold (CG-T-002)", () => {
  const def = template("CG-T-002"); // each < 25000, >= 2 records, total >= 25000, 30 days

  it("matches two sub-threshold purchases whose total reaches the threshold", () => {
    const out = evaluateRule(
      def,
      META,
      [
        rec("PO-1", "PURCHASE_ORDER", { vendorRecordId: "V-5", amount: 14000, occurredAt: d("2026-04-01T00:00:00Z") }),
        rec("PO-2", "PURCHASE_ORDER", { vendorRecordId: "V-5", amount: 12500, occurredAt: d("2026-04-20T00:00:00Z") }),
      ],
      NOW,
    );
    expect(out.results[0].outcome).toBe("MATCH");
    expect(out.results[0].explanation).toContain("totalling 26500");
  });

  it("does not match a legitimate pair below the total", () => {
    const out = evaluateRule(
      def,
      META,
      [
        rec("PO-3", "PURCHASE_ORDER", { vendorRecordId: "V-6", amount: 9000, occurredAt: d("2026-04-01T00:00:00Z") }),
        rec("PO-4", "PURCHASE_ORDER", { vendorRecordId: "V-6", amount: 8000, occurredAt: d("2026-04-05T00:00:00Z") }),
      ],
      NOW,
    );
    expect(out.results[0].outcome).toBe("NO_MATCH");
  });

  it("respects the window boundary (30 days inclusive)", () => {
    const a = rec("PO-5", "PURCHASE_ORDER", { vendorRecordId: "V-7", amount: 13000, occurredAt: d("2026-04-01T00:00:00Z") });
    const inside = rec("PO-6", "PURCHASE_ORDER", { vendorRecordId: "V-7", amount: 13000, occurredAt: d("2026-05-01T00:00:00Z") });
    const outside = rec("PO-7", "PURCHASE_ORDER", { vendorRecordId: "V-7", amount: 13000, occurredAt: d("2026-05-01T00:00:01Z") });
    expect(evaluateRule(def, META, [a, inside], NOW).results[0].outcome).toBe("MATCH");
    expect(evaluateRule(def, META, [a, outside], NOW).results[0].outcome).toBe("NO_MATCH");
  });

  it("excludes purchases at or above the approval threshold", () => {
    const out = evaluateRule(
      def,
      META,
      [
        rec("PO-8", "PURCHASE_ORDER", { vendorRecordId: "V-8", amount: 25000, occurredAt: d("2026-04-01T00:00:00Z") }),
        rec("PO-9", "PURCHASE_ORDER", { vendorRecordId: "V-8", amount: 1000, occurredAt: d("2026-04-02T00:00:00Z") }),
      ],
      NOW,
    );
    expect(out.results[0].outcome).toBe("NO_MATCH");
  });

  it("reports INSUFFICIENT_DATA rather than NO_MATCH when an amount is missing", () => {
    const out = evaluateRule(
      def,
      META,
      [
        rec("PO-10", "PURCHASE_ORDER", { vendorRecordId: "V-9", amount: 14000, occurredAt: d("2026-04-01T00:00:00Z") }),
        rec("PO-11", "PURCHASE_ORDER", { vendorRecordId: "V-9", occurredAt: d("2026-04-02T00:00:00Z") }),
      ],
      NOW,
    );
    expect(out.results[0].outcome).toBe("INSUFFICIENT_DATA");
    expect(out.results[0].missingFields).toEqual([{ recordId: "PO-11", field: "amount" }]);
  });
});

describe("record checks", () => {
  it("CG-T-003: blank PO reference matches; absent PO column is insufficient, not a match", () => {
    const def = template("CG-T-003");
    const out = evaluateRule(
      def,
      META,
      [
        rec("PAY-BLANK", "PAYMENT", { poReference: "" }),
        rec("PAY-NOCOL", "PAYMENT", { amount: 100 }),
        rec("PAY-OK", "PAYMENT", { poReference: "PO-77" }),
      ],
      NOW,
    );
    const byId = Object.fromEntries(out.results.map((r) => [r.matchedRecordIds[0], r.outcome]));
    expect(byId).toEqual({ "PAY-BLANK": "MATCH", "PAY-NOCOL": "INSUFFICIENT_DATA", "PAY-OK": "NO_MATCH" });
  });

  it("CG-T-004: change order approved after work started, with grace boundary", () => {
    const def = template("CG-T-004");
    const late = rec("CO-1", "CHANGE_ORDER", { approvedAt: d("2026-05-10T00:00:00Z"), workStartedAt: d("2026-05-01T00:00:00Z") });
    const sameTime = rec("CO-2", "CHANGE_ORDER", { approvedAt: d("2026-05-01T00:00:00Z"), workStartedAt: d("2026-05-01T00:00:00Z") });
    const missing = rec("CO-3", "CHANGE_ORDER", { approvedAt: d("2026-05-01T00:00:00Z") });
    const out = evaluateRule(def, META, [late, sameTime, missing], NOW);
    expect(out.results.map((r) => r.outcome)).toEqual(["MATCH", "NO_MATCH", "INSUFFICIENT_DATA"]);
    expect(out.results[0].conditions[0].actual).toMatchObject({ differenceDays: 9 });
  });

  it("Kleene AND: a definite FALSE condition wins over an unknown applicability field", () => {
    const def = template("CG-T-005");
    const out = evaluateRule(def, META, [rec("PO-E", "PURCHASE_ORDER", { documents: ["quote", "approval_form"] })], NOW);
    expect(out.results[0].outcome).toBe("NO_MATCH");
    expect(out.results[0].missingFields).toEqual([{ recordId: "PO-E", field: "amount" }]);
  });

  it("CG-T-005: applicability uses a known amount; unknown amount is insufficient", () => {
    const def = template("CG-T-005");
    const out = evaluateRule(
      def,
      META,
      [
        rec("PO-A", "PURCHASE_ORDER", { amount: 50000, documents: ["quote"] }),
        rec("PO-B", "PURCHASE_ORDER", { amount: 50000, documents: ["quote", "approval_form"] }),
        rec("PO-C", "PURCHASE_ORDER", { amount: 500, documents: [] }),
        rec("PO-D", "PURCHASE_ORDER", { documents: [] }),
      ],
      NOW,
    );
    expect(out.outOfScope).toBe(1); // PO-C is below the document threshold
    const byId = Object.fromEntries(out.results.map((r) => [r.matchedRecordIds[0], r.outcome]));
    expect(byId).toEqual({ "PO-A": "MATCH", "PO-B": "NO_MATCH", "PO-D": "INSUFFICIENT_DATA" });
    const a = out.results.find((r) => r.matchedRecordIds[0] === "PO-A")!;
    expect(a.conditions.find((c) => c.id === "documents_missing")!.actual).toMatchObject({ absent: ["approval_form"] });
  });

  it("CG-T-006: approval recorded after the payment matches; approval before payment does not", () => {
    const def = template("CG-T-006");
    const out = evaluateRule(
      def,
      META,
      [
        rec("PAY-X", "PAYMENT", { approvedAt: d("2026-06-05T00:00:00Z"), occurredAt: d("2026-06-01T00:00:00Z") }),
        rec("PAY-Y", "PAYMENT", { approvedAt: d("2026-06-01T00:00:00Z"), occurredAt: d("2026-06-05T00:00:00Z") }),
      ],
      NOW,
    );
    expect(out.results.map((r) => r.outcome)).toEqual(["MATCH", "NO_MATCH"]);
  });
});
