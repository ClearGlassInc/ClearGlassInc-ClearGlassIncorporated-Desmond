# Managed rulesets (http_request_firewall_managed phase).
#
# Deploys Cloudflare's Managed Ruleset and the OWASP Core Ruleset with an action
# OVERRIDE so both run in "log" first (observe what they would catch), then get
# promoted to challenge/block via `managed_waf_override_action`. Gated by
# `enable_managed_waf` so a zone that manages these in the dashboard can opt out.

resource "cloudflare_ruleset" "managed_waf" {
  count = var.enable_managed_waf ? 1 : 0

  zone_id     = var.zone_id
  name        = "ClearGlass managed WAF deployment"
  description = "Cloudflare Managed + OWASP rulesets, observe-first."
  kind        = "zone"
  phase       = "http_request_firewall_managed"

  # Cloudflare Managed Ruleset (well-known stable ID).
  rules {
    ref         = "deploy_cloudflare_managed"
    description = "Cloudflare Managed Ruleset"
    expression  = "true"
    action      = "execute"
    action_parameters {
      id = "efb7b8c949ac4650a09736fc376e9aee"
      overrides {
        action = var.managed_waf_override_action
      }
    }
  }

  # OWASP Core Ruleset (well-known stable ID). Anomaly-scoring; keep at log until
  # its paranoia level is tuned against real traffic to avoid false positives.
  rules {
    ref         = "deploy_owasp_core"
    description = "OWASP Core Ruleset"
    expression  = "true"
    action      = "execute"
    action_parameters {
      id = "4814384a9e5d4991b9815dcfc25d2f1f"
      overrides {
        action = var.managed_waf_override_action
      }
    }
  }
}

# Super Bot Fight Mode (Pro/Business). Off by default — enable only after the
# baseline shows verified-bot vs. automated traffic clearly, so you don't
# accidentally challenge a partner integration.
resource "cloudflare_bot_management" "sbfm" {
  count      = var.enable_super_bot_fight_mode ? 1 : 0
  zone_id    = var.zone_id
  sbfm_definitely_automated      = "managed_challenge"
  sbfm_likely_automated          = "managed_challenge"
  sbfm_verified_bots             = "allow"
  sbfm_static_resource_protection = false
  optimize_wordpress             = false
}
