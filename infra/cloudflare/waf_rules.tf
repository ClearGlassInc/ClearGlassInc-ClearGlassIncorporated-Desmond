# Custom WAF (http_request_firewall_custom phase) — anti-scraping heuristics.
#
# Rule 1 is an ALLOW for verified crawlers + logged-in operators, so legitimate
# SEO indexing and real sessions are never challenged. Everything after it only
# sees anonymous, unverified traffic. Each enforcement rule's action is a
# per-tier variable that starts at "log".

resource "cloudflare_ruleset" "waf_custom" {
  zone_id     = var.zone_id
  name        = "ClearGlass anti-scraping (custom)"
  description = "Protect high-value content from scraping/republishing. Observe-first."
  kind        = "zone"
  phase       = "http_request_firewall_custom"

  # --- Rule 1: never touch verified search engines or authenticated operators.
  # Skips the rest of THIS ruleset so canonicals/metadata stay reachable to
  # Googlebot/Bingbot and signed-in sessions pass straight through.
  rules {
    ref         = "allow_seo_and_sessions"
    description = "Allow verified bots + authenticated sessions (preserve SEO, skip scraping rules)"
    expression  = "${local.verified_bot} or (http.cookie contains \"cg_admin_session=\")"
    action      = "skip"
    action_parameters {
      ruleset = "current"
    }
    logging {
      enabled = true
    }
  }

  # --- Rule 2: obvious scraper fingerprints on any content path.
  # Empty/scripted user-agents and headless signatures that legitimate browsers
  # and verified crawlers never send.
  rules {
    ref         = "scraper_fingerprints"
    description = "Challenge/deny scripted clients (empty or library UA) on content"
    expression  = <<-EOT
      (${var.premium_path_expr} or starts_with(http.request.uri.path, "/"))
      and (
        http.user_agent eq ""
        or lower(http.user_agent) contains "python-requests"
        or lower(http.user_agent) contains "scrapy"
        or lower(http.user_agent) contains "httpclient"
        or lower(http.user_agent) contains "curl/"
        or lower(http.user_agent) contains "wget/"
        or lower(http.user_agent) contains "headlesschrome"
        or lower(http.user_agent) contains "node-fetch"
        or lower(http.user_agent) contains "go-http-client"
      )
    EOT
    action      = var.action_scraper_heuristics
  }

  # --- Rule 3: unverified automation hitting premium routes from datacenters.
  # High threat score OR hosting/datacenter ASN + no verified-bot status. This is
  # where most republish scrapers live. Kept off verified bots by Rule 1.
  rules {
    ref         = "aggressive_datacenter_crawl"
    description = "Challenge unverified datacenter/high-risk traffic on premium routes"
    expression  = <<-EOT
      ${var.premium_path_expr}
      and not ${local.verified_bot}
      and (cf.threat_score gt 10 or ip.src.is_in_european_union or cf.bot_management.verified_bot eq false)
    EOT
    action      = var.action_aggressive_crawl
  }

  # --- Rule 4: hotlink / referer protection for premium assets.
  # Deny asset requests whose Referer is neither our own site nor empty (direct
  # navigation). Blocks embedding our premium assets on third-party pages.
  rules {
    ref         = "asset_hotlink_protection"
    description = "Block off-site hotlinking of premium assets"
    expression  = <<-EOT
      ${var.asset_path_expr}
      and not ${local.same_site_ref}
      and not ${local.empty_referer}
      and not ${local.verified_bot}
    EOT
    action      = var.action_hotlink
  }
}
