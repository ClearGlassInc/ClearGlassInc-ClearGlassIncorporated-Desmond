# AI Agent Attack-Surface and Control Assurance

The sales and delivery pack for ClearGlass's agent assurance service.

| File | What it is |
|---|---|
| `OFFER.md` | Productized offer sheet: positioning, buyers, three tiers, pricing arithmetic, scope limits. Internal. Confirm the pricing block before it goes out. |
| `OUTREACH.md` | Cold email sequence, LinkedIn note, 15-minute discovery script, objection handling, target-list template. |
| `INTAKE.md` | Pre-engagement questionnaire: access needed, documents requested, people to interview, scope boundary, data handling. |
| `ASSESSMENT_TEMPLATE.md` | The blank six-artifact delivery template. Ships empty. Nothing in it is a finding. |
| `engagements/` | Per-client working copies. Gitignored. |

## Operating loop

1. **Send outreach.** Run the sequence in `OUTREACH.md`, qualify on the
   discovery script, propose a tier from `OFFER.md`.
2. **Run intake.** Send `INTAKE.md` before day 1. Access and documents arrive
   first, so fieldwork starts on evidence rather than on waiting.
3. **Deliver the assessment.** Scaffold the engagement, fill the artifacts from
   evidence only, then run `--check` and `--summary` before the report ships.

## Tool

```bash
python3 tools/assurance_pack.py --new acme-credit-union   # scaffold an engagement
python3 tools/assurance_pack.py --list                    # list engagements
python3 tools/assurance_pack.py --check operations/assurance/engagements/acme-credit-union
python3 tools/assurance_pack.py --summary operations/assurance/engagements/acme-credit-union
```

`--check` is the pre-delivery gate. It exits 1 while any bracketed placeholder
remains, printing every offending line, so an unfilled field cannot reach a
client. A bare `UNKNOWN` in a Confidence cell is a legitimate value and passes;
only bracketed markers such as `[UNKNOWN - NOT YET VALIDATED]` fail.

`--summary` reports the VERIFIED / REPORTED / UNKNOWN ratio so evidence quality
is visible before delivery rather than after a client asks.

Tests: `tests/test_assurance_pack.py`.

## Warning

`operations/assurance/engagements/*/` contains real client data and is
gitignored. Do not commit it, and do not remove the ignore rule.
