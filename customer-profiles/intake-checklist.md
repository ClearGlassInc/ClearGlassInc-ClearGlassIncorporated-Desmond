# Customer Profile Intake Checklist

Use this checklist before creating or updating any customer profile.

## 1. Pre-collection disclosure

Confirm the customer has been shown the current privacy notice covering:

- Information requested
- Why it is needed
- How it will be used
- Retention period
- Third-party sharing
- Decline, withdrawal, correction, and deletion rights
- Privacy contact and policy link

## 2. Explicit consent gate

Do not collect profile information until the customer gives explicit consent.

Minimum consent record:

- Consent answer: `yes` or `no`
- Notice version shown
- Date/time of consent
- Collection method
- Identity of system or staff member collecting the data

If consent is `no`, stop intake and collect no personal data except a minimal operational note that consent was declined, where necessary.

## 3. Data minimization check

Before asking each question, verify that it is necessary for the requested service.

Approved default fields:

- Name or business name
- Preferred contact method
- Contact detail for selected method
- Service requested
- Customer-supplied project notes
- Consent metadata

Optional fields must be labelled optional.

## 4. Prohibited collection

Do not ask for or store:

- Passwords
- Private keys, seed phrases, API keys, recovery codes, or MFA codes
- Government ID numbers unless legally required
- Banking login credentials
- Credit-card numbers
- Health or medical data
- Precise residential address unless operationally required
- Sensitive attributes such as race, religion, political opinion, union membership, sexual orientation, or disability status

Never infer sensitive attributes from names, photos, locations, writing style, or business context.

## 5. Confirmation before submission

Before saving or submitting a profile, show the customer a plain-language confirmation summary:

- Required information entered
- Optional information entered
- Consent status
- Retention period
- Privacy contact

Ask the customer to confirm the summary is accurate.

## 6. Storage rule

Do not store live customer personal data in GitHub.

Approved locations must provide:

- Private access control
- Encryption in transit
- Encryption at rest where available
- Audit logging
- Role-based access
- Retention/deletion controls
- Backup and recovery controls

## 7. Deletion and withdrawal handling

When a customer requests deletion or withdraws consent:

1. Verify the request through a reasonable low-friction method.
2. Locate all relevant records.
3. Delete or anonymize data unless retention is legally required.
4. Record the request outcome without keeping unnecessary personal data.
5. Confirm completion or explain any lawful retention limitation.

## 8. Review cadence

Review this process every 6 months or whenever privacy law, service scope, vendor stack, or data collection changes.
