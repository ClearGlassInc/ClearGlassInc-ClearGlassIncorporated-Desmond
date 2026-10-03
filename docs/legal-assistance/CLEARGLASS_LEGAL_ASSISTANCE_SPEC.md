# ClearGlass Legal Assistance — Implementation Specification

**Status:** Approved for free, non-destructive design/prototype work only  
**Date:** 2026-10-03  
**Owner:** ClearGlass Inc.  
**Scope:** Single-user private legal-information assistant for Canada  
**Release state:** NOT DEPLOYED — PAID SERVICES LOCKED — NO PHONE NUMBER PROVISIONED

## 1. Approved operating configuration

| Decision | Requirement |
|---|---|
| Service name | ClearGlass Legal Assistance |
| Access | iPhone/PWA voice access and a new dedicated Canadian telephone number |
| Jurisdiction | Canada-wide legal information, with province/territory identified per matter |
| Case information | Encrypted case vault; client-side encryption for sensitive files and notes |
| Call records | No call recordings and no retained transcripts by default |
| Monthly target | USD $25 maximum planning target; not spending authorization |
| Human escalation | User's existing lawyer plus an independently maintained lawyer-referral directory |
| Authorization | Free, read-only inspection and non-production development only |
| Prohibited without fresh approval | Paid resource creation, number purchase, subscriptions, API billing activation, secret creation, production deployment, external lawyer contact, or disclosure of case material |

The USD $25 figure is a hard budget target, not an instruction to incur charges. The application must enforce a monthly usage ceiling and fail closed when usage cannot be bounded. Any unavoidable recurring charge requires separate explicit approval.

## 2. Product boundary and legal notice

The service provides legal information, issue spotting, document organization, chronology preparation, source-linked legal research, and preparation for conversations with qualified counsel. It is not a lawyer, law firm, paralegal service, legal representative, or substitute for independent legal advice. It does not create a solicitor-client relationship or guarantee solicitor-client privilege.

The assistant must:
- Identify the country, province/territory, court/tribunal, and relevant date before giving procedural information.
- Prefer current official statutes, regulations, court rules, and court decisions; identify source, court, date, and subsequent treatment where available.
- Distinguish binding authority, persuasive authority, legislation, administrative guidance, commentary, and AI-generated analysis.
- Never invent cases, citations, deadlines, legal tests, or procedural requirements.
- Flag limitation periods, service dates, filing deadlines, criminal charges, immigration deadlines, injunctions, eviction, family violence, detention, and imminent hearings for prompt human-lawyer review.
- Never file documents, contact opposing parties, negotiate, make admissions, or contact counsel without a separate user instruction and review.
- Display a clear emergency instruction: the hotline is not an emergency service; call 911 for immediate danger and contact a licensed lawyer for urgent legal advice.

## 3. Access architecture

### A. iPhone access
Build a private, responsive Progressive Web App (PWA) that can be added to the iPhone Home Screen. It provides authenticated voice sessions, a secure case-vault interface, source-linked research, and lawyer contact shortcuts.

The PWA is the app's mobile channel. Existing ChatGPT voice may be used separately as a manual fallback, but it is not the same authenticated application session and must not be represented as directly connected to the private case vault.

### B. Dedicated telephone access
Provision a new Canadian local number only after explicit purchase approval. Preferred design: Canadian SIP-capable number and SIP trunk (Twilio is the candidate provider, subject to account, number availability, contractual, privacy, and pricing review).

Incoming call flow:
1. Caller dials the assigned Canadian number.
2. Provider sends a signed incoming-call event to a dedicated server-side call controller.
3. Controller validates provider signature, destination number, call state, and configured allowlist.
4. Controller requests/accepts a GPT-Live SIP session with fixed legal-assistant instructions and restricted tools.
5. The voice assistant gives the AI/legal-information disclosure and asks the caller not to share highly sensitive details until the data-processing notice is accepted.
6. Caller authentication uses a separate PIN or stronger challenge; caller ID alone is not authentication.
7. Session ends on caller request, timeout, budget limit, failed authentication, or safety escalation.

