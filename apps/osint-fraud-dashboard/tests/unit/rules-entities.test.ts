import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { citedRecordIds, conditionSupport, formatIssues, ruleDefinitionSchema } from "@/lib/rules/schema";
import { nameSimilarity, proposeLinks, type ResolvableEntity } from "@/lib/entities/resolve";
import { template } from "./helpers";

describe("rule definitions", () => {
  const dir = join(__dirname, "..", "..", "rules", "templates");
  it.each(readdirSync(dir))("template %s is valid, illustrative, and every condition carries support", (file) => {
    const def = ruleDefinitionSchema.parse(JSON.parse(readFileSync(join(dir, file), "utf8")));
    expect(def.illustrative).toBe(true);
    expect(def.disclaimer).toMatch(/not derived from any verified or suppressed incident/);
    for (const c of conditionSupport(def.pattern)) {
      expect(c.support.evidenceIds.length + c.support.incidentIds.length > 0 || c.support.assumption !== null).toBe(true);
    }
    for (const t of Object.values(def.thresholds)) expect(t.rationale.length).toBeGreaterThanOrEqual(10);
  });

  it("refuses a threshold that is referenced but not defined", () => {
    const def = structuredClone(template("CG-T-001")) as Record<string, unknown>;
    def.thresholds = {};
    const r = ruleDefinitionSchema.safeParse(def);
    expect(r.success).toBe(false);
    expect(formatIssues(r.error!)).toContain('thresholds.windowDays: Threshold "windowDays" is referenced but not defined');
  });

  it("refuses a condition with no evidence and no stated assumption", () => {
    const def = structuredClone(template("CG-T-003")) as unknown as { pattern: { conditions: { support: unknown }[] } };
    def.pattern.conditions[0].support = { evidenceIds: [], incidentIds: [], assumption: null };
    expect(ruleDefinitionSchema.safeParse(def).success).toBe(false);
  });

  it("refuses a non-illustrative rule that cites nothing", () => {
    const def = { ...structuredClone(template("CG-T-003")), illustrative: false, disclaimer: null };
    const r = ruleDefinitionSchema.safeParse(def);
    expect(formatIssues(r.error!).join()).toMatch(/must cite the incidents or evidence/);
  });

  it("refuses a definition that still contains TODO placeholders", () => {
    const def = structuredClone(template("CG-T-001"));
    def.thresholds.windowDays.rationale = "TODO: state the documented basis";
    expect(formatIssues(ruleDefinitionSchema.safeParse(def).error!).join()).toMatch(/Replace every TODO placeholder/);
  });

  it("refuses a pattern field missing from requiredFields", () => {
    const def = { ...structuredClone(template("CG-T-004")), requiredFields: ["approvedAt"] };
    expect(formatIssues(ruleDefinitionSchema.safeParse(def).error!).join()).toMatch(/workStartedAt/);
  });

  it("collects every cited record id for traceability", () => {
    const def = structuredClone(template("CG-T-001"));
    def.supportingIncidentIds = ["INC-1"];
    def.pattern = { ...def.pattern } as typeof def.pattern;
    if (def.pattern.kind === "sequence_within_window") def.pattern.first.support = { evidenceIds: ["EV-2", "EV-1"], incidentIds: [], assumption: null };
    expect(citedRecordIds(def)).toEqual({ evidenceIds: ["EV-1", "EV-2"], incidentIds: ["INC-1"] });
  });
});

describe("entity resolution", () => {
  const e = (o: Partial<ResolvableEntity> & Pick<ResolvableEntity, "id" | "name">): ResolvableEntity => ({
    kind: "VENDOR",
    recordId: o.id,
    identifier: null,
    domain: null,
    address: null,
    ...o,
  });

  it("ignores legal suffixes and punctuation in name similarity", () => {
    expect(nameSimilarity("Northwind Supply Ltd.", "NORTHWIND SUPPLY INC")).toBe(1);
    expect(nameSimilarity("Example Paving", "Sample Office Supply")).toBe(0);
  });

  it("only proposes candidates for similarity, and says identifiers differ", () => {
    const links = proposeLinks([
      e({ id: "V-A", name: "Northwind Supply Ltd", identifier: "EX-1", address: "1 Main St" }),
      e({ id: "V-B", name: "Northwind Supply Inc", identifier: "EX-2", address: "9 Other Rd" }),
    ]);
    expect(links).toHaveLength(1);
    expect(links[0]).toMatchObject({ basis: "CANDIDATE_NAME_SIMILARITY", status: "CANDIDATE" });
    expect(links[0].basisDetail).toMatch(/identifiers differ/);
    expect(links[0].basisDetail).toMatch(/not evidence of common ownership/);
  });

  it("confirms only links the source states explicitly", () => {
    const links = proposeLinks([
      e({ id: "V-1", name: "Alpha", organizationId: "O-1" }),
      { kind: "ORGANIZATION", id: "O-1", recordId: "ORG-1", name: "Beta Holdings", identifier: null, domain: null, address: null },
      e({ id: "V-2", name: "Gamma", address: "100 Example Street, Testville" }),
      e({ id: "V-3", name: "Delta", address: "100 example st testville" }),
    ]);
    expect(links.filter((l) => l.status === "CONFIRMED")).toEqual([expect.objectContaining({ basis: "EXPLICIT_IDENTIFIER", fromId: "V-1", toId: "O-1" })]);
    expect(links.filter((l) => l.basis === "CANDIDATE_SHARED_ADDRESS")).toHaveLength(1);
  });
});
