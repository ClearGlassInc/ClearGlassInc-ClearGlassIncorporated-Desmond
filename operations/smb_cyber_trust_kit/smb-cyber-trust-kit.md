# ClearGlass SMB Cyber Trust Kit

*Version 1.0.0 · prepared for [Your Business Name] · 2026-06-20 09:36 UTC*

A plain-language cyber resilience starter pack for small and medium businesses. Four pieces: policy templates, a risk heat-map, an incident communication script, and a guide to talking about cyber risk without jargon. Edit anything in `[brackets]` or `{braces}`.

> Practical guidance, not legal advice. For PIPEDA / PHIPA breach obligations, confirm specifics with a qualified advisor.

## 1. Simple Policy Templates

### Acceptable Use Policy

**Purpose.** Set clear, fair rules for using company devices, accounts, and data.

**Who it covers.** Everyone who uses [Your Business Name] systems: staff, contractors, and volunteers.

**The rules.**
1. Use company accounts and devices for work purposes; keep reasonable personal use lawful and minimal.
2. Do not install unapproved software or plug in unknown USB drives.
3. Do not share your login with anyone, including co-workers.
4. Lock your screen when you step away.
5. Report anything that looks suspicious — no blame for a fast report.

**Owner:** Owner / Office Manager  
**Review:** Annually, or after a major change

### Password & Multi-Factor Authentication Policy

**Purpose.** Keep accounts hard to break into, even if a password leaks.

**Who it covers.** All [Your Business Name] accounts: email, banking, cloud apps, and admin logins.

**The rules.**
1. Use a unique passphrase of 12+ characters for every account.
2. Use the company password manager — never a sticky note or a shared spreadsheet.
3. Turn on multi-factor authentication (MFA) on every account that offers it, especially email and banking.
4. Never approve an MFA prompt you did not start.
5. Change a password immediately if you suspect it was exposed.

**Owner:** Owner / IT Lead  
**Review:** Annually

### Data Protection & Privacy Policy

**Purpose.** Protect customer and staff information and meet privacy obligations.

**Who it covers.** All personal and sensitive data [Your Business Name] collects, stores, or shares.

**The rules.**
1. Collect only the information you actually need.
2. Store sensitive data in approved systems — not personal email or personal cloud drives.
3. Encrypt laptops, phones, and backups.
4. Share sensitive data only over approved, protected channels.
5. Delete data you no longer need on a defined schedule.
6. Know your obligations under PIPEDA (and PHIPA for health data).

**Owner:** Owner / Privacy Lead  
**Review:** Annually, or after a process change

### Incident Response Policy

**Purpose.** Make sure everyone knows what to do in the first hour of an incident.

**Who it covers.** Any suspected breach, ransomware, lost device, or account takeover.

**The rules.**
1. If you suspect an incident, report it to [Incident Lead — name & number] immediately — speed beats certainty.
2. Do not turn the device off or 'clean it up' — preserve evidence.
3. The incident lead decides on containment (disconnect, reset passwords, isolate).
4. Follow the Communication During Incidents script for who to tell and when.
5. Write down what happened and when — a simple timeline is enough.
6. Hold a short blameless review within a week to fix root causes.

**Owner:** Owner / Incident Lead  
**Review:** Annually, plus after every incident

### Access Control (Joiners, Movers, Leavers) Policy

**Purpose.** Give people the access they need — and remove it the day they leave.

**Who it covers.** All accounts and physical access across [Your Business Name].

**The rules.**
1. Grant the least access needed to do the job.
2. Set up new-starter access from a checklist on day one.
3. Review access when someone changes role.
4. Remove all access the same day someone leaves — accounts, devices, building keys, and shared passwords.
5. Review who has admin rights every quarter.

**Owner:** Owner / Office Manager  
**Review:** Quarterly access review

### Backup & Recovery Policy

**Purpose.** Be able to get back to work quickly after loss, theft, or ransomware.

**Who it covers.** All business-critical data, files, and systems.

**The rules.**
1. Follow 3-2-1: three copies, on two types of media, one off-site.
2. Automate backups daily for anything you cannot afford to retype.
3. Keep at least one backup offline or otherwise out of reach of ransomware.
4. Test a real restore at least quarterly — an untested backup is a guess.
5. Know your target recovery time for the systems that matter most.

**Owner:** Owner / IT Lead  
**Review:** Quarterly restore test

### Vendor & Third-Party Risk Policy

**Purpose.** Make sure the suppliers you trust do not become your weak point.

**Who it covers.** Any vendor with access to [Your Business Name] data, systems, or accounts.

**The rules.**
1. Keep a simple list of vendors and what each can access.
2. Ask new vendors how they protect your data before you sign.
3. Give vendors the least access they need, and remove it when the work ends.
4. Require vendors to tell you promptly if they have a breach.
5. Review the vendor list once a year.

**Owner:** Owner  
**Review:** Annually

### Device & Bring-Your-Own-Device (BYOD) Policy

