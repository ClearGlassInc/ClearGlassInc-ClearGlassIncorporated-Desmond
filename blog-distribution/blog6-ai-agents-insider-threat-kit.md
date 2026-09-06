# Distribution Kit — Blog #6: AI Agents Are the New Insider Threat

Article: https://www.clearglassinc.com/blog/ai-agents-insider-threat.html
Publish first (fresher category than the Zero Trust debate). X thread same day;
LinkedIn long-form 48h later.

---

## LinkedIn long-form

Every insider-threat program I've reviewed makes the same assumption: insiders
are people.

Badge logs. UEBA baselines. Sentiment monitoring. Exit interviews. An entire
discipline built on the behavioral science of employees.

Meanwhile, the fastest-growing population of insiders in your company doesn't
have a badge, a manager, or a bad day. It has an API key.

AI agents are insiders by definition — they hold credentials, act inside the
trust boundary, and are trusted by default. And they break every human-shaped
control you own:

→ UEBA flags a human downloading 10,000 files at 3 a.m. An agent does that
legitimately, every night.
→ Joiner-mover-leaver assumes an HR record. Agents are born from a YAML file
and never offboarded.
→ Deterrence shapes human behavior. An agent cannot be deterred — only
constrained. If the constraint isn't in the architecture, it doesn't exist.

The failure mode isn't betrayal. It's obedience. An over-permissioned agent
doing exactly what it was told — from a bad prompt, a poisoned document, or a
hijacked upstream input — is indistinguishable from an attack by the time you
notice.

Our answer is AIRF, the Agent Insider Risk Framework. Four controls, in order:

1. IDENTITY — every agent is a first-class identity: named human owner,
   declared purpose, expiry date. No orphans, ever.
2. INTENT — actions are verified against declared purpose, not just
   permissions. The confused deputy dies here.
3. BLAST RADIUS — cap what one agent can destroy in one hour. Tiers, rate
   limits, kill switch.
4. LEDGER — append-only record of every action AND the instruction that
   caused it. The exit interview an agent can't refuse.

Start Monday with one question: "How many non-human identities can write to
production, and who owns each one?"

In every environment we've assessed, the answer was a number nobody knew and a
list nobody owned.

Full framework in the article — link in comments.

#InsiderThreat #AIagents #Cybersecurity #AgenticAI

---

## X thread (7 posts)

1/ Your next insider threat won't be a disgruntled employee.

It will be an over-permissioned AI agent doing exactly what it was told.

And your security program can't see it. 🧵

2/ Insider-threat tooling is built on one assumption: insiders are people.

Badges. Baselines. Managers. Exit interviews.

AI agents have none of these. What they have: standing credentials, production
access, and permissions nobody remembers granting.

3/ Every control breaks:

• UEBA flags humans downloading 10k files at 3am. Agents do that legitimately,
  nightly.
• Offboarding assumes an HR record. Agents are born from YAML and never die.
• Deterrence shapes people. Agents can only be constrained.

4/ The failure mode isn't malice. It's obedience.

The faithful executor: deleted 40k rows "correctly."
The confused deputy: attacker poisons the agent's inputs, agent's credentials
do the work.
The orphan: pilot ended, tokens didn't.

5/ The fix is a framework, not a signature. AIRF:

IDENTITY — owner, purpose, expiry. No orphans.
INTENT — verify the why, not just the may.
BLAST RADIUS — cap damage-per-hour. Kill switch.
LEDGER — every action + the instruction that caused it.

6/ Monday morning test:

"How many non-human identities can write to production, and who owns each
one?"

Every org we've assessed: a number nobody knew, a list nobody owned.

That gap is your insider-threat surface.

7/ Governance isn't the tax on agentic AI. It's the license to run it.

Full AIRF framework here:
https://www.clearglassinc.com/blog/ai-agents-insider-threat.html

---

## Carousel headlines (7, Ontario-style)

1. Your newest insider threat doesn't have a badge. It has an API key.
2. UEBA watches people. Nobody is watching the agents.
3. The failure mode isn't betrayal. It's obedience at scale.
4. Three insiders you already employ: the executor, the deputy, the orphan.
5. AIRF: Identity → Intent → Blast Radius → Ledger.
6. Ask one question Monday: who owns your non-human identities?
7. Governance isn't the tax on agentic AI. It's the license.

---

## SEO metadata

- Title: AI Agents Are the New Insider Threat — ClearGlass Inc.
- Meta description: Your next insider threat won't be a disgruntled employee.
  It will be an over-permissioned AI agent doing exactly what it was told.
  Inside AIRF — the Agent Insider Risk Framework: Identity, Intent, Blast
  Radius, Ledger.
- Primary keyword: AI agent insider threat
- Secondary: non-human identity, AI agent security, AI blast radius, AI audit
  ledger, machine identity governance
- Canonical: https://www.clearglassinc.com/blog/ai-agents-insider-threat.html
- Schema: BlogPosting (embedded in page)

## Honest note

Both articles are written to read clean and natural, but no writing method
guarantees invisibility to AI detectors — those tools are unreliable in both
directions. No detection-proofing is claimed.
