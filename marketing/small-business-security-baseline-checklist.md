# Small-Business Security Baseline Checklist

**ClearGlass Inc. · Burlington, Ontario · Draft educational asset**  
**Use:** A self-check for business owners and operations leads. This checklist does not inspect your systems and is not an audit, certification, penetration test, or legal opinion.

## Identity and access

- [ ] Require multi-factor authentication for business email and administrative accounts.
- [ ] Review administrator accounts and remove access that is no longer required.
- [ ] Use unique accounts for each person; do not share administrator credentials.
- [ ] Confirm onboarding, role changes and offboarding include access review.
- [ ] Record who owns each critical account and recovery method.

## Email and domain protection

- [ ] Confirm SPF, DKIM and DMARC are configured and monitored for business domains.
- [ ] Train staff to verify unexpected payment, credential and document requests through a second channel.
- [ ] Review external forwarding rules and unusual mailbox access using authorized administrative tools.
- [ ] Make a clear process for reporting suspicious messages.

## Devices and software

- [ ] Keep operating systems, browsers and business applications supported and updated.
- [ ] Enable endpoint protection and confirm alerts reach a responsible person.
- [ ] Encrypt portable devices where available and use screen locks.
- [ ] Remove unmanaged or unused accounts and software where practical.

## Data and recovery

- [ ] Know where important business and client data is stored.
- [ ] Limit access to sensitive files by role and business need.
- [ ] Maintain backups appropriate to business needs; test restoration, not just backup completion.
- [ ] Document how to recover access if the primary administrator is unavailable.
- [ ] Set a retention and secure-disposal practice for records the business no longer needs.

## Incident readiness

- [ ] Name the person who coordinates a security incident and the alternate contact.
- [ ] Keep a simple incident reporting path available to staff.
- [ ] Preserve relevant logs and evidence during an incident; do not delete or alter records casually.
- [ ] Know when to contact qualified incident-response support and legal/privacy advisers.
- [ ] Practice one recovery scenario and record lessons learned.

## What to do with the results

For every item, mark one of the following based on what you actually know:

- **Verified:** you checked current evidence and it supports the control.
- **Not verified:** you do not yet have enough evidence.
- **Needs improvement:** evidence shows the control is missing or inadequate.
- **Not applicable:** record the reason.

Do not label a control “verified” merely because someone believes it is probably in place. Missing evidence is not proof of a failure, but it is a reason to investigate.

## Suggested priority method

For each not-verified or needs-improvement item, record:
1. Potential business impact.
2. Evidence that supports the concern.
3. The smallest practical next action.
4. The person responsible.
5. A review date.

Start with exposed privileged access, business email, recovery and backup readiness. Priorities depend on your actual environment and risk tolerance.

## Important boundary

This is a general educational aid, not a substitute for an organization-specific assessment. Do not send passwords, API keys, personal health information, payment-card data, incident evidence, or confidential client records to ClearGlass through public forms or social media.

For Canadian baseline guidance, review the [Canadian Centre for Cyber Security’s Baseline Cyber Security Controls for Small and Medium Organizations](https://www.cyber.gc.ca/en/guidance/baseline-cyber-security-controls-small-and-medium-organizations).

For an Ontario organization that wants a scoped, read-only review with a written report and ranked next steps, see the [ClearGlass Security Quick-Audit](https://www.clearglassinc.com/offers/security-quick-audit.html). Review the service scope and exclusions before buying.
