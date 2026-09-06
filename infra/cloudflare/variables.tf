# Cloudflare content-protection — inputs.
#
# The per-tier `action_*` variables are the heart of the safe rollout: every
# rule ships in "log" first, and you promote ONE tier at a time to
# "managed_challenge" and then "block" as evidence accumulates. Nothing here is
# all-or-nothing.
#
# NOTE ON "log": the log-only action on custom firewall + rate-limit rules is an
# Enterprise capability. If this zone is not Enterprise, see README ("Observe
# without Enterprise") for the fallback — deploy the narrowest rules at
# "managed_challenge" and read intent from Security Analytics instead.

variable "account_id" {
  type        = string
  description = "Cloudflare account ID that owns the zone."
}

variable "zone_id" {
  type        = string
  description = "Cloudflare zone ID for the protected site."
}

variable "zone_hostname" {
  type        = string
  description = "Apex hostname of the zone, e.g. clearglass.example. Used for hotlink/referer checks."
}

variable "premium_path_expr" {
  type        = string
  description = "Wirefilter fragment matching premium HTML routes (server-rendered, gated)."
  default     = "(http.request.uri.path contains \"/playbooks\" or http.request.uri.path contains \"/api/premium\" or starts_with(http.request.uri.path, \"/admin\"))"
}

variable "asset_path_expr" {
  type        = string
  description = "Wirefilter fragment matching downloadable/premium asset endpoints (both origin signing schemes)."
  default     = "(starts_with(http.request.uri.path, \"/api/download/\") or starts_with(http.request.uri.path, \"/api/assets/\") or http.request.uri.path contains \"/assets/premium/\")"
}

# --- Per-tier enforcement actions. Start every tier at "log". ------------------
# Allowed values: log | managed_challenge | js_challenge | block

variable "action_ratelimit_premium" {
  type    = string
  default = "log"
}

variable "action_ratelimit_assets" {
  type    = string
  default = "log"
}

variable "action_scraper_heuristics" {
  type    = string
  default = "log"
}

variable "action_aggressive_crawl" {
  type    = string
  default = "log"
}

variable "action_hotlink" {
  type    = string
  default = "log"
}

variable "managed_waf_override_action" {
  type        = string
  description = "Action override for the Cloudflare Managed + OWASP rulesets. Start at 'log'."
  default     = "log"
}

variable "enable_managed_waf" {
  type    = bool
  default = true
}

variable "enable_super_bot_fight_mode" {
  type        = bool
  description = "Toggle Super Bot Fight Mode (Pro/Biz). Leave false until baseline is understood."
  default     = false
}

# --- Rate-limit thresholds. Deliberately generous to start; tighten in Phase 4.
variable "premium_rpm_per_ip" {
  type    = number
  default = 60
}

variable "asset_rpm_per_ip" {
  type    = number
  default = 30
}

variable "mitigation_timeout_seconds" {
  type        = number
  description = "How long a client stays mitigated after tripping a rate limit."
  default     = 600
}

# Shared HMAC secret for edge signed-asset verification. MUST equal the origin's
# ASSET_SIGNING_SECRET (admin/lib/signing.ts) so tokens verify identically at
# edge and origin. Store in a tfvars file or TF_VAR_ env, never in VCS.
variable "asset_signing_secret" {
  type      = string
  sensitive = true
  default   = ""
}
