"use server";

// Server actions. Each one authenticates, then calls a service; the service
// enforces authorization and validation. Redirect targets are built from ids,
// never taken from the form, so there is no open redirect.

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { DEMO_COOKIE, DEMO_TTL_SECONDS, issueDemoToken } from "@/lib/auth/demo";
import { getActor, requireCtx } from "@/lib/auth/server";
import { config } from "@/lib/config";
import { db } from "@/lib/db";
import { errorMessage } from "@/lib/errors";
import { addNote, createInvestigation, decideAlert, decideInvestigation, linkAlert, verifyEvidence } from "@/lib/services/cases";
import { audit, type Ctx } from "@/lib/services/context";
import { generateCandidateLinks, reviewRelationship } from "@/lib/services/entities";
import { addFact, collectEvidence } from "@/lib/services/evidence";
import { runImport, type ImportOutcome } from "@/lib/services/imports";
import { createRule, decideVersion, parseDefinitionText, proposeVersion, retireVersion, runEvaluation } from "@/lib/services/rules";
import type { ImportFormatName, ImportOriginName } from "@/lib/import/validate";
import type { ImportRecordTypeName } from "@/lib/import/fields";

const str = (f: FormData, k: string) => {
  const v = f.get(k);
  return typeof v === "string" ? v : "";
};
const ID = /^[A-Za-z0-9_-]{1,64}$/;
const id = (f: FormData, k: string) => {
  const v = str(f, k);
  if (!ID.test(v)) throw new Error(`Invalid ${k}`);
  return v;
};

function withMessage(path: string, kind: "ok" | "error", message: string) {
  return `${path}${path.includes("?") ? "&" : "?"}${kind}=${encodeURIComponent(message.slice(0, 1500))}`;
}

async function act(back: string, ok: string, fn: (ctx: Ctx) => Promise<string | void>): Promise<never> {
  const ctx = await requireCtx();
  let target: string;
  try {
    const dest = await fn(ctx);
    target = withMessage(dest ?? back, "ok", ok);
  } catch (e) {
    target = withMessage(back, "error", errorMessage(e));
  }
  redirect(target);
}

// ---------------------------------------------------------------- demo auth

export async function signInDemo(form: FormData) {
  const cfg = config();
  if (!cfg.demoAuthEnabled) redirect("/login?error=" + encodeURIComponent("Demo sign-in is disabled"));
  const userId = id(form, "userId");
  const user = await db().user.findFirst({ where: { id: userId, isDemo: true } });
  if (!user) redirect("/login?error=" + encodeURIComponent("Unknown demo user"));
  (await cookies()).set(DEMO_COOKIE, issueDemoToken(cfg.sessionSecret!, user.id), {
    httpOnly: true,
    sameSite: "strict",
    secure: false, // local http only; demo auth is refused outside APP_ENV=local/test
    path: "/",
    maxAge: DEMO_TTL_SECONDS,
  });
  await audit(db(), { id: user.id, role: user.role }, "auth.demo_sign_in", { type: "User", id: user.id });
  redirect("/");
}

export async function signOut() {
  const actor = await getActor();
  (await cookies()).delete(DEMO_COOKIE);
  if (actor) await audit(db(), actor, "auth.sign_out", { type: "User", id: actor.id });
  redirect("/login");
}

// ---------------------------------------------------------------- alerts & cases

export async function decideAlertAction(form: FormData) {
  const alertId = id(form, "alertId");
  await act(`/alerts/${alertId}`, "Decision recorded", (ctx) => decideAlert(ctx, alertId, str(form, "to"), str(form, "rationale")));
}

export async function decideInvestigationAction(form: FormData) {
  const invId = id(form, "investigationId");
  await act(`/investigations/${invId}`, "Decision recorded", (ctx) => decideInvestigation(ctx, invId, str(form, "to"), str(form, "rationale")));
}

export async function createInvestigationAction(form: FormData) {
  const alertIds = form.getAll("alertIds").filter((v): v is string => typeof v === "string" && ID.test(v));
  await act(alertIds.length === 1 ? `/alerts/${alertIds[0]}` : "/investigations", "Case opened", async (ctx) => {
    const caseId = await createInvestigation(ctx, { title: str(form, "title"), summary: str(form, "summary"), priority: str(form, "priority"), alertIds });
    return `/investigations/${caseId}`;
  });
}

export async function linkAlertAction(form: FormData) {
  const alertId = id(form, "alertId");
  await act(`/alerts/${alertId}`, "Alert added to case", (ctx) => linkAlert(ctx, alertId, id(form, "investigationId")));
}

export async function addNoteAction(form: FormData) {
  const invId = id(form, "investigationId");
  const evidence = str(form, "evidenceRecordIds").split(/[\s,]+/).filter(Boolean);
  await act(`/investigations/${invId}`, "Note added", async (ctx) => {
    await addNote(ctx, invId, { kind: str(form, "kind"), body: str(form, "body"), evidenceRecordIds: evidence });
  });
}

// ---------------------------------------------------------------- evidence

export async function verifyEvidenceAction(form: FormData) {
  const evId = id(form, "evidenceId");
  await act(`/evidence/${evId}`, "Verification recorded", (ctx) => verifyEvidence(ctx, evId, str(form, "status"), str(form, "rationale")));
}

