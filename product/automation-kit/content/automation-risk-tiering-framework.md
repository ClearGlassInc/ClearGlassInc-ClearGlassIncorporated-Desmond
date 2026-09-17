# Automation Risk-Tiering Framework

Use risk tiers to determine the amount of human review and evidence required. This is a planning framework, not a professional risk assessment or certification.

## Tier 1 — Low operational impact

Typical characteristics:
- Reversible
- Limited data sensitivity
- Low consequence of an incorrect output
- Human review remains practical

Minimum controls:
- Named owner
- Basic test evidence
- Change record
- Rollback documented

## Tier 2 — Material operational impact

Typical characteristics:
- Recurring business process
- Multiple systems or dependencies
- Material effect on staff, customers, or operations
- More significant data or access requirements

Minimum controls:
- Named owner and reviewer
- Documented approval gate
- Test cases and failure handling
- Evidence retention
- Recovery/rollback procedure
- Periodic review

## Tier 3 — High-impact or sensitive

Typical characteristics:
- Sensitive data
- High operational consequence
- Difficult-to-reverse action
- Significant external dependency
- High-impact decision support

Minimum controls:
- Explicit accountable owner
- Explicit human approval before consequential action
- Least-privilege access
- Strong evidence/provenance
- Defined escalation path
- Recovery plan
- Security/privacy review by appropriately qualified professionals where applicable

## Out of scope for autonomous execution

Do not use this kit as authorization for autonomous financial/trading/payment, hiring/firing, medical, legal, law-enforcement, or other high-impact decisions.