The call controller must not accept arbitrary destinations, arbitrary SIP URIs, caller-supplied model IDs, or arbitrary tool execution.

### C. Voice model and SIP
Use GPT-Live with SIP as the initial candidate because OpenAI documents SIP connectivity and per-second voice-session billing. The application backend retains session control and private tool execution. The existing ClearGlass AI proxy is not currently a Realtime/SIP gateway and must not be assumed to support this flow without new implementation and testing.

## 4. Data protection model

### A. Data classes
- **Class 0 — Public:** statutes, public judgments, public court forms, published guidance.
- **Class 1 — Operational metadata:** random case ID, event timestamp, access outcome, application version. Avoid names, telephone numbers, prompts, filenames, and case subjects.
- **Class 2 — Confidential case content:** notes, correspondence, pleadings, contracts, identity data, evidence, and documents. Encrypt before upload.
- **Class 3 — Highly sensitive:** criminal, family, health, immigration, financial, child-protection, or safety information. Do not send to an AI provider unless the user specifically authorizes the exact processing and the privacy/data-retention gate is passed.

### B. Case-vault cryptography
- Encrypt document and note content client-side using AES-256-GCM with a fresh nonce per encryption operation.
- Use per-case data-encryption keys (DEKs); wrap DEKs with a separately managed key-encryption key (KEK).
- Derive user unlock material with a modern memory-hard KDF (Argon2id) and store no plaintext password or key.
- Provide a user-controlled recovery-key workflow and tested recovery procedure.
- Keep key material out of browser local storage, logs, URLs, analytics, source control, and database plaintext.
- Encrypt backups and verify restoration before production.
- Use TLS 1.2+ in transit, MFA, short-lived sessions, device/session revocation, rate limits, and least-privilege authorization.
- Apply row-level access controls as defense in depth. A single-user release must still enforce ownership checks on every object and endpoint.
- Do not index confidential plaintext. Search should run client-side after authorized decryption.

Cryptographic implementation and key custody require independent security review. AES-256-GCM and client-side encryption are design requirements, not a claim that encryption has already been implemented or audited.

### C. No-recording / no-transcript rule
- Disable telephony recording, transcription products, voicemail capture, session storage, and transcript persistence.
- Do not write raw audio, transcript text, prompts, model responses, documents, or caller phone numbers to application logs.
- Keep live audio/session state in memory only as needed for the call and discard it on session closure.
- Retain only minimal security metadata with a short, documented retention period, and disclose that metadata separately.
- If a provider's default abuse-monitoring or operational retention may contain content, disclose it before the caller shares case details. ClearGlass's no-transcript policy does not override third-party provider retention.

### D. Critical third-party processing limitation
OpenAI's published API data controls state that abuse-monitoring logs may contain prompts and responses and are ordinarily retained for up to 30 days unless the organization has approved Modified Abuse Monitoring or Zero Data Retention. GPT-Live sessions are documented as ZDR-eligible, but eligibility is not the same as approval. OpenAI's current data-controls documentation describes GPT-Live data residency for the United States and Europe, not Canada.

Therefore:
- Do not promise that telephone audio or AI processing remains in Canada.
- Do not submit full case files, privileged communications, or highly sensitive evidence to the voice model by default.
- Before production voice launch, obtain a written privacy/data-flow review, verify the exact endpoint/model retention controls available to the account, seek ZDR approval if required, and disclose processing geography and subprocessors.
- If Canadian-only processing is a mandatory requirement, the current OpenAI voice design is a blocker until a compliant Canada-resident processing option is independently verified.
- The encrypted case vault may be hosted in Canada while AI voice processing occurs elsewhere; these are separate data flows and must never be conflated.

## 5. Canadian legal research

The application must use jurisdiction-aware source adapters. Initial authoritative sources:
- Federal legislation: https://laws-lois.justice.gc.ca/
- Ontario e-Laws: https://www.ontario.ca/laws
- Supreme Court of Canada: https://www.scc-csc.ca/
- Ontario Courts: https://www.ontariocourts.ca/
- CanLII: https://www.canlii.org/ (subject to its current access terms; do not scrape or assume API access)
- Federation of Law Societies of Canada: https://flsc.ca/
- Law Society of Ontario: https://lso.ca/

