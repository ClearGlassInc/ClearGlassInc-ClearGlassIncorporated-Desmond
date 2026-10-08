// Status labels. Each carries its meaning in words, never in colour alone.

import type { ReactNode } from "react";

function Pill({ tone, children, title }: { tone: string; children: ReactNode; title?: string }) {
  return (
    <span
      title={title}
      className={`inline-flex items-center whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${tone}`}
    >
      {children}
    </span>
  );
}

const TONES = {
  amber: "border-amber-300/40 bg-amber-300/10 text-amber-200",
  rose: "border-rose-300/40 bg-rose-300/10 text-rose-200",
  sky: "border-sky-300/40 bg-sky-300/10 text-sky-200",
  violet: "border-violet-300/40 bg-violet-300/10 text-violet-200",
  emerald: "border-emerald-300/40 bg-emerald-300/10 text-emerald-200",
  cyan: "border-cyan-300/40 bg-cyan-300/10 text-cyan-200",
  slate: "border-slate-300/30 bg-slate-300/5 text-slate-300",
};

export function SyntheticBadge({ synthetic }: { synthetic: boolean }) {
  if (!synthetic) return null;
  return (
    <Pill tone={TONES.amber} title="Synthetic fixture created for demonstration. Not a real record.">
      Synthetic
    </Pill>
  );
}

export const CLAIM_LABELS: Record<string, { label: string; tone: string; meaning: string }> = {
  ALLEGATION: { label: "Allegation", tone: TONES.rose, meaning: "Claimed by someone; not supported by evidence in this workspace." },
  SOURCE_SUPPORTED_OBSERVATION: {
    label: "Source-supported observation",
    tone: TONES.sky,
    meaning: "Stated in cited evidence. The evidence itself may still be wrong.",
  },
  ANALYST_INTERPRETATION: { label: "Analyst interpretation", tone: TONES.violet, meaning: "An analyst's reading of the evidence, not a fact." },
  REVIEWED_FINDING: { label: "Reviewed finding", tone: TONES.emerald, meaning: "A reviewer recorded a decision with a rationale." },
};

export function ClaimBadge({ status }: { status: string }) {
  const c = CLAIM_LABELS[status] ?? { label: status, tone: TONES.slate, meaning: "" };
  return (
    <Pill tone={c.tone} title={c.meaning}>
      {c.label}
    </Pill>
  );
}

export function OutcomeBadge({ outcome }: { outcome: string }) {
  if (outcome === "MATCH") return <Pill tone={TONES.cyan} title="Conditions met: a reason to review, not a finding.">Match - review</Pill>;
  if (outcome === "NO_MATCH") return <Pill tone={TONES.slate} title="Conditions not met on supplied data. Not a clearance.">No match - not a clearance</Pill>;
  return <Pill tone={TONES.amber} title="Required fields were not supplied. Not cleared.">Insufficient data</Pill>;
}

const STATE_LABEL: Record<string, string> = {
  NEW: "New",
  NEEDS_EVIDENCE: "Needs evidence",
  UNDER_REVIEW: "Under review",
  ESCALATED_FOR_REVIEW: "Escalated for review",
  EXPLAINED_NO_FURTHER_ACTION: "Explained / no further action",
  CLOSED: "Closed",
};
export function stateLabel(s: string): string {
  return STATE_LABEL[s] ?? s;
}
export function ReviewStateBadge({ state }: { state: string }) {
  const tone =
    state === "NEW" ? TONES.cyan : state === "NEEDS_EVIDENCE" ? TONES.amber : state === "ESCALATED_FOR_REVIEW" ? TONES.rose : state === "UNDER_REVIEW" ? TONES.sky : TONES.slate;
  return <Pill tone={tone}>{stateLabel(state)}</Pill>;
}

export function PriorityBadge({ priority }: { priority: string }) {
  const tone = priority === "HIGH" ? TONES.rose : priority === "MEDIUM" ? TONES.amber : TONES.slate;
  return (
    <Pill tone={tone} title="Review priority set by the rule. It is not a probability of fraud.">
      {priority.toLowerCase()} priority
    </Pill>
  );
}

export function VerificationBadge({ status }: { status: string }) {
  const tone = status === "VERIFIED" ? TONES.emerald : status === "DISPUTED" || status === "REJECTED" ? TONES.rose : status === "PARTIALLY_VERIFIED" ? TONES.sky : TONES.slate;
  return <Pill tone={tone}>{status.replace(/_/g, " ").toLowerCase()}</Pill>;
}

export function ClassificationBadge({ value }: { value: string }) {
  const tone = value === "RESTRICTED" || value === "CONFIDENTIAL" ? TONES.rose : value === "INTERNAL" ? TONES.violet : TONES.slate;
  return <Pill tone={tone}>{value.toLowerCase()}</Pill>;
}

/** hideSynthetic: the caller already shows SyntheticBadge for the same record. */
export function OriginBadge({ origin, hideSynthetic = false }: { origin: string; hideSynthetic?: boolean }) {
  if (hideSynthetic && origin === "SYNTHETIC") return null;
  const map: Record<string, [string, string]> = {
    SYNTHETIC: ["Synthetic fixture", TONES.amber],
    PUBLIC_SOURCE: ["Public source", TONES.sky],
    INTERNAL_RECORD: ["Internal record", TONES.violet],
    ANALYST_ENTERED: ["Analyst entered", TONES.slate],
  };
  const [label, tone] = map[origin] ?? [origin, TONES.slate];
  return <Pill tone={tone}>{label}</Pill>;
}

export function RuleStatusBadge({ status }: { status: string }) {
  const tone = status === "ACTIVE" ? TONES.emerald : status === "PENDING_APPROVAL" ? TONES.amber : status === "REJECTED" ? TONES.rose : TONES.slate;
  return <Pill tone={tone}>{status.replace(/_/g, " ").toLowerCase()}</Pill>;
}

export function IllustrativeBadge({ illustrative }: { illustrative: boolean }) {
  if (!illustrative) return null;
  return (
    <Pill tone={TONES.violet} title="Investigative check shipped as an example. Not derived from any verified incident.">
      Illustrative template
    </Pill>
  );
}

export function RelationshipStatusBadge({ status }: { status: string }) {
  const tone = status === "CONFIRMED" ? TONES.emerald : status === "CANDIDATE" ? TONES.amber : TONES.slate;
  return <Pill tone={tone}>{status === "CANDIDATE" ? "candidate - needs review" : status.toLowerCase()}</Pill>;
}

export function LabelLegend() {
  return (
    <dl className="grid gap-2 text-sm sm:grid-cols-2">
      <div className="flex gap-2">
        <dt>
          <SyntheticBadge synthetic />
        </dt>
        <dd className="muted">Fixture made for demonstration; not a real record.</dd>
      </div>
      {Object.entries(CLAIM_LABELS).map(([k, v]) => (
        <div key={k} className="flex gap-2">
          <dt>
            <ClaimBadge status={k} />
          </dt>
          <dd className="muted">{v.meaning}</dd>
        </div>
      ))}
    </dl>
  );
}
