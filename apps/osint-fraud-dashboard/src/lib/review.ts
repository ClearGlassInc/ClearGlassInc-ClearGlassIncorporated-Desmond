// Review workflow shared by alerts and investigations.
// "triage" moves are open to analysts; "decide" moves need a reviewer.
// Every move needs a written rationale and is kept as a ReviewDecision row.

export const REVIEW_STATES = [
  "NEW",
  "NEEDS_EVIDENCE",
  "UNDER_REVIEW",
  "ESCALATED_FOR_REVIEW",
  "EXPLAINED_NO_FURTHER_ACTION",
  "CLOSED",
] as const;
export type ReviewStateName = (typeof REVIEW_STATES)[number];
export type TransitionLevel = "triage" | "decide";

const T: Record<ReviewStateName, Partial<Record<ReviewStateName, TransitionLevel>>> = {
  NEW: { NEEDS_EVIDENCE: "triage", UNDER_REVIEW: "triage" },
  NEEDS_EVIDENCE: { UNDER_REVIEW: "triage" },
  UNDER_REVIEW: {
    NEEDS_EVIDENCE: "triage",
    ESCALATED_FOR_REVIEW: "triage",
    EXPLAINED_NO_FURTHER_ACTION: "decide",
    CLOSED: "decide",
  },
  ESCALATED_FOR_REVIEW: {
    UNDER_REVIEW: "decide",
    NEEDS_EVIDENCE: "decide",
    EXPLAINED_NO_FURTHER_ACTION: "decide",
    CLOSED: "decide",
  },
  EXPLAINED_NO_FURTHER_ACTION: { UNDER_REVIEW: "decide", CLOSED: "decide" },
  CLOSED: { UNDER_REVIEW: "decide" },
};

export function transitionLevel(from: ReviewStateName, to: ReviewStateName): TransitionLevel | null {
  return T[from][to] ?? null;
}

export function nextStates(from: ReviewStateName): { to: ReviewStateName; level: TransitionLevel }[] {
  return Object.entries(T[from]).map(([to, level]) => ({ to: to as ReviewStateName, level: level! }));
}

export const MIN_RATIONALE = 10;

export const OPEN_STATES: ReviewStateName[] = ["NEW", "NEEDS_EVIDENCE", "UNDER_REVIEW", "ESCALATED_FOR_REVIEW"];

export function isReviewState(v: string): v is ReviewStateName {
  return (REVIEW_STATES as readonly string[]).includes(v);
}