For nationwide coverage, add province/territory-specific official legislation and court sources. Identify the relevant law society or official lawyer referral service for each jurisdiction. The user's existing lawyer's contact details are entered by the user and stored only with their authorization.

Privacy-law mapping must be assessed for the actual operator, service model, data flows, and jurisdictions. PIPEDA and substantially similar provincial private-sector laws may apply differently; do not claim that one federal statute alone governs every case.

## 6. Proposed technology layout

| Layer | Candidate | Required control |
|---|---|---|
| Mobile UI | Next.js PWA, isolated app path | MFA, CSP, no sensitive browser telemetry |
| Telephone | Twilio Canadian SIP number/trunk | Signed webhooks, allowlisted destination, no recording |
| Voice | OpenAI GPT-Live SIP | Explicit disclosure, store=false, usage cap, retention gate |
| Call controller | Separate server-side service/Worker | Webhook verification, authentication, session close |
| Case vault | Supabase Canada Central or verified Canada-resident alternative | Client-side encryption, RLS, encrypted backup |
| Key custody | Client-held recovery key + managed KEK when approved | Separation of duties, rotation, recovery tests |
| Legal research | Official Canadian sources + CanLII subject to terms | Source/date/court citations, no invented citations |
| Hosting | Existing Cloudflare/other account only after read-only account and region review | No paid plan or production deployment without approval |

Supabase has a specific Canada Central region (ca-central-1). Region selection locates the primary project data; it does not prove that every support, telemetry, backup, subprocessors, or AI processing operation remains in Canada. The connected Supabase organization currently has no projects, so no database or vault has been created.

## 7. Repository inspection findings (2026-10-03)

Repository: ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond  
Observed main commit: c744200c1682ab187e05045b234d37b97a73df6f  
Repository default branch: main

Existing clearglass-ai-proxy/:
- Cloudflare Worker; zero runtime dependencies.
- Authenticated, rate-limited, request-validating gateway.
- Current routes are /health, /v1/chat/completions, /v1/models, and /v1/embeddings.
- It does not implement the GPT-Live SIP call controller or Realtime session lifecycle.
- It logs allowlisted operational metadata and hashed identifiers; it is not a call-recording/transcript store.
- wrangler.toml enables observability. Review actual log settings/retention and remove or restrict any logging inconsistent with the no-content-retention policy before any legal-assistance production use.
- Its tests are documented in the README; tests have not been run as part of this read-only inspection.

Existing render.yaml provisions paid Starter services and an Oregon region. Do not reuse it for this service or for confidential Canadian case data.

Observed connected platform state:
- Supabase organization exists on the Free plan; zero projects returned.
- Vercel team listing returned no teams.
- No connected Twilio account/integration was identified in the available connected integrations.
- No production legal-assistance service, number, database, or secrets were provisioned.
- GitHub Actions status in repository documentation has a known runner-dispatch problem. Do not treat workflow checks as valid verification until runner execution is observed.
- main branch protection was reported disabled by GitHub metadata. Do not push directly to main; keep all work on a dedicated feature branch and require manual review.

## 8. Cost model and USD $25 guardrail

Current published reference prices observed 2026-10-03:
- Twilio Canada Elastic SIP Trunking: local number listed at $0.75/month and local origination at $0.0045/minute (confirm the exact number type, destination, and taxes before purchase).
- Twilio Programmable Voice alternative: local number $1.15/month and inbound local calls $0.0085/minute.
- OpenAI GPT-Live 1: $0.05 per active session minute, billed per second; backend model and tool use is separate.
- Supabase Pro: $25/month before optional compute/usage; this alone consumes the entire target budget. The existing Free organization may support a non-production prototype, but Free-tier suitability, backups, availability, and terms must be reviewed before any real case data is stored.
- Cloudflare Workers Free has limited free usage; current published limits and logs retention must be rechecked before deployment.

