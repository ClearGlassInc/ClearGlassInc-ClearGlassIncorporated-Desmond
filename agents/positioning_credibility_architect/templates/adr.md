# ADR-NNN: <short decision title>

- **Status:** proposed | accepted | superseded by ADR-NNN | deprecated
- **Date:** YYYY-MM-DD
- **Deciders:** <roles>
- **Provenance:** shipped | designed

## Context

The forces in play: constraints, requirements, scale targets, regulatory or
governance obligations, and what is already true about the system. State the
invariant this decision must not break.

## Decision

One decision, stated in the active voice. "We will …"

## Alternatives considered

| Option | Why it was credible | Why it was not chosen |
|--------|--------------------|----------------------|
| | | |
| | | |

## Consequences

**Positive:** what this buys, quantified where possible.

**Negative:** what this costs — operational burden, coupling, lock-in, latency,
complexity.

**Neutral:** what changes without being better or worse.

## Failure modes

1. What breaks first, under what condition, detected how.
2. What breaks at scale, at what threshold.
3. What breaks on partial failure of a dependency.

## Rollback

The specific path back, and the point after which rollback stops being cheap.

## Verification

The test, gate, or telemetry that proves this decision is still holding in
production. An ADR without a verification hook decays into folklore.
