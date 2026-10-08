// Synthetic demonstration data. Every record created here is a fixture: names
// use the reserved .example domain, people are "Person A (synthetic)", and no
// record describes a real organisation, person or incident.
//
// The seed goes through the same services a user does (imports, rule
// proposals, approvals, evaluation, review decisions), so the audit log and
// decision history it leaves are the real thing.

import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import type { Actor } from "./auth/actor";
import type { Db } from "./db";
import type { RoleName } from "./auth/roles";
import { runImport } from "./services/imports";
import { createRule, decideVersion, proposeVersion, runEvaluation } from "./services/rules";
import { addNote, createInvestigation, decideAlert } from "./services/cases";
import { generateCandidateLinks, reviewRelationship } from "./services/entities";
import { audit, type Ctx } from "./services/context";
import type { ImportRecordTypeName } from "./import/fields";

export const DEMO_USERS: { email: string; name: string; role: RoleName }[] = [
  { email: "admin@demo.clearglass.local", name: "Demo Administrator", role: "ADMINISTRATOR" },
  { email: "analyst@demo.clearglass.local", name: "Demo Analyst", role: "ANALYST" },
  { email: "reviewer@demo.clearglass.local", name: "Demo Reviewer", role: "REVIEWER" },
  { email: "readonly@demo.clearglass.local", name: "Demo Read-only", role: "READ_ONLY" },
];

export interface SeedResult {
  actors: Record<RoleName, Actor>;
  alerts: number;
}

function root(...parts: string[]): string {
  return join(process.cwd(), ...parts);
}

async function importFile(ctx: Ctx, file: string, recordType: ImportRecordTypeName) {
  const bytes = new Uint8Array(readFileSync(root("examples", "imports", file)));
  const out = await runImport(ctx, {
    filename: file,
    bytes,
    format: file.endsWith(".csv") ? "CSV" : "JSON",
    recordType,
    origin: "SYNTHETIC",
    mapping: null,
    limits: { maxBytes: 1_000_000, maxRows: 10_000 },
    commit: true,
  });
  if (out.status !== "COMMITTED") {
    throw new Error(`Seed import ${file} failed: ${JSON.stringify(out.report.errors, null, 2)}`);
  }
}

function readRule(dir: string, file: string): unknown {
  return JSON.parse(readFileSync(root("rules", dir, file), "utf8"));
}

