# Outreach Kit - AI Agent Attack-Surface and Control Assurance

Cold outreach, qualification, and objection handling for the assurance offer in
`OFFER.md`.

House rule for all outbound: plain text only. No emoji, no icons, no unicode
bullets or dashes. Plain hyphens and normal ASCII punctuation. Anything fancier
lands in a spam folder or looks automated.

Replace every `[bracketed]` field before sending.

---

## Email 1 - cold, first touch

Subject line options (pick one, do not A/B test with the same person):

1. Agent inventory question
2. Who owns your AI agents?
3. 15 minutes on agent access at [Company]

Body:

```
Hi [First Name],

One question: can you name every AI agent in your tenant that holds
write access to a production system, and who owns each one?

Most IT and audit leaders can name two or three. The full register is
usually longer.

I run independent, read-only assurance assessments on AI agent estates
for Ontario organizations. The output is an inventory, a permission map,
and a control record that is tested rather than assumed. I sell no
tooling.

Worth 15 minutes to see whether this applies to you? I will ask six
questions and tell you plainly if it does not.

Desmond Otieno Odhiambo
ClearGlass Inc.
289-707-0269
```

Notes: no attachment, no link, no deck. The hook is a checkable question, not a
claim. The close asks for a call, not a sale.

---

## Email 2 - follow-up, 4 business days later if no reply

Send in the same thread. Subject: `Re: [original subject]`.

```
Hi [First Name],

Same question, different angle.

When your auditor or your board asks for the AI agent inventory -
what each agent can access, who approved it, what it did - who
produces it, and how long does that take?

If the answer is "we would have to go and build that", it is cheaper
to build it before you are asked.

Still happy to spend 15 minutes on it.

Desmond Otieno Odhiambo
ClearGlass Inc.
289-707-0269
```

---

## Email 3 - breakup, 8 business days later

```
Hi [First Name],

I will stop here so I am not cluttering your inbox.

If the agent inventory question comes up later, from audit, the board,
or an incident, I am easy to find.

Desmond Otieno Odhiambo
ClearGlass Inc.
289-707-0269
```

---

## LinkedIn connection note

Under 300 characters, plain text.

```
Hi [First Name] - I do independent assurance assessments on AI agent
access and controls for Ontario organizations. Read-only, evidence
based, no tooling sold. Connecting in case the agent inventory question
lands on your desk. - Desmond, ClearGlass Inc.
```

---

## The 15-minute discovery call script

Purpose: qualify hard and disqualify fast. A prospect who should not buy this is
worth finding out about in minute four, not week three.

Open with one line: "I have six questions. If this is not a fit I will say so
and give you the time back."

### Question 1

"How many AI agents, copilots, or automated assistants are connected to systems
in your environment today, and where would you look to get the exact number?"

- **What the answer tells you:** whether an inventory exists at all, and whether
  the buyer knows the discovery method. "I would check with three different
  teams" is the qualifying answer.
- **Disqualifies if:** they give an exact, confident number and can name the
  source system that produces it. They may already have this covered.

### Question 2

"Which of those agents can write, not just read? Anything touching production,
customer records, money movement, or code that ships?"

- **What the answer tells you:** whether there is real exposure or only
  low-risk read-only chat use. Write access is the entire argument.
- **Disqualifies if:** genuinely nothing has write access and nothing is
  planned. Low urgency, revisit in two quarters.

### Question 3

"For each agent, who is the named human owner and who approved the access?"

- **What the answer tells you:** whether accountability is assigned or diffuse.
  "IT set it up" is a governance gap, not an answer.
- **Disqualifies if:** they have a documented owner and approval record per
  agent, with a maintained approval matrix.

### Question 4

"If an agent did something you did not expect last Tuesday at 3pm, could you
reconstruct the full chain of what it did from logs alone? Has anyone tried?"

- **What the answer tells you:** telemetry maturity and, more usefully, whether
  it has ever been tested. Almost nobody has tried.
- **Disqualifies if:** they have run that reconstruction, have the evidence, and
  it worked.

### Question 5

"If you needed to shut one down right now, what is the procedure, who can
execute it, and when was it last tested?"

- **What the answer tells you:** whether a kill switch exists as a tested
  control or as an assumption. An untested kill switch is a finding.
- **Disqualifies if:** documented, assigned, and tested within the last 6
  months, with evidence.

### Question 6

"If this assessment found something serious, who signs the engagement, what
budget does it come from, and what is your approval threshold and timeline?"

- **What the answer tells you:** authority, budget, and cycle. Ask it directly.
  A prospect who cannot answer this is a conversation, not a pipeline entry.
- **Disqualifies if:** no budget holder identified, no budget line, no timeline,
  and no path to get one. Park the contact, do not book a second call.

**Close:** if they qualify, propose Tier 1 as the next step and name the price
on the call. If they do not, say so, name the reason, and end early. Ending
early is the credibility move that gets the callback in six months.

---

## Objection handling

### "We already have SOC 2 / we already do security audits."

Those attest to your control environment as designed and operated for the
systems in the audit scope. AI agents are usually not in that scope, and where
they are, the testing is over the platform, not over what the agent itself is
permitted to do inside your tenants. A SOC 2 report will not tell you which
agent holds write access to your finance workflow, who approved it, or whether
the kill switch works. This assessment produces the agent-level evidence your
existing audit does not currently reach, in a form your auditor can consume.

### "Our AI use is just chatbots, low risk."

Good. That is worth confirming rather than assuming, and the confirmation is
cheap. What usually turns up is that a chatbot has been connected to a document
store, an email account, a ticketing system, or a repository, and the connector
inherited the permissions of the person who set it up. The risk is not the
model, it is the credential and the scope attached to it. If the scan finds that
every agent is genuinely read-only and narrow, you get a documented result
saying so, which is itself useful the next time someone asks.

### "This is IT's problem, not audit's."

The implementation is IT's. The evidence is audit's. When an agent takes an
action nobody authorized, the question that lands on the audit and risk side is
whether a control existed, whether it was tested, and whether the action can be
reconstructed. Those three questions are what this assessment answers. IT should
absolutely be in the room; the deliverable is written so both sides can use it,
and the control validation is done by test rather than by asking IT whether the
control exists.

### "Too expensive / no budget this cycle."

Then start with the Tier 1 scan at $7,500, which is five days and usually sits
inside a discretionary approval. It produces the inventory and the top five
exposures. If it finds nothing material you have a documented clean result for a
small spend. If it finds something material, you now have the evidence to
support a budget request rather than an argument. The Tier 1 fee credits in full
against the full assessment if you upgrade within 60 days, so nothing is wasted
by starting small.

---

## Target list template

Do not invent organizations or people. Fill from real research only: public
sector supplier lists, association member directories, conference attendee
lists, LinkedIn, and referrals. Record where each contact came from in `Source`.

Status values: `Not contacted`, `Email 1 sent`, `Email 2 sent`, `Email 3 sent`,
`Replied`, `Call booked`, `Qualified`, `Disqualified`, `Closed won`,
`Closed lost`.

| Organization | Sector | Size | Contact Name | Title | Source | Status | Last Touch | Next Action |
|---|---|---|---|---|---|---|---|---|
| [EXAMPLE - DELETE BEFORE USE] Placeholder Org | [sector] | [headcount] | [name] | [title] | [where found] | Not contacted | [YYYY-MM-DD] | [action] |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |
