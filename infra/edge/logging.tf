locals {
  firewall_log_fields = concat([
    "Datetime",
    "Action",
    "RuleID",
    "Source",
    "ClientASN",
    "ClientCountry",
    "ClientRequestHTTPHost",
    "ClientRequestPath",
    "ClientRequestUserAgent",
    "ClientRequestReferer",
    "ClientRequestMethod",
    "EdgeResponseStatus"
  ], var.log_full_client_ip ? ["ClientIP"] : [])
}

# Privacy-preserving default: export firewall/security events only, omit request
# bodies, cookies, authorization data and full query strings. Full client IP is
# opt-in and should have a documented retention/need justification.
resource "cloudflare_logpush_job" "firewall_events" {
  count = var.enable_logpush && var.logpush_destination != "" ? 1 : 0

  zone_id          = var.zone_id
  name             = "clearglass-edge-firewall-events"
  dataset          = "firewall_events"
  destination_conf = var.logpush_destination
  enabled          = true

  output_options {
    field_names      = local.firewall_log_fields
    timestamp_format = "rfc3339"
  }
}