export async function seedDemo(db: Db): Promise<SeedResult> {
  const users = await Promise.all(
    DEMO_USERS.map((u) => db.user.upsert({ where: { email: u.email }, update: {}, create: { ...u, isDemo: true } })),
  );
  const actors = Object.fromEntries(
    users.map((u) => [u.role, { id: u.id, email: u.email, name: u.name, role: u.role as RoleName, isDemo: true }]),
  ) as Record<RoleName, Actor>;
  const analyst: Ctx = { db, actor: actors.ANALYST };
  const reviewer: Ctx = { db, actor: actors.REVIEWER };

  // Organizations and people have no import path in the prototype; create them directly.
  const buyer = await db.organization.create({
    data: { recordId: "ORG-SYN-001", name: "Example Municipal Works Department", domain: "works.example", address: "1 Civic Square, Testville", origin: "SYNTHETIC", isSynthetic: true },
  });
  await db.organization.create({
    data: { recordId: "ORG-SYN-002", name: "Example Holdings Ltd", registrationNumber: "EX-HOLD-01", domain: "exampleholdings.example", address: "9 Holding Row, Testville", origin: "SYNTHETIC", isSynthetic: true },
  });
  await db.person.create({
    data: { recordId: "PER-SYN-001", displayName: "Person A (synthetic)", roleTitle: "Procurement officer", organizationId: buyer.id, origin: "SYNTHETIC", isSynthetic: true },
  });
  await audit(db, actors.ADMINISTRATOR, "seed.reference_entities", { type: "Organization" }, { organizations: 2, people: 1, synthetic: true });

  await importFile(analyst, "synthetic-vendors.csv", "VENDOR");
  await importFile(analyst, "synthetic-evidence.json", "EVIDENCE");
  await importFile(analyst, "synthetic-transactions.csv", "TRANSACTION");
  await importFile(analyst, "synthetic-transactions-partial.json", "TRANSACTION");
  await importFile(analyst, "synthetic-incident.json", "INCIDENT");

  // Illustrative templates: proposed by the analyst, approved by the reviewer.
  for (const file of readdirSync(root("rules", "templates")).sort()) {
    const { versionId } = await createRule(analyst, { definition: readRule("templates", file), changeSummary: "Initial illustrative template" });
    await decideVersion(reviewer, versionId, "APPROVE", "Approved for evaluation against synthetic demonstration data only.");
  }

  // Incident-to-rule: v1 approved (step G), v2 left pending to show a version change awaiting review.
  const derived = await createRule(analyst, {
    definition: readRule("derived", "syn-r-001.v1.json"),
    changeSummary: "Derived from SYN-INC-001 steps A-D",
    isSynthetic: true,
  });
  await decideVersion(reviewer, derived.versionId, "APPROVE", "Each condition maps to SYN-INC-001 evidence; threshold cites policy fixture SYN-EV-005.");

  await runEvaluation(analyst);

  await proposeVersion(analyst, derived.ruleId, {
    definition: readRule("derived", "syn-r-001.v2.json"),
    changeSummary: "Narrow the window from 14 to 10 days",
  });

  // A case with a reviewed history.
  const alerts = await db.alert.findMany({ include: { rule: true } });
  const derivedMatch = alerts.find((a) => a.rule.ruleKey === "SYN-R-001" && a.outcome === "MATCH");
  const templateMatch = alerts.find((a) => a.rule.ruleKey === "CG-T-001" && a.outcome === "MATCH");
  const blankPo = alerts.find((a) => a.rule.ruleKey === "CG-T-003" && a.outcome === "MATCH");
  if (derivedMatch && templateMatch) {
    const caseId = await createInvestigation(analyst, {
      title: "Synthetic case: payment after banking-detail change, vendor SYN-V-001",
      summary: "SYNTHETIC demonstration case opened from two rule matches on the same records. Nothing in it is an established finding.",
      priority: "HIGH",
      alertIds: [derivedMatch.id, templateMatch.id],
    });
    await addNote(analyst, caseId, {
      kind: "OBSERVATION",
      body: "The change request's callback verification field is blank (SYN-EV-001), and the payment was released 7 days later (SYN-EV-002).",
      evidenceRecordIds: ["SYN-EV-001", "SYN-EV-002"],
    });
    await addNote(analyst, caseId, {
      kind: "INTERPRETATION",
      body: "Possible gap in the callback control. This is an interpretation; a callback log held elsewhere could explain it.",
      evidenceRecordIds: ["SYN-EV-005"],
    });
    await addNote(analyst, caseId, {
      kind: "QUESTION",
      body: "Does a telephone log exist for CR-0042? The public notice (SYN-EV-003) conflicts with the change request.",
      evidenceRecordIds: ["SYN-EV-003"],
    });
    await decideAlert(analyst, derivedMatch.id, "UNDER_REVIEW", "Taking this into review; both records are present.");
    await decideAlert(analyst, derivedMatch.id, "ESCALATED_FOR_REVIEW", "Callback evidence is missing; a reviewer should decide the next step.");
  }
  if (blankPo) {
    await decideAlert(analyst, blankPo.id, "UNDER_REVIEW", "Checking the payment category against the policy fixture.");
    await decideAlert(reviewer, blankPo.id, "EXPLAINED_NO_FURTHER_ACTION", "Signage replacement under the fixture's low-value exemption; no PO required.");
  }

  // Entity candidates; the reviewer rejects the incorrect Northwind link.
  await generateCandidateLinks(analyst);
  const wrong = await db.relationship.findFirst({ where: { basis: "CANDIDATE_NAME_SIMILARITY", status: "CANDIDATE" } });
  if (wrong) {
    await reviewRelationship(reviewer, wrong.id, "REJECT", "Different tax identifiers and addresses; the similar names are coincidental.");
  }

  return { actors, alerts: await db.alert.count() };
}
