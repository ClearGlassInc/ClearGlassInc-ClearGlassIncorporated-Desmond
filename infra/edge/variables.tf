variable "account_id" {
  type        = string
  description = "Cloudflare account ID."
}

variable "zone_id" {
  type        = string
  description = "Cloudflare zone ID."
}

variable "zone_name" {
  type        = string
  description = "Apex zone name."
  default     = "clearglassinc.com"
}

variable "public_hostname" {
  type        = string
  description = "Public hostname protected by the edge."
  default     = "www.clearglassinc.com"
}

variable "api_hostname" {
  type        = string
  description = "Optional future dynamic API hostname. Empty disables API-specific Terraform rules."
  default     = ""
}

variable "admin_hostname" {
  type        = string
  description = "Optional future administrative hostname. Empty disables admin-specific Terraform rules."
  default     = ""
}

variable "enable_custom_waf" {
  type        = bool
  description = "Create custom WAF rules. Leave false for the first plan until phase ownership/action support is confirmed."
  default     = false
}

variable "enable_managed_waf" {
  type        = bool
  description = "Execute Cloudflare Managed Ruleset when zone plan and phase ownership are confirmed."
  default     = false
}

variable "enable_rate_limits" {
  type        = bool
  description = "Create route rate-limit rules. Disabled by default for an observation-first rollout."
  default     = false
}

variable "enable_security_headers" {
  type        = bool
  description = "Create response-header transform rules."
  default     = false
}

variable "enable_logpush" {
  type        = bool
  description = "Create firewall-events Logpush job. Requires a validated destination."
  default     = false
}

variable "enable_geo_asn_rules" {
  type        = bool
  description = "Enable country/ASN enforcement. Must remain false unless explicitly approved."
  default     = false
}

variable "enable_emergency_mode" {
  type        = bool
  description = "Enable temporary high-security mode. Must be reverted promptly after incident containment."
  default     = false
}

variable "custom_waf_action" {
  type        = string
  description = "Provider custom-rule action after staged review. 'log' may require an Enterprise plan."
  default     = "log"
  validation {
    condition     = contains(["log", "managed_challenge", "block"], var.custom_waf_action)
    error_message = "custom_waf_action must be log, managed_challenge, or block."
  }
}

variable "managed_waf_override_action" {
  type        = string
  description = "Override for Cloudflare Managed/OWASP rules. Start with log where the plan supports it."
  default     = "log"
  validation {
    condition     = contains(["log", "managed_challenge", "block"], var.managed_waf_override_action)
    error_message = "managed_waf_override_action must be log, managed_challenge, or block."
  }
}

variable "rate_limit_action" {
  type        = string
  description = "Action for route rate limits after rollout approval."
  default     = "managed_challenge"
  validation {
    condition     = contains(["managed_challenge", "block"], var.rate_limit_action)
    error_message = "rate_limit_action must be managed_challenge or block."
  }
}

variable "trusted_ipv4_cidrs" {
  type        = list(string)
  description = "Explicit trusted IPv4 CIDRs. Keep minimal."
  default     = []
}

variable "trusted_ipv6_cidrs" {
  type        = list(string)
  description = "Explicit trusted IPv6 CIDRs. Keep minimal."
  default     = []
}

variable "trusted_asns" {
  type        = list(number)
  description = "Trusted ASNs used only when geo/ASN controls are explicitly enabled."
  default     = []
}

variable "allowed_countries" {
  type        = list(string)
  description = "Country codes explicitly allowed by an enabled geo policy. Empty means no allow-only policy."
  default     = []
}

variable "denied_countries" {
  type        = list(string)
  description = "Country codes denied only when geo enforcement is enabled."
  default     = []
}

variable "challenge_countries" {
  type        = list(string)
  description = "Country codes challenged only when geo enforcement is enabled."
  default     = []
}

variable "static_asset_requests_per_minute" {
  type    = number
  default = 600
}

variable "html_requests_per_minute" {
  type    = number
  default = 120
}

variable "login_requests_per_minute" {
  type    = number
  default = 20
}

variable "reset_requests_per_10_minutes" {
  type    = number
  default = 8
}

variable "search_requests_per_minute" {
  type    = number
  default = 60
}

variable "form_requests_per_10_minutes" {
  type    = number
  default = 10
}

variable "api_requests_per_minute" {
  type    = number
  default = 120
}

variable "admin_requests_per_minute" {
  type    = number
  default = 60
}

variable "webhook_requests_per_minute" {
  type    = number
  default = 300
}

variable "mitigation_timeout_seconds" {
  type    = number
  default = 600
}

variable "hsts_include_subdomains" {
  type        = bool
  description = "Add includeSubDomains only after every subdomain is confirmed HTTPS-ready."
  default     = false
}

variable "hsts_preload" {
  type        = bool
  description = "Add HSTS preload only after includeSubDomains is approved and preload requirements are met."
  default     = false
  validation {
    condition     = !var.hsts_preload || var.hsts_include_subdomains
    error_message = "hsts_preload requires hsts_include_subdomains=true."
  }
}

variable "logpush_destination" {
  type        = string
  description = "Validated Logpush destination URI. Treat as sensitive if it embeds credentials."
  default     = ""
  sensitive   = true
}

variable "logpush_ownership_challenge" {
  type        = string
  description = "Optional ownership challenge string required by some Logpush destinations."
  default     = ""
  sensitive   = true
}

variable "log_full_client_ip" {
  type        = bool
  description = "Include full ClientIP in exported firewall events only when incident/retention requirements justify it."
  default     = false
}
