# Human Approval-Gate Model

Automation should stop at a defined gate whenever an action is consequential, irreversible, externally visible, or outside its approved scope.

## Gate record

- Proposed action:
- Automation owner:
- Human approver:
- Risk tier:
- Systems affected:
- Data affected:
- Expected evidence:
- Failure condition:
- Rollback/recovery:
- Approval decision: `APPROVED` / `REJECTED` / `NOT VERIFIED`
- Decision timestamp:
- Evidence reference:

## Gate rules

1. No approval may be inferred from silence.
2. Approval must identify the specific action and scope.
3. High-impact actions require explicit human approval before execution.
4. Failed or missing evidence results in `NOT VERIFIED`.
5. A new material scope requires a new approval decision.
6. Approval does not authorize unrelated changes.
