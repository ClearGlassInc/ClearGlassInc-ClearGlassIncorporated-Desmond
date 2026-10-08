// Export redaction. Pattern-based and conservative: it removes what it can
// recognise, and the export says so. A human still reviews before sharing.

const EMAIL = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g;
// Grouped like a phone number (separators required), so bare digit runs fall to LONG_NUMBER.
const PHONE = /(?:\+?\d{1,2}[\s.-])?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b/g;
// Account, card and transit numbers: 8 or more digits, optionally grouped.
const LONG_NUMBER = /\b\d(?:[\s-]?\d){7,}\b/g;

export function redactText(text: string): string {
  return text.replace(EMAIL, "[REDACTED EMAIL]").replace(PHONE, "[REDACTED PHONE]").replace(LONG_NUMBER, "[REDACTED NUMBER]");
}

export interface ExportEvidence {
  recordId: string;
  title: string;
  excerpt: string;
  url: string | null;
  accessClassification: string;
  verificationStatus: string;
  contentHash: string;
  isSynthetic: boolean;
  origin: string;
}

export interface ExportPerson {
  label: string;
  role: string;
}

export interface InvestigationExport {
  exportVersion: 1;
  generatedAt: string;
  redaction: { mode: "redacted" | "unredacted"; applied: string[]; notice: string };
  disclaimers: string[];
  containsSyntheticData: boolean;
  investigation: {
    caseKey: string;
    title: string;
    summary: string;
    status: string;
    claimStatus: string;
    owner: ExportPerson;
  };
  alerts: {
    ruleKey: string;
    ruleVersion: number;
    outcome: string;
    status: string;
    explanation: string;
    matchedRecordIds: string[];
    evidenceRefs: string[];
  }[];
  notes: { kind: string; body: string; author: ExportPerson; createdAt: string; evidenceRecordIds: string[] }[];
  decisions: { target: string; from: string | null; to: string; rationale: string; decidedBy: ExportPerson; at: string }[];
  evidence: ExportEvidence[];
  transactions: { recordId: string; type: string; vendorRecordId: string | null; approvedBy: string | null; description: string | null }[];
}

const WITHHELD = new Set(["CONFIDENTIAL", "RESTRICTED"]);

export function redactExport(data: InvestigationExport): InvestigationExport {
  const person = (p: ExportPerson): ExportPerson => ({ label: `[${p.role} user]`, role: p.role });
  return {
    ...data,
    redaction: {
      mode: "redacted",
      applied: [
        "User names replaced with their role",
        "approvedBy values on transactions removed",
        "Email addresses, phone numbers and 8+ digit numbers masked in free text",
        "Excerpts of CONFIDENTIAL and RESTRICTED evidence withheld",
      ],
      notice: "Automated pattern redaction. It can miss identifying details: review the file before sharing it.",
    },
    investigation: {
      ...data.investigation,
      title: redactText(data.investigation.title),
      summary: redactText(data.investigation.summary),
      owner: person(data.investigation.owner),
    },
    alerts: data.alerts.map((a) => ({ ...a, explanation: redactText(a.explanation) })),
    notes: data.notes.map((n) => ({ ...n, body: redactText(n.body), author: person(n.author) })),
    decisions: data.decisions.map((d) => ({ ...d, rationale: redactText(d.rationale), decidedBy: person(d.decidedBy) })),
    evidence: data.evidence.map((e) => ({
      ...e,
      title: redactText(e.title),
      excerpt: WITHHELD.has(e.accessClassification) ? `[WITHHELD: ${e.accessClassification}]` : redactText(e.excerpt),
    })),
    transactions: data.transactions.map((t) => ({
      ...t,
      approvedBy: t.approvedBy ? "[REDACTED PERSON]" : null,
      description: t.description ? redactText(t.description) : null,
    })),
  };
}
