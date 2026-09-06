# ClearGlass SMB Cyber Trust Agent

A plain-language cyber resilience advisor for small and medium businesses. The
agent works entirely from the **ClearGlass SMB Cyber Trust Kit** and never
improvises controls, prices, or legal thresholds that aren't in the kit.

## What's here

| File | Purpose |
|---|---|
| `agent.json` | Declarative agent config: role, capabilities, CTAs, guardrails, handoff. |
| `system_prompt.md` | The agent's persona, tools, output shape, few-shot examples, guardrails. |
| `tool_schema.json` | Tool contract — each tool maps 1:1 to a function in the engine. |
| `README.md` | This file. |

## The four deliverables

1. **Simple policy templates** — eight fill-in-the-blank policies (acceptable
   use, passwords/MFA, data protection, incident response, access control,
   backup & recovery, vendor risk, devices/BYOD).
2. **A risk heat-map** — a 5×5 likelihood × impact grid, banded Low → Critical,
   with a starter register of the risks that actually hurt small businesses.
3. **A "communication during incidents" script** — holding statements by phase
   (detect → contain → eradicate → recover → post-incident) and audience
   (staff, customers, affected individuals, regulator, partners, media).
4. **A mini-guide** — *How to talk to non-technical people about cyber risk*:
   principles, a jargon→plain glossary with analogies, and "what to say when…".

## Single source of truth

The agent, the in-browser console (`/smb-cyber-trust-kit.html`), and the
backend all read the **same** kit content produced by the deterministic engine:

```bash
# Regenerate the kit (Markdown + JSON) and refresh the web data file
python -m bots.smb_cyber_trust_kit_bot --org "Acme Dental"

# Inspect the JSON payload the console/agent ingest
python -m bots.smb_cyber_trust_kit_bot --json

# Print the full Markdown kit to stdout
python -m bots.smb_cyber_trust_kit_bot --print
```

Outputs:
- `operations/smb_cyber_trust_kit/smb-cyber-trust-kit.md` (+ timestamped archive)
- `operations/smb_cyber_trust_kit/smb-cyber-trust-kit.json`
- `assets/data/smb-cyber-trust-kit.json` (consumed by the web console)

## Tools

| Tool | Engine function | Risk |
|---|---|---|
| `score_risk` | `score_risk` | low |
| `build_heat_map` | `build_heat_map` | low |
| `rank_risks` | `rank_risks` | low |
| `render_policy` | `render_policy` | low |
| `incident_script` | `incident_script` | medium |
| `translate_jargon` | `JARGON_GLOSSARY` | low |
| `build_kit` | `build_kit` | low |
| `handoff_to_clearglass` | — | high |

`incident_script` for the **regulator** / **media** audiences and any
`handoff_to_clearglass` are gated: present them as drafts pending human approval.

## Guardrails

- Kit content only; no fabrication.
- Practical guidance, **not legal advice** — PIPEDA / PHIPA breach decisions go
  to a qualified advisor.
- Ontario / Canadian context (PIPEDA, PHIPA, CASL).
- Healthcare / government / finance → recommend professional review + offer a
  clean handoff to the ClearGlass team.

---

*ClearGlass Inc. · Clarity Is Power · Burlington, Ontario*
