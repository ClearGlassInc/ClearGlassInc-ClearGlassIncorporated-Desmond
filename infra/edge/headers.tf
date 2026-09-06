# Response headers are edge-enforced because GitHub Pages cannot reliably set
# application-controlled security headers. CSP remains Report-Only initially.

resource "cloudflare_ruleset" "security_headers" {
  count = var.enable_security_headers ? 1 : 0

  zone_id     = var.zone_id
  name        = "ClearGlass security response headers"
  description = "Browser security headers for the public hostname."
  kind        = "zone"
  phase       = "http_response_headers_transform"

  rules {
    ref         = "public_security_headers"
    description = "Set baseline security headers and CSP Report-Only"
    expression  = local.host_scope
    action      = "rewrite"

    action_parameters {
      headers {
        name      = "Content-Security-Policy-Report-Only"
        operation = "set"
        value     = local.csp
      }
      headers {
        name      = "X-Content-Type-Options"
        operation = "set"
        value     = "nosniff"
      }
      headers {
        name      = "Referrer-Policy"
        operation = "set"
        value     = "strict-origin-when-cross-origin"
      }
      headers {
        name      = "Permissions-Policy"
        operation = "set"
        value     = "geolocation=(), microphone=(), camera=()"
      }
      headers {
        name      = "Cross-Origin-Opener-Policy"
        operation = "set"
        value     = "same-origin-allow-popups"
      }
      headers {
        name      = "Cross-Origin-Resource-Policy"
        operation = "set"
        value     = "same-site"
      }
      headers {
        name      = "X-Frame-Options"
        operation = "set"
        value     = "SAMEORIGIN"
      }
      headers {
        name      = "X-Permitted-Cross-Domain-Policies"
        operation = "set"
        value     = "none"
      }
      headers {
        name      = "Strict-Transport-Security"
        operation = "set"
        value = var.hsts_include_subdomains ? (
          var.hsts_preload ? "max-age=31536000; includeSubDomains; preload" : "max-age=31536000; includeSubDomains"
        ) : "max-age=31536000"
      }
      headers {
        name      = "X-Powered-By"
        operation = "remove"
      }
    }
  }
}
