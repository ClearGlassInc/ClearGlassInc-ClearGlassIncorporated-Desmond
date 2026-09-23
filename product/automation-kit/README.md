# Governed AI Automation Operating Kit

Internal MVP package. **Not public. Not a marketplace listing. Not a payment product.**

## What this package contains

- Opportunity and workflow discovery templates
- Prioritization and risk-tiering frameworks
- Human approval and governance controls
- Evidence/provenance and security/privacy readiness checklists
- SOP and implementation-readiness templates
- A 30/60/90-day implementation roadmap
- Original illustrative workflows
- A deterministic planning calculator for user-entered assumptions
- Automated provenance and content-policy validation

## Use boundary

This package is for general business-process planning, workflow documentation, automation prioritization, governance, and implementation readiness. It does not provide legal, tax, financial, compliance, security-certification, or custom implementation advice.

Do not treat calculator outputs as forecasts or guarantees. They are planning estimates only.

## Validation

From the repository root, run:

```text
python -m pytest product/automation-kit/tests -v
python product/automation-kit/validation/validate_kit.py
```

The validation report must use evidence-safe statuses: `PASS`, `FAIL`, or `NOT VERIFIED`.

## Release gate

Internal development is authorized. Publication, Etsy listing creation, Stripe objects, checkout activation, payment processing, advertising, customer outreach, invoicing, contracts, and production deployment remain outside this MVP authorization.
