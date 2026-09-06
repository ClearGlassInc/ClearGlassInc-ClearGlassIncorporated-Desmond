# ClearGlassInc Artemis — ATT&CK Threat Intel & Detection Engineering Bot

This bot is a Python-first generator for SOC, Threat Intel, Detection Engineering, and Red Team planning.

- Framework basis: MITRE ATT&CK Enterprise **v18.1**.
- Output: structured JSON containing tactics, techniques, IOC enrichment, detections, playbooks, and ATT&CK Navigator layer.
- Location: `scripts/artemis_attack_intel_bot.py`.

## Quick start

```bash
python3 scripts/artemis_attack_intel_bot.py \
  --target-environment "enterprise cloud + on-prem hybrid" \
  --industry "finance" \
  --threat-actor "APT29" \
  --objective "detect" \
  --ioc "185.199.110.153" \
  --ioc "example-c2-domain.net" \
  --ioc "https://bad-domain.tld/login" \
  --output /tmp/artemis_attack_report.json
```

## What the bot produces

1. **Tactic progression** across all ATT&CK enterprise tactics listed in the prompt.
2. **Technique/sub-technique bundle** with ATT&CK IDs, examples, detections, mitigations, and data sources.
3. **IOC → TTP enrichment** with confidence labels and behavioral notes.
4. **Detection engineering plan**: high-signal analytics, SIEM/SOAR correlations, tuning, and known gaps.
5. **Red team simulation chain** for realistic enterprise hybrid attack paths.
6. **Blue team response playbooks** with trigger, response, containment, and forensic artifacts.
7. **ATT&CK Navigator JSON-compatible layer** for coverage visualization and prioritization.
8. **Strategic gap analysis** with quick wins, mid-term, and long-term upgrades.

## Integration pattern

- Wire report output into Foundry pipelines for daily enrichment.
- Push generated Navigator layer into ATT&CK Navigator dashboards.
- Store IOC enrichment output in a detection knowledge graph for auto-correlation.
- Use report sections to bootstrap AIP copilots and response runbooks.
