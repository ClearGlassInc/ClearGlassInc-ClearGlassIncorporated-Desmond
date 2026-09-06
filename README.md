# ClearGlassInc Artemis Documentation Index

Long-form blueprints, platform designs, and corporate documentation supporting the public site.

## Corporate and governance
- `clearglassinc_corporate_profile.md`
- `clearglassinc_artemis_enterprise_corporate_layer.md`
- `clearglassinc_official_letterhead_template.md`
- `desmond_otieno_odhiambo_executive_profile.md`

## Platform architecture
- `artemis-intelligence-platform-blueprint.md`
- `clearglassinc_artemis_palantir_aip_blueprint.md`
- `clearglassinc_artemis_palantir_gotham_foundry_aip_apollo_production_design.md`
- `clearglassinc_artemis_palantir_self_evolving_intelligence_platform_blueprint_2026-07-18.md`
- `clearglassinc_artemis_palantir_self_evolving_ai_platform_advanced_merge_blueprint_2026-07-21.md`
- `clearglassinc_artemis_palantir_self_improving_fullstack_design.md`
- `clearglassinc_artemis_palantir_self_evolving_ai_platform_2026.md`
- `clearglassinc_artemis_legal_tech_multi_agent_blueprint.md`
- `clearglassinc_artemis_linked_fullstack_blueprint.md`
- `clearglassinc_artemis_operating_model_and_ai_architecture.md`
- `clearglassinc_artemis_quantum_neural_smart_glass_unified_roadmap.md`

## Self-evolving platform designs
- `clearglassinc_artemis_self_evolving_ai_intelligence_platform_blueprint.md`
- `clearglassinc_artemis_global_net_self_evolving_intelligence_platform_2026-06-29.md`
- `clearglassinc_artemis_self_evolving_platform.md`
- `clearglassinc_artemis_self_evolving_intelligence_platform_design.md`
- `clearglassinc_artemis_extreme_self_evolving_platform_design.md`
- `clearglassinc_artemis_fullstack_self_evolving_platform_spec.md`
- `clearglassinc_artemis_nextgen_self_improving_platform_spec.md`
- `clearglassinc_artemis_self_evolving_runtime_blueprint_2026.md`
- `clearglassinc_artemis_coo_self_improving_platform_blueprint.md`
- `clearglassinc_artemis_gotham_foundry_aip_apollo_self_evolving_blueprint.md`
- `clearglassinc_artemis_gotham_foundry_aip_apollo_extreme_blueprint.md`
- `clearglassinc_artemis_palantir_self_evolving_intelligence_platform_2040.md`
- `CLEARGLASSINC_ARTEMIS_SELF_EVOLVING_AI_PLATFORM_DESIGN_2026-05-06.md`

## Revenue, intelligence, and automation
- `GITHUB_GROWTH_LAUNCH_PLAYBOOK.md`
- `clearglass_monetization_engine_deploy_now.md`
- `clearglassinc_artemis_ethics_first_revenue_and_intelligence_engine.md`
- `clearglassinc_artemis_lead_scraping_architecture_python.md`
- `clearglassinc_artemis_stegoforge_linked_system_design.md`

## Operational reporting
- `clearglassinc_artemis_governed_intelligence_platform_core_sitrep_2026-07-31.md`

## Guardian
- `guardian_clear_glass_browser_concept.md`
- `guardian_command_nexus_spec.html`
- `guardian_command_nexus_spec.css`

## Finance automation

The operations finance bot (`bots/operations_finance_bot.py`) is the primary production-grade financial model in this repository. It computes inventory cost, customer retention value, and management fee structure on a weekly schedule and on-demand.

**Key outputs (written to `operations/output/`):**

| File | Description |
|---|---|
| `latest.md` | Human-readable finance report for the most recent run |
| `latest.json` | Machine-readable payload for downstream dashboards or integrations |
| `archive/<timestamp>.md` | Immutable historical run record |

**Trigger on demand** via GitHub Actions → Operations Finance Bot → Run workflow. All 15 financial parameters are configurable as workflow dispatch inputs, including unit cost, churn rate, labor cost, margin target, and fee preference. Unset inputs fall back to production defaults defined in the bot.

**Extending the model:** See `CONTRIBUTING.md` → "Finance automation" for the full step-by-step process for adding metrics, inputs, and tests.

**Test coverage:** `tests/test_operations_finance_bot.py` validates financial invariants including linear cost scaling, fee floor enforcement, formatter precision, zero-churn boundary conditions, and full JSON output integrity.

## Usage
These documents are written to be copied directly into GitHub Pages, governance repositories, or client-facing documentation portals. When a topic has multiple iterations, the most recent dated file takes precedence; earlier versions are retained for traceability.