Illustrative SIP + GPT-Live cost before backend model/tool use, tax, and optional services:
- Fixed number: $0.75/month
- Per active minute: $0.0045 + $0.05 = $0.0545
- 100 minutes: approximately $6.20/month
- 300 minutes: approximately $17.10/month
- 400 minutes: approximately $22.55/month

These are arithmetic illustrations, not quotes or guaranteed total costs. The $25 ceiling must include backend model/tool usage, hosting, taxes, and all provider fees. The app must maintain a conservative internal usage ledger, stop new calls before the budget is exceeded, and display the remaining allowance. Provider spending alerts are not a hard spending cap. No paid project, API key, number, or subscription may be created without a new explicit approval.

## 9. Delivery phases and acceptance gates

### Phase 0 — Free inspection and specification (authorized)
- Read-only repository and integration inspection.
- Record current baseline and dependencies.
- Prepare this implementation specification.
- No paid resources, production secrets, or deployments.

### Phase 1 — Local-only prototype (free)
- Add an isolated clearglass-legal-assistance/ app directory on a feature branch.
- Use mock telephony and mock AI responses only.
- Implement PWA shell, legal notice, jurisdiction selector, non-sensitive mock case records, and no-retention call-state interface.
- Implement client-side encryption proof-of-concept with test fixtures only.
- No real user case data, no real API calls, no provider keys.
- Run unit tests and static checks locally; report exact commands/results.

### Phase 2 — Security and privacy review (no launch)
- Threat model, data-flow map, privacy impact assessment, encryption review, key recovery test, access-control test, dependency audit, and retention review.
- Verify OpenAI retention eligibility and regional processing limits in writing.
- Confirm provider contracts, subprocessors, cross-border transfers, breach handling, and applicable Canadian privacy obligations.
- Obtain qualified Canadian legal/privacy counsel review.

### Phase 3 — Paid pilot (requires separate written approval)
- Confirm organization/account, exact costs, selected Canadian number, and monthly hard cap.
- Create a separate project and scoped credentials.
- Configure Twilio SIP and GPT-Live session webhooks.
- Test with synthetic data only.
- No automatic billing increases.

### Phase 4 — Production (requires separate written approval)
- Independent security sign-off.
- Confirm lawyer escalation contact and referral sources.
- Confirm privacy notices, consent, retention, terms, and data-processing agreements.
- Enable production only after all critical gates pass.

### Mandatory release blockers
- No verified Canada-only processing path for AI voice.
- No ZDR/MAM approval status verified.
- No Twilio account or Canadian number provisioned.
- No Supabase project or vault created.
- No independent security/privacy review.
- GitHub Actions runner issue means CI evidence is currently unreliable.
- No lawyer referral list verified for every province/territory.

## 10. Definition of done

A production release is not complete until:
1. iPhone PWA and dedicated Canadian number both authenticate securely.
2. No recordings or transcript persistence are enabled in the application or telephone provider.
3. Provider-side retention and geographic processing are disclosed accurately.
4. Case files are encrypted before leaving the client device and keys are not stored with ciphertext.
5. Authorization, case isolation, key recovery, revocation, backup restore, rate-limit, and cost-cap tests pass.
6. Legal research returns traceable primary sources and clearly flags uncertainty.
7. Human lawyer escalation is tested and never misrepresented as AI representation.
8. Independent security and privacy review signs off.
9. Owner explicitly authorizes paid pilot and production release.

## 11. Approval ledger

| Action | Current state |
|---|---|
| Read-only GitHub/Supabase/Vercel inspection | Authorized and performed |
| Create this specification on an isolated feature branch | Authorized |
| Local mock-only prototype | Authorized in principle; no real data or provider use |
| Supabase project creation | Not authorized |
| Twilio account/number purchase | Not authorized |
| OpenAI API key creation or billing activation | Not authorized |
| Cloudflare paid plan / Render / Vercel paid resources | Not authorized |
| Real case data processing | Not authorized |
| Production deployment or external lawyer contact | Not authorized |

**Operating rule:** If a task requires money, production credentials, live customer/case information, external communication, or a change to main, stop and obtain a separate explicit approval.
