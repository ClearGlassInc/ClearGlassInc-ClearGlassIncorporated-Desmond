# Campaign Playbook

Use the five initial packages in `data/campaigns/burlington-campaign-packages.json` as draft campaign kits. Every campaign must define audience, offer, CTA, landing-page mapping, channel assets, measurement plan, approval status, shutdown thresholds, and compliance findings.

No campaign may launch until approval exists for the exact external action, spend ceiling, audience, creative, destination URL, and measurement configuration.

`python3 tools/campaign_registry.py` checks every package against this list and reports what each still needs; `--check` fails if a campaign marked `approved` or `active` is incomplete, and `--links` prints each campaign's tracked destination. Every campaign carries a code, `CG-<CHANNEL>-<AUDIENCE>-<OFFER>-<YYYY>-Q<n>` (for example `CG-LINKEDIN-SMB-RISKAUDIT-2026-Q4`), used as `utm_campaign`. The control plane copies it from the lead through Stripe checkout onto the paid order, so the revenue cockpit reports confirmed revenue per campaign. A campaign's results come only from that verified data, never from the package file.