**Purpose.** Keep work data safe on the phones and laptops people actually use.

**Who it covers.** Company and personal devices used for [Your Business Name] work.

**The rules.**
1. Protect every device with a passcode or biometric lock.
2. Keep operating systems and apps updated.
3. Encrypt devices that hold work data.
4. Enable remote-wipe for lost or stolen devices.
5. Report a lost or stolen device immediately so access can be cut.

**Owner:** Owner / IT Lead  
**Review:** Annually

## 2. Risk Heat-Map Template

Score each risk: **Likelihood (1-5) x Impact (1-5)**. The cell colour is the band; cells list the starter risks placed on the map.

| Impact \ Likelihood | 1 Rare | 2 Unlikely | 3 Possible | 4 Likely | 5 Almost certain |
|---|---|---|---|---|---|
| **5** | 5 M | 10 H | 15 H · R2,R6 | 20 C · R4 | 25 C |
| **4** | 4 L | 8 M · R10 | 12 H · R8 | 16 C · R1,R3 | 20 C |
| **3** | 3 L | 6 M · R11 | 9 M · R5,R9 | 12 H · R7,R12 | 15 H |
| **2** | 2 L | 4 L | 6 M | 8 M | 10 H |
| **1** | 1 L | 2 L | 3 L | 4 L | 5 M |

**Bands.**  
- **Low** (1-4): Accept and monitor. Review at the normal cadence.  
- **Moderate** (5-9): Plan a fix. Assign an owner and a target date this quarter.  
- **High** (10-15): Act soon. Put a control in place within 30 days.  
- **Critical** (16-25): Act now. Escalate to the owner today; treat as a priority.

**Starter risk register** (edit the numbers for your business):

- **R1 Phishing / business email compromise** (People) — L4 x I4 = 16 (Critical). Most common entry point. Fake invoice or 'CEO' wire request.
- **R2 Ransomware locks files / servers** (Systems) — L3 x I5 = 15 (High). Often arrives via phishing or an unpatched remote login.
- **R3 Stolen or reused passwords** (Identity) — L4 x I4 = 16 (Critical). One leaked password unlocks email, banking, and cloud apps.
- **R4 No multi-factor authentication (MFA)** (Identity) — L4 x I5 = 20 (Critical). Without MFA, a stolen password is a full account takeover.
- **R5 Lost or stolen laptop / phone** (Devices) — L3 x I3 = 9 (Moderate). Unencrypted device = the data on it is gone with the device.
- **R6 No tested backups** (Recovery) — L3 x I5 = 15 (High). A backup you have never restored is a guess, not a safety net.
- **R7 Unpatched software / overdue updates** (Systems) — L4 x I3 = 12 (High). Known holes get exploited within days of a patch release.
- **R8 Ex-employee access not removed** (Identity) — L3 x I4 = 12 (High). Accounts that outlive the job are a quiet, standing risk.
- **R9 Sensitive data emailed in the clear** (Data) — L3 x I3 = 9 (Moderate). Client PII / health info sent unprotected can trigger reporting.
- **R10 Vendor / supplier breach reaches you** (Third-party) — L2 x I4 = 8 (Moderate). Their access and their breach become your incident.
- **R11 Website / customer portal defaced or down** (Systems) — L2 x I3 = 6 (Moderate). Reputation and revenue both take the hit when it is public.
- **R12 Staff unsure who to call in an incident** (People) — L4 x I3 = 12 (High). Minutes lost in confusion are the most expensive minutes.

## 3. Communication During Incidents Script

**Principles.**
- Be first, be honest, be brief — silence reads as a cover-up.
- Say what you know, what you don't yet know, and when you'll update next.
- One approved spokesperson. Everyone else routes questions to them.
- Never speculate on cause, numbers, or blame before the facts are in.
- Write a timeline as you go — it protects you and speeds the review.
- Tell people what to DO (the action) before why it happened.

Fill the `{placeholders}` at go-time. Keep one approved spokesperson.

#### Internal staff — contain (Internal chat / all-hands)
*When to use:* First message to the team once an incident is confirmed.  
*Approver:* Incident Lead

> Team — we are responding to a security incident affecting {systems_affected}. Please {staff_action} now. Do not discuss this outside the company or post about it. Direct all questions to {incident_contact}. Next update by {next_update_time}.

#### Internal staff — recover (Internal chat / all-hands)
*When to use:* When systems are restored and normal work resumes.  
*Approver:* Incident Lead

> Update — the incident affecting {systems_affected} is resolved and systems are back to normal as of {resolved_time}. Thank you for your patience. If you notice anything unusual, tell {incident_contact}. A short review follows so we come out stronger.

#### Customers — contain (Email / status page)
*When to use:* Early, honest notice while you are still responding.  
*Approver:* Owner

> We are writing to let you know we identified a security issue on {date} affecting {systems_affected}. We acted quickly to contain it and are investigating with care. {customer_impact_statement} We will share another update by {next_update_time}. Questions: {support_contact}.

