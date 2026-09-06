# IMPORTANT: Cloudflare zone ruleset phases are shared entry points. Do not let
# this state and clearglass-commerce/infra/cloudflare independently own the same
# zone/phase. Migrate/import existing rules into one state before enabling.

resource "cloudflare_ruleset" "custom_waf" {
  count = var.enable_custom_waf ? 1 : 0

  zone_id     = var.zone_id
  name        = "ClearGlass public perimeter custom WAF"
  description = "Conservative custom detections for the public hostname."
  kind        = "zone"
  phase       = "http_request_firewall_custom"

  dynamic "rules" {
    for_each = length(concat(var.deny_ipv4_cidrs, var.deny_ipv6_cidrs)) > 0 ? [1] : []
    content {
      ref         = "confirmed_abuse_ip_deny"
      description = "Explicit confirmed-abuse IP/CIDR deny list"
      expression  = "(${local.host_scope} and (${local.denied_ip_expr}) and not (${local.trusted_ip_expr}))"
      action      = "block"
      enabled     = true
    }
  }

  dynamic "rules" {
    for_each = length(concat(var.quarantine_ipv4_cidrs, var.quarantine_ipv6_cidrs)) > 0 ? [1] : []
    content {
      ref         = "temporary_ip_quarantine"
      description = "TEMPORARY quarantine list; managed challenge until the configured future expiry"
      expression  = "(${local.host_scope} and (${local.quarantine_ip_expr}) and not (${local.trusted_ip_expr}))"
      action      = "managed_challenge"
      enabled     = true
    }
  }

  rules {
    ref         = "unexpected_method_static"
    description = "Unexpected HTTP method on static public hostname"
    expression  = "(${local.host_scope} and not http.request.method in {\"GET\" \"HEAD\" \"OPTIONS\"} and not (${local.trusted_ip_expr}))"
    action      = var.custom_waf_action
    enabled     = true
  }

  rules {
    ref         = "path_traversal_and_probe"
    description = "Path traversal, secret-file and common scanner probes"
    expression  = "(${local.host_scope} and not (${local.verified_bot}) and not (${local.trusted_ip_expr}) and (http.request.uri.path contains \"../\" or lower(http.request.uri.path) contains \"%2e%2e\" or starts_with(http.request.uri.path, \"/.git/\") or http.request.uri.path eq \"/.env\" or starts_with(lower(http.request.uri.path), \"/wp-admin\") or starts_with(lower(http.request.uri.path), \"/phpmyadmin\")))"
    action      = var.custom_waf_action
    enabled     = true
  }

  rules {
    ref         = "suspicious_scripted_clients"
    description = "Suspicious scripted-client fingerprints; verified bots and trusted IPs excluded"
    expression  = "(${local.host_scope} and not (${local.verified_bot}) and not (${local.trusted_ip_expr}) and (http.user_agent eq \"\" or lower(http.user_agent) contains \"sqlmap\" or lower(http.user_agent) contains \"nikto\" or lower(http.user_agent) contains \"nuclei\" or lower(http.user_agent) contains \"masscan\" or lower(http.user_agent) contains \"python-requests\" or lower(http.user_agent) contains \"scrapy\"))"
    action      = var.custom_waf_action
    enabled     = true
  }

  rules {
    ref         = "request_metadata_size_anomaly"
    description = "Oversized URI, query string, individual header value, or truncated header set"
    expression  = "(${local.host_scope} and not (${local.trusted_ip_expr}) and (len(raw.http.request.uri) gt ${var.max_uri_bytes} or len(raw.http.request.uri.query) gt ${var.max_query_bytes} or http.request.headers.truncated or any(len(http.request.headers.values[*])[*] gt ${var.max_single_header_value_bytes})))"
    action      = var.custom_waf_action
    enabled     = true
  }

  dynamic "rules" {
    for_each = var.enable_enterprise_body_size_rule ? [1] : []
    content {
      ref         = "request_body_size_anomaly"
      description = "Plan-specific oversized or truncated request-body detection"
      expression  = "(${local.host_scope} and not (${local.trusted_ip_expr}) and (http.request.body.size gt ${var.max_request_body_bytes} or http.request.body.truncated))"
      action      = var.custom_waf_action
      enabled     = true
    }
  }

  dynamic "rules" {
    for_each = var.enable_geo_asn_rules && length(var.denied_countries) > 0 ? [1] : []
    content {
      ref         = "geo_deny_explicit"
      description = "Explicit operator-approved country deny list"
      expression  = "(${local.host_scope} and ip.src.country in {${join(" ", [for c in var.denied_countries : format("\"%s\"", upper(c))])}} and not (${local.trusted_ip_expr}) and not (${local.trusted_asn_expr}))"
      action      = "block"
      enabled     = true
    }
  }

  dynamic "rules" {
    for_each = var.enable_geo_asn_rules && length(var.denied_asns) > 0 ? [1] : []
    content {
      ref         = "asn_deny_explicit"
      description = "Explicit operator-approved confirmed-abuse ASN deny list"
      expression  = "(${local.host_scope} and (${local.denied_asn_expr}) and not (${local.trusted_ip_expr}) and not (${local.trusted_asn_expr}))"
      action      = "block"
      enabled     = true
    }
  }

  dynamic "rules" {
    for_each = var.enable_geo_asn_rules && length(var.challenge_countries) > 0 ? [1] : []
    content {
      ref         = "geo_challenge_explicit"
      description = "Explicit operator-approved country challenge list"
      expression  = "(${local.host_scope} and ip.src.country in {${join(" ", [for c in var.challenge_countries : format("\"%s\"", upper(c))])}} and not (${local.trusted_ip_expr}) and not (${local.trusted_asn_expr}))"
      action      = "managed_challenge"
      enabled     = true
    }
  }

  dynamic "rules" {
    for_each = var.enable_geo_asn_rules && length(var.challenge_asns) > 0 ? [1] : []
    content {
      ref         = "asn_challenge_explicit"
      description = "Explicit operator-approved ASN challenge list"
      expression  = "(${local.host_scope} and (${local.challenge_asn_expr}) and not (${local.trusted_ip_expr}) and not (${local.trusted_asn_expr}))"
      action      = "managed_challenge"
      enabled     = true
    }
  }

  dynamic "rules" {
    for_each = var.enable_geo_asn_rules && length(var.allowed_countries) > 0 && local.restricted_host_expr != "false" ? [1] : []
    content {
      ref         = "restricted_host_country_boundary"
      description = "Challenge API/admin traffic outside the explicit allowed-country set; no public-site default deny"
      expression  = "((${local.restricted_host_expr}) and not (${local.allowed_country_expr}) and not (${local.trusted_ip_expr}) and not (${local.trusted_asn_expr}))"
      action      = "managed_challenge"
      enabled     = true
    }
  }

  dynamic "rules" {
    for_each = var.enable_emergency_mode ? [1] : []
    content {
      ref         = "emergency_high_security"
      description = "TEMPORARY emergency challenge for unverified, untrusted traffic; disable after containment"
      expression  = "(${local.host_scope} and not (${local.verified_bot}) and not (${local.trusted_ip_expr}) and not (${local.trusted_asn_expr}))"
      action      = "managed_challenge"
      enabled     = true
    }
  }
}

resource "cloudflare_ruleset" "managed_waf" {
  count = var.enable_managed_waf ? 1 : 0

  zone_id     = var.zone_id
  name        = "ClearGlass managed WAF deployment"
  description = "Cloudflare Managed + OWASP rulesets with staged override action."
  kind        = "zone"
  phase       = "http_request_firewall_managed"

  rules {
    ref         = "deploy_cloudflare_managed"
    description = "Cloudflare Managed Ruleset"
    expression  = local.host_scope
    action      = "execute"
    action_parameters {
      id = "efb7b8c949ac4650a09736fc376e9aee"
      overrides {
        action = var.managed_waf_override_action
      }
    }
  }

  rules {
    ref         = "deploy_owasp_core"
    description = "Cloudflare OWASP Core Ruleset"
    expression  = local.host_scope
    action      = "execute"
    action_parameters {
      id = "4814384a9e5d4991b9815dcfc25d2f1f"
      overrides {
        action = var.managed_waf_override_action
      }
    }
  }
}
