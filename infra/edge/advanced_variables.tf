variable "enable_bot_management" {
  type        = bool
  description = "Manage Cloudflare Super Bot Fight Mode/Bot Management settings. Default off because another Terraform state may already own the zone setting and plan availability varies."
  default     = false
}

variable "bot_definitely_automated_action" {
  type        = string
  description = "Action for traffic Cloudflare classifies as definitely automated."
  default     = "managed_challenge"
  validation {
    condition     = contains(["allow", "managed_challenge", "block"], var.bot_definitely_automated_action)
    error_message = "bot_definitely_automated_action must be allow, managed_challenge, or block."
  }
}

variable "bot_likely_automated_action" {
  type        = string
  description = "Action for traffic Cloudflare classifies as likely automated."
  default     = "managed_challenge"
  validation {
    condition     = contains(["allow", "managed_challenge", "block"], var.bot_likely_automated_action)
    error_message = "bot_likely_automated_action must be allow, managed_challenge, or block."
  }
}

variable "deny_ipv4_cidrs" {
  type        = list(string)
  description = "Confirmed-abuse IPv4 CIDRs for explicit deny rules. Never populate solely from an unverified reputation signal."
  default     = []
}

variable "deny_ipv6_cidrs" {
  type        = list(string)
  description = "Confirmed-abuse IPv6 CIDRs for explicit deny rules. Never populate solely from an unverified reputation signal."
  default     = []
}

variable "quarantine_ipv4_cidrs" {
  type        = list(string)
  description = "Temporary IPv4 quarantine CIDRs challenged rather than permanently denied. Requires a future quarantine_expires_at."
  default     = []
}

variable "quarantine_ipv6_cidrs" {
  type        = list(string)
  description = "Temporary IPv6 quarantine CIDRs challenged rather than permanently denied. Requires a future quarantine_expires_at."
  default     = []
}

variable "quarantine_expires_at" {
  type        = string
  description = "RFC3339 expiry for temporary quarantine lists. Empty only when quarantine lists are empty."
  default     = ""
}

variable "denied_asns" {
  type        = list(number)
  description = "Explicit confirmed-abuse ASNs, enforced only when geo/ASN controls are enabled."
  default     = []
}

variable "challenge_asns" {
  type        = list(number)
  description = "ASNs to managed-challenge, enforced only when geo/ASN controls are enabled."
  default     = []
}

variable "max_uri_bytes" {
  type        = number
  description = "Observe/challenge requests whose raw URI exceeds this byte length. Tune from legitimate traffic before blocking."
  default     = 16384
  validation {
    condition     = var.max_uri_bytes >= 4096
    error_message = "max_uri_bytes must be at least 4096 to avoid an unsafe low limit."
  }
}

variable "max_query_bytes" {
  type        = number
  description = "Observe/challenge requests whose raw query string exceeds this byte length."
  default     = 8192
  validation {
    condition     = var.max_query_bytes >= 2048
    error_message = "max_query_bytes must be at least 2048 to avoid an unsafe low limit."
  }
}

variable "max_single_header_value_bytes" {
  type        = number
  description = "Observe/challenge requests containing an individual header value larger than this threshold."
  default     = 8192
  validation {
    condition     = var.max_single_header_value_bytes >= 2048
    error_message = "max_single_header_value_bytes must be at least 2048."
  }
}

variable "enable_enterprise_body_size_rule" {
  type        = bool
  description = "Enable body-size/truncation custom-rule fields that require the applicable Cloudflare plan."
  default     = false
}

variable "max_request_body_bytes" {
  type        = number
  description = "Maximum request body byte threshold when the plan-specific body-size rule is enabled."
  default     = 1048576
  validation {
    condition     = var.max_request_body_bytes >= 65536
    error_message = "max_request_body_bytes must be at least 65536."
  }
}

check "temporary_quarantine_has_future_expiry" {
  assert {
    condition = length(concat(var.quarantine_ipv4_cidrs, var.quarantine_ipv6_cidrs)) == 0 ? true : (
      can(timecmp(var.quarantine_expires_at, plantimestamp())) ? timecmp(var.quarantine_expires_at, plantimestamp()) > 0 : false
    )
    error_message = "Temporary quarantine CIDRs require quarantine_expires_at to be a valid RFC3339 timestamp later than the current Terraform plan time."
  }
}
