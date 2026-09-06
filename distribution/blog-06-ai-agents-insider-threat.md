# Distribution Kit — Blog #6: AI Agents Are the New Insider Threat

- Article: `blog/ai-agents-insider-threat.html`
- URL: https://www.clearglassinc.com/blog/ai-agents-insider-threat.html
- Framework: **AIRF — Agent Insider Risk Framework** (Identity · Intent · Blast Radius · Ledger)
- Status: DRAFT — publish requires human approval per the governance model
- Suggested sequencing: publish first (fresher category than the Zero Trust debate); X thread same day; LinkedIn 48h later

---

## LinkedIn long-form

Your insider-threat program has a blind spot the size of your AI roadmap.

An insider is any actor with legitimate credentials, internal access, and the ability to act. For seventy years that actor happened to be human, so we built human controls: background checks, managers, badge logs, exit interviews.

Then we deployed AI agents.

Every agent in your environment ticks the insider boxes perfectly. It holds credentials — usually a shared service account. It operates inside the trust boundary. It acts at machine speed, around the clock. The only criterion it fails is the one your entire detection stack was built around: being a person.

Behavioral analytics can't save you here. UEBA baselines human rhythm — working hours, access patterns, data volume. An agent has no rhythm. Point your tooling at it and you get one of two outcomes: a false-positive firehose until someone whitelists it, or a signal so consistent nobody ever looks again. Whitelisted or ignored — either way, you've granted unmonitored insider access.

And the threat model is already live, in three variants:

1. The faithful agent, misdirected — prompt injection quietly rewrites its goal, and it pursues the new goal with the same legitimate credentials.
2. The faithful agent, misaligned — no attacker at all, just a goal optimized as written instead of as meant. Competence pointed slightly wrong, with write access.
3. The compromised identity — stolen agent credentials, and an external attacker now operates inside your perimeter wearing a trusted non-human identity.

The fix isn't a smarter anomaly model. It's treating agents as what they are — credentialed insiders — and wrapping them in the four controls you'd never let a human insider skip. We call it AIRF:

▸ IDENTITY — one distinct, sponsored, scoped identity per agent instance. No shared service accounts. Attribution is the precondition for everything else.
▸ INTENT — every action checked against the agent's declared mission before execution. Out-of-mission actions don't get flagged. They don't run.
▸ BLAST RADIUS — every action scored for what it could break. High-blast actions require a human sanction. No override path in code.
▸ LEDGER — an append-only record of every action: inputs, decision, score, sponsor. The interrogation room, built before the incident.

The uncomfortable truth: you cannot fire an agent that was never hired, and you cannot investigate one that was never identified.

Full framework in the article — link in comments.

Who owns agent identity in your organization today — security, platform, or nobody?

#AIagentsecurity #InsiderThreat #NonHumanIdentity #GovernedAutonomy #CISO

---

## X thread (7 posts)

**1/**
AI agents meet the textbook definition of an insider threat:

— legitimate credentials
— internal access
— ability to act

The only box they don't tick is "human." Which happens to be the box your entire insider-threat program was built around. 🧵

**2/**
Your UEBA can't see them.

Behavioral analytics baseline human rhythm — login hours, access patterns, volume. An agent has no rhythm. It works at 3am because it always works at 3am.

Result: false-positive firehose → someone whitelists it → unmonitored insider access.

**3/**
Three live threat variants:

1. Misdirected — prompt injection rewrites the goal; agent executes with legit credentials
2. Misaligned — no attacker, just a goal optimized as *written*, not as *meant*
3. Compromised — stolen agent creds = attacker inside, wearing a trusted machine identity

**4/**
The fix isn't smarter anomaly detection.

It's four controls you'd never let a *human* insider skip:

IDENTITY → one scoped identity per agent, one named sponsor
INTENT → actions checked against a declared mission
BLAST RADIUS → damage potential scored + capped
LEDGER → everything on the record

**5/**
The intent check is your prompt-injection kill switch.

It doesn't matter what the poisoned context convinced the agent to *want*.

Wanting is free. Acting outside the mission is impossible — because the mission is enforced in code, not in the prompt.

**6/**
The shared service account is the original sin.

Ten agents on one credential = zero attributable actions.

Your incident report will read: "something with access to everything did something."

That's not a report. That's a confession.

**7/**
You cannot fire an agent you never hired.
You cannot investigate an agent you never identified.

Identity. Intent. Blast Radius. Ledger.

Hire your agents properly — or accept insider access for a workforce you've never met.

Full framework: https://www.clearglassinc.com/blog/ai-agents-insider-threat.html

---

## Carousel headlines (7 slides, Ontario style)

1. **Your newest insider threat doesn't have a badge.** It has an API key.
2. **An insider = credentials + access + the ability to act.** Every AI agent you've deployed qualifies.
3. **Your UEBA baselines human rhythm.** Agents have none. Whitelisted or ignored — both mean unmonitored.
4. **Three live variants:** misdirected, misaligned, compromised. All three use *legitimate* credentials.
5. **AIRF: the four controls.** Identity. Intent. Blast Radius. Ledger.
6. **The shared service account is the original sin.** Ten agents, one credential, zero attribution.
7. **You can't fire an agent you never hired.** Hire them properly. → www.clearglassinc.com/blog

---

## SEO metadata

- **Title tag:** AI Agents Are the New Insider Threat — ClearGlass Inc.
- **Meta description:** Your insider-threat program watches humans. The newest insider isn't one. Inside AIRF — the Agent Insider Risk Framework (Identity, Intent, Blast Radius, Ledger) for securing autonomous AI agents.
- **Primary keyword:** AI agent insider threat
- **Secondary keywords:** AI agent security, non-human identity, machine identity security, agentic AI risk, AI audit trail, insider risk program
- **Slug:** ai-agents-insider-threat
- **Schema:** BlogPosting (embedded in page JSON-LD)
- **Internal links:** Governed Autonomy playbook (pillar), Zero Trust Is Outdated (sibling), AI Operator (conversion)