export async function addFactAction(form: FormData) {
  const evId = id(form, "evidenceId");
  await act(`/evidence/${evId}`, "Statement recorded", (ctx) => addFact(ctx, evId, str(form, "statement"), str(form, "claimStatus")));
}

export async function collectEvidenceAction(form: FormData) {
  const adapterId = str(form, "adapterId");
  const fields: Record<string, string> = {};
  for (const [k, v] of form.entries()) if (typeof v === "string" && k !== "adapterId" && !k.startsWith("$")) fields[k] = v;
  await act("/evidence/new", "Evidence recorded", async (ctx) => {
    const out = await collectEvidence(ctx, adapterId, fields);
    if (out.created.length === 1) return `/evidence/${out.created[0]}`;
    return `/evidence?created=${out.created.length}&skipped=${out.skipped.length}`;
  });
}

// ---------------------------------------------------------------- rules

export async function createRuleAction(form: FormData) {
  await act("/rules/new", "Rule proposed; it stays inactive until a reviewer approves it", async (ctx) => {
    const { ruleId } = await createRule(ctx, { definition: parseDefinitionText(str(form, "definition")), changeSummary: str(form, "changeSummary") });
    return `/rules/${ruleId}`;
  });
}

export async function proposeVersionAction(form: FormData) {
  const ruleId = id(form, "ruleId");
  await act(`/rules/${ruleId}?edit=1`, "New version proposed; awaiting review", async (ctx) => {
    await proposeVersion(ctx, ruleId, { definition: parseDefinitionText(str(form, "definition")), changeSummary: str(form, "changeSummary") });
    return `/rules/${ruleId}`;
  });
}

export async function decideVersionAction(form: FormData) {
  const ruleId = id(form, "ruleId");
  const decision = str(form, "decision") === "APPROVE" ? "APPROVE" : "REJECT";
  await act(`/rules/${ruleId}`, decision === "APPROVE" ? "Version approved and active" : "Version rejected", (ctx) =>
    decideVersion(ctx, id(form, "versionId"), decision, str(form, "rationale")),
  );
}

export async function retireVersionAction(form: FormData) {
  const ruleId = id(form, "ruleId");
  await act(`/rules/${ruleId}`, "Version retired", (ctx) => retireVersion(ctx, id(form, "versionId"), str(form, "rationale")));
}

export async function runEvaluationAction() {
  await act("/alerts", "Evaluation finished", async (ctx) => {
    const s = await runEvaluation(ctx);
    return `/alerts?run=${encodeURIComponent(`${s.rules} rules: ${s.results.MATCH} match, ${s.results.NO_MATCH} no match, ${s.results.INSUFFICIENT_DATA} insufficient data; ${s.alertsCreated} new alerts`)}`;
  });
}

// ---------------------------------------------------------------- entities

export async function generateLinksAction() {
  await act("/entities", "Candidate links generated", async (ctx) => {
    await generateCandidateLinks(ctx);
  });
}

export async function reviewRelationshipAction(form: FormData) {
  await act("/entities", "Link decision recorded", (ctx) => reviewRelationship(ctx, id(form, "relationshipId"), str(form, "action"), str(form, "rationale")));
}

// ---------------------------------------------------------------- import

export type ImportActionState = { outcome?: ImportOutcome; error?: string } | null;

export async function importAction(_prev: ImportActionState, form: FormData): Promise<ImportActionState> {
  const ctx = await requireCtx();
  try {
    const file = form.get("file");
    if (!(file instanceof File) || file.size === 0) return { error: "Choose a .csv or .json file" };
    const cfg = config();
    if (file.size > cfg.importMaxBytes) return { error: `The file is ${file.size} bytes; the limit is ${cfg.importMaxBytes}` };
    const format = str(form, "format") as ImportFormatName;
    const recordType = str(form, "recordType") as ImportRecordTypeName;
    const origin = str(form, "origin") as ImportOriginName;
    if (!["CSV", "JSON"].includes(format)) return { error: "Choose CSV or JSON" };
    if (!["VENDOR", "TRANSACTION", "EVIDENCE", "INCIDENT"].includes(recordType)) return { error: "Choose a record type" };
    if (!["PUBLIC_SOURCE", "INTERNAL_RECORD", "SYNTHETIC"].includes(origin)) return { error: "Choose where the data comes from" };
    let mapping: Record<string, string> | null = null;
    const rawMapping = str(form, "mapping").trim();
    if (rawMapping) {
      try {
        const m = JSON.parse(rawMapping);
        if (!m || typeof m !== "object" || Array.isArray(m) || Object.values(m).some((v) => typeof v !== "string")) throw new Error();
        mapping = m as Record<string, string>;
      } catch {
        return { error: 'Field mapping must be a JSON object such as {"Vendor ID": "vendorRecordId"}' };
      }
    }
    const outcome = await runImport(ctx, {
      filename: file.name,
      bytes: new Uint8Array(await file.arrayBuffer()),
      format,
      recordType,
      origin,
      mapping,
      limits: { maxBytes: cfg.importMaxBytes, maxRows: cfg.importMaxRows },
      commit: str(form, "mode") === "commit",
    });
    return { outcome };
  } catch (e) {
    return { error: errorMessage(e) };
  }
}
