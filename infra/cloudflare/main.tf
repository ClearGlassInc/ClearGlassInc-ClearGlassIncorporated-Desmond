# Provider + shared locals for the Cloudflare content-protection stack.
#
# Apply order is intentional: verified search engines and same-site traffic are
# always allowed FIRST (so SEO and real users are never touched), then the
# anti-scraping heuristics, then rate limits, then managed rulesets. Cloudflare
# evaluates the http_request_firewall_custom phase top-to-bottom and stops at the
# first terminating action, so the allow/skip rule must be rule #1.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.40"
    }
  }
}

provider "cloudflare" {
  # Auth via CLOUDFLARE_API_TOKEN env var (token scoped to Zone WAF + Rulesets +
  # Workers). Never hard-code credentials here.
}

locals {
  # Verified good bots (Googlebot, Bingbot, etc.) — cf.client.bot is true only
  # for crawlers Cloudflare has cryptographically verified, so this cannot be
  # spoofed by a scraper setting a Googlebot user-agent.
  verified_bot   = "(cf.client.bot)"
  same_site_ref  = "(http.referer contains \"${var.zone_hostname}\")"
  empty_referer  = "(http.referer eq \"\")"
}
