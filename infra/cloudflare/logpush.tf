# Logpush — the evidence pipeline that makes the observe-first rollout possible.
#
# Ships firewall events (what rules matched, at what action) and sampled HTTP
# requests to your sink (R2 / S3 / Splunk / an HTTPS collector). While rules are
# in "log", these datasets are how you SEE what each rule WOULD have blocked
# before you promote it. Gated on `logpush_destination` being set.

variable "logpush_destination" {
  type        = string
  description = "Logpush destination URI (e.g. r2://bucket/path?... or https://...). Empty disables Logpush."
  default     = ""
  sensitive   = true
}

resource "cloudflare_logpush_job" "firewall_events" {
  count            = var.logpush_destination == "" ? 0 : 1
  zone_id          = var.zone_id
  name             = "cg-firewall-events"
  dataset          = "firewall_events"
  destination_conf = var.logpush_destination
  enabled          = true
  # Fields that let you separate real users from scrapers during tuning.
  output_options {
    field_names = [
      "Datetime", "Action", "RuleID", "Source", "ClientIP", "ClientASN",
      "ClientCountry", "ClientRequestHTTPHost", "ClientRequestPath",
      "ClientRequestQuery", "ClientRequestUserAgent", "ClientRequestReferer",
      "EdgeResponseStatus", "ClientRequestMethod",
    ]
    timestamp_format = "rfc3339"
  }
}

resource "cloudflare_logpush_job" "http_requests" {
  count            = var.logpush_destination == "" ? 0 : 1
  zone_id          = var.zone_id
  name             = "cg-http-requests"
  dataset          = "http_requests"
  destination_conf = var.logpush_destination
  enabled          = true
  # Sampled to keep volume down; raise for a short window during active tuning.
  output_options {
    field_names = [
      "EdgeStartTimestamp", "ClientIP", "ClientASN", "ClientCountry",
      "ClientRequestHost", "ClientRequestURI", "ClientRequestUserAgent",
      "ClientRequestReferer", "EdgeResponseStatus", "EdgeResponseBytes",
      "WAFAction", "BotScore", "BotScoreSrc", "JA4",
    ]
    sample_rate      = 0.1
    timestamp_format = "rfc3339"
  }
}
