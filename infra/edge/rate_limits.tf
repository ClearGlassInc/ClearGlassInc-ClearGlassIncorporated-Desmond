# One zone-level http_ratelimit entry point. If the existing commerce stack owns
# this phase for the same zone, migrate/import before enabling this resource.

resource "cloudflare_ruleset" "rate_limits" {
  count = var.enable_rate_limits ? 1 : 0

  zone_id     = var.zone_id
  name        = "ClearGlass perimeter rate limits"
  description = "Static-site and optional dynamic-origin rate limits."
  kind        = "zone"
  phase       = "http_ratelimit"

  rules {
    ref         = "rl_static_assets"
    description = "Static assets per IP/minute"
    expression  = "${local.static_asset_expr} and not (${local.verified_bot}) and not (${local.trusted_ip_expr})"
    action      = var.rate_limit_action
    ratelimit {
      characteristics     = ["ip.src", "cf.colo.id"]
      period              = 60
      requests_per_period = var.static_asset_requests_per_minute
      mitigation_timeout  = var.mitigation_timeout_seconds
    }
  }

  rules {
    ref         = "rl_html_documents"
    description = "HTML/document requests per IP/minute"
    expression  = "${local.html_expr} and not (${local.verified_bot}) and not (${local.trusted_ip_expr})"
    action      = var.rate_limit_action
    ratelimit {
      characteristics     = ["ip.src", "cf.colo.id"]
      period              = 60
      requests_per_period = var.html_requests_per_minute
      mitigation_timeout  = var.mitigation_timeout_seconds
    }
  }

  dynamic "rules" {
    for_each = var.api_hostname != "" ? [1] : []
    content {
      ref         = "rl_login"
      description = "Login/authentication attempts per IP/minute"
      expression  = "(http.host eq \"${var.api_hostname}\" and (${replace(local.login_expr, local.host_scope, "true")}) and not (${local.trusted_ip_expr}))"
      action      = var.rate_limit_action
      ratelimit {
        characteristics     = ["ip.src", "cf.colo.id"]
        period              = 60
        requests_per_period = var.login_requests_per_minute
        mitigation_timeout  = var.mitigation_timeout_seconds
      }
    }
  }

  dynamic "rules" {
    for_each = var.api_hostname != "" ? [1] : []
    content {
      ref         = "rl_password_reset"
      description = "Password reset initiation per IP/10 minutes"
      expression  = "(http.host eq \"${var.api_hostname}\" and lower(http.request.uri.path) contains \"reset\" and not (${local.trusted_ip_expr}))"
      action      = var.rate_limit_action
      ratelimit {
        characteristics     = ["ip.src", "cf.colo.id"]
        period              = 600
        requests_per_period = var.reset_requests_per_10_minutes
        mitigation_timeout  = var.mitigation_timeout_seconds
      }
    }
  }

  dynamic "rules" {
    for_each = var.api_hostname != "" ? [1] : []
    content {
      ref         = "rl_search"
      description = "Search requests per IP/minute"
      expression  = "(http.host eq \"${var.api_hostname}\" and (http.request.uri.path eq \"/search\" or starts_with(http.request.uri.path, \"/api/search\")) and not (${local.trusted_ip_expr}))"
      action      = var.rate_limit_action
      ratelimit {
        characteristics     = ["ip.src", "cf.colo.id"]
        period              = 60
        requests_per_period = var.search_requests_per_minute
        mitigation_timeout  = var.mitigation_timeout_seconds
      }
    }
  }

  dynamic "rules" {
    for_each = var.api_hostname != "" ? [1] : []
    content {
      ref         = "rl_contact_form"
      description = "Contact/form submissions per IP/10 minutes"
      expression  = "(http.host eq \"${var.api_hostname}\" and (http.request.uri.path eq \"/contact\" or starts_with(http.request.uri.path, \"/api/contact\")) and not (${local.trusted_ip_expr}))"
      action      = var.rate_limit_action
      ratelimit {
        characteristics     = ["ip.src", "cf.colo.id"]
        period              = 600
        requests_per_period = var.form_requests_per_10_minutes
        mitigation_timeout  = var.mitigation_timeout_seconds
      }
    }
  }

  dynamic "rules" {
    for_each = var.api_hostname != "" ? [1] : []
    content {
      ref         = "rl_api"
      description = "General API requests per IP/minute"
      expression  = "(http.host eq \"${var.api_hostname}\" and starts_with(http.request.uri.path, \"/api/\") and not (${local.trusted_ip_expr}) and not starts_with(http.request.uri.path, \"/api/webhook\"))"
      action      = var.rate_limit_action
      ratelimit {
        characteristics     = ["ip.src", "cf.colo.id"]
        period              = 60
        requests_per_period = var.api_requests_per_minute
        mitigation_timeout  = var.mitigation_timeout_seconds
      }
    }
  }

  dynamic "rules" {
    for_each = var.admin_hostname != "" ? [1] : []
    content {
      ref         = "rl_admin"
      description = "Administrative requests per IP/minute"
      expression  = "(http.host eq \"${var.admin_hostname}\" and not (${local.trusted_ip_expr}))"
      action      = var.rate_limit_action
      ratelimit {
        characteristics     = ["ip.src", "cf.colo.id"]
        period              = 60
        requests_per_period = var.admin_requests_per_minute
        mitigation_timeout  = var.mitigation_timeout_seconds
      }
    }
  }

  # Webhook traffic is not included here by default. Signed webhook endpoints
  # need sender/signature-aware limits and must never receive browser challenges.
}
