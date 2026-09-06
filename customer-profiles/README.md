# Customer Profiles — Privacy-First Framework

This folder defines the ClearGlass Inc. customer-profile intake framework.

## Critical rule

Do **not** commit real customer personal information, passwords, identity documents, payment details, health information, private financial data, or sensitive attributes to this repository.

This folder is for governance templates, schema definitions, consent wording, and sanitized examples only. Real customer records must be stored only in an approved private system with access control, encryption, audit logging, retention controls, and deletion workflow.

## Purpose

The customer-profile process exists to collect only the minimum information needed to provide a requested ClearGlass Inc. service.

## Information requested

Required fields should be limited to:

- Service requested
- Customer name or business name
- Preferred contact method
- Contact detail for the selected method
- Consent confirmation
- Date/time of consent
- Intake version used

Optional fields must be clearly marked optional, such as:

- Company website
- Role/title
- Project goals
- Preferred meeting window
- Notes supplied directly by the customer

Never infer sensitive attributes. Never request passwords. Never request government ID, banking data, medical information, precise home address, or other high-risk personal data unless a documented legal and operational requirement exists.

## Required pre-collection disclosure

Before collecting any personal data, the assistant or intake flow must clearly explain:

1. What information is being requested.
2. Why it is needed.
3. How it will be used.
4. How long it will be retained.
5. Whether it will be shared with third parties.
6. How the customer can decline, withdraw consent, or request deletion.

Explicit consent is required before proceeding.

## Use of information

Customer information may be used only to:

- Respond to the customer's request
- Deliver the requested service
- Schedule and manage service communication
- Maintain necessary business records
- Honour deletion, correction, or consent-withdrawal requests

It must not be used for unrelated marketing, profiling, resale, enrichment, or automated decision-making without separate notice and consent.

## Retention baseline

Default retention: retain active service-intake records only while needed to deliver the service, then delete or anonymize within **12 months after the last customer interaction**, unless a shorter period is requested or a longer legal/business retention obligation applies.

Consent and deletion-request logs may be retained as compliance evidence for up to **24 months**, unless legal obligations require otherwise.

## Third-party sharing

Do not share customer information with third parties except:

- Service providers required to deliver the requested service
- Systems clearly identified in the privacy notice
- Legal or compliance obligations

Any third-party sharing must be disclosed before collection where reasonably possible.

## Decline, withdrawal, and deletion

Customers must be told they can:

- Decline optional fields
- Stop the intake process
- Withdraw consent
- Request correction
- Request deletion, subject to legal retention limits

Default privacy contact: `privacy@clearglassinc.com`

Default policy link: `https://www.clearglassinc.com/privacy.html`

Update these values if the official privacy address or policy URL changes.

## Files in this folder

- `privacy-notice-template.md` — customer-facing notice before collection
- `intake-checklist.md` — operational checklist for safe intake
- `customer-profile.schema.json` — minimal profile schema for validation
- `customer-profile.example.json` — sanitized example only
- `deletion-request-template.md` — request-handling template
- `.gitignore` — blocks accidental commits of local customer data exports