#### Customers — recover (Email / status page)
*When to use:* Closing the loop once service is restored.  
*Approver:* Owner

> Update on the {date} security issue: it is now resolved. {what_we_did} {what_we_changed} We take the trust you place in us seriously and are sorry for any disruption. Questions: {support_contact}.

#### Affected individuals — post-incident (Email / letter)
*When to use:* If personal information was exposed (PIPEDA / PHIPA may require notice).  
*Approver:* Owner + Privacy Lead (consider legal review)

> We are notifying you that a security incident on {date} may have exposed the following information about you: {data_categories}. Here is what happened, what we have done, and steps you can take: {protective_steps}. We have reported this as required. For help, contact {privacy_contact}.

#### Privacy regulator — post-incident (Official form / letter)
*When to use:* Report to the Privacy Commissioner when a breach poses real risk of significant harm (PIPEDA) or per PHIPA for health information.  
*Approver:* Owner + Privacy Lead (legal review recommended)

> Organization: {org}. Date of incident: {date}. Nature of breach: {breach_nature}. Personal information involved: {data_categories}. Estimated individuals affected: {affected_count}. Containment and remediation: {remediation}. Notification to individuals: {notice_status}. Contact: {privacy_contact}.

#### Partners & vendors — contain (Email / phone)
*When to use:* When a partner's data or shared systems may be involved.  
*Approver:* Owner

> We are managing a security incident that may touch our shared {shared_resource}. As a precaution we have {precaution_taken}. Please watch for {what_to_watch_for} and let us know of anything unusual. Coordination contact: {incident_contact}.

#### Media / public — contain (Spokesperson statement)
*When to use:* A short holding line if the incident becomes public. One spokesperson only.  
*Approver:* Owner (single approved spokesperson)

> We are aware of a security incident and are responding with urgency. Protecting our customers' information is our priority. We have engaged the right expertise, are taking steps to contain it, and will share verified information as it becomes available.

## 4. Mini-Guide: How to Talk to Non-Technical People About Cyber Risk

**Principles.**
1. Lead with the business, not the technology: money, time, trust, reputation, and legal exposure.
2. Translate every risk into 'if this happens, then this is the cost.'
3. Use one analogy they already understand (a door, a key, insurance).
4. Give one clear recommendation, not five options.
5. Quantify with ranges, not false precision: 'a day or two offline.'
6. Replace fear with a next step — people act on direction, not dread.
7. Check for understanding: ask them to say it back in their own words.

**Jargon → plain language.**

| Term | In plain words | Analogy |
|---|---|---|
| Phishing | A fake email or text that tricks someone into clicking, paying, or giving up a password. | A con artist in a delivery uniform talking their way through the door. |
| Ransomware | Malicious software that locks your files until you pay — and paying is no guarantee. | A burglar who changes all your locks and sells you the new keys. |
| Multi-factor authentication (MFA) | A second check beyond your password, like a code on your phone. | A deadbolt on top of the doorknob lock. |
| Patch / update | A fix the vendor releases to close a known security hole. | Repairing a lock the manufacturer just warned everyone is pickable. |
| Encryption | Scrambling data so it's useless to anyone without the key. | A document shredder that can be perfectly un-shredded only by you. |
| Firewall | A filter that decides what network traffic is allowed in or out. | A bouncer checking everyone at the door against the guest list. |
| Backup | A spare copy of your data you can restore after loss or attack. | A photocopy of every important document, kept in a different building. |
| Breach | An incident where data is accessed or taken by someone who shouldn't have it. | Discovering the filing cabinet was opened and copied overnight. |
| Endpoint | Any device that connects to your systems — laptop, phone, tablet. | Every door and window into the building. |
| Zero-day | A brand-new flaw that attackers know about before a fix exists. | A lock flaw the locksmith hasn't learned about yet. |
| Social engineering | Manipulating a person, not a computer, to get access. | Sweet-talking the receptionist instead of breaking the lock. |
| Attack surface | All the ways someone could possibly get in. | The total number of doors, windows, and vents on the building. |

**What to say when…**

**Asking the owner to fund MFA**  
✅ Say: "For about the cost of a coffee per person each month, a stolen password stops being enough to drain the bank account."  
🚫 Not: "We need to deploy TOTP-based 2FA across the identity provider."

**Explaining why backups matter**  
✅ Say: "If ransomware hit tomorrow, tested backups are the difference between a bad day and a closed business."  
🚫 Not: "We have no immutable, air-gapped recovery tier."

**Justifying patching downtime**  
✅ Say: "A 20-minute update tonight closes a hole criminals are already using this week."  
🚫 Not: "There's an unpatched CVE with a public exploit in the wild."

**Reporting an incident to the board**  
✅ Say: "Here's what happened, what it cost us, what we've fixed, and the one thing we're changing so it can't repeat."  
🚫 Not: "We observed anomalous lateral movement and exfiltration indicators."

---

*ClearGlass Inc. · Clarity Is Power · Burlington, Ontario*
