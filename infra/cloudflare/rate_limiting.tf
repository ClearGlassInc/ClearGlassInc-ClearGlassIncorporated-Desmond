# Rate limiting (http_ratelimit phase) — premium routes + asset endpoints.
#
# Counts per client IP within a rolling window and mitigates for
# `mitigation_timeout_seconds`. Verified bots and authenticated sessions are
# exempted inside each counting expression so SEO crawlers and real operators
# are never rate-limited. Actions start at "log".
#
# NOTE: `cf.colo.id` is included in characteristics because non-Enterprise zones
# require it (counts are per-datacenter). On Enterprise you may drop it for a
# true global per-IP count.

resource "cloudflare_ruleset" "rate_limit" {
  zone_id     = var.zone_id
  name        = "ClearGlass premium rate limiting"
  description = "Per-IP limits on premium pages and asset downloads."
  kind        = "zone"
  phase       = "http_ratelimit"

  # --- Premium HTML routes: cap page fetches per IP/minute.
  rules {
    ref         = "rl_premium_pages"
    description = "Limit premium page requests per IP"
    expression  = "${var.premium_path_expr} and not ${local.verified_bot}"
    action      = var.action_ratelimit_premium
    ratelimit {
      characteristics     = ["ip.src", "cf.colo.id"]
      period              = 60
      requests_per_period = var.premium_rpm_per_ip
      mitigation_timeout  = var.mitigation_timeout_seconds
      # Don't count authenticated operators toward the limit.
      counting_expression = "${var.premium_path_expr} and not (http.cookie contains \"cg_admin_session=\")"
    }
  }

  # --- Asset endpoints: tighter cap; downloads should be occasional.
  rules {
    ref         = "rl_premium_assets"
    description = "Limit premium asset/download requests per IP"
    expression  = "${var.asset_path_expr} and not ${local.verified_bot}"
    action      = var.action_ratelimit_assets
    ratelimit {
      characteristics     = ["ip.src", "cf.colo.id"]
      period              = 60
      requests_per_period = var.asset_rpm_per_ip
      mitigation_timeout  = var.mitigation_timeout_seconds
    }
  }

  # --- Burst guard: many DISTINCT premium paths from one IP in a short window is
  # the signature of a site-wide scrape. Longer window, low ceiling.
  rules {
    ref         = "rl_scrape_burst"
    description = "Catch broad crawls: high request volume across premium paths"
    expression  = "${var.premium_path_expr} and not ${local.verified_bot}"
    action      = var.action_ratelimit_premium
    ratelimit {
      characteristics     = ["ip.src", "cf.colo.id"]
      period              = 600
      requests_per_period = var.premium_rpm_per_ip * 8
      mitigation_timeout  = var.mitigation_timeout_seconds
    }
  }
}
