terraform {
  required_version = ">= 1.6.0"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.40"
    }
  }
}

provider "cloudflare" {
  # Authentication is read from CLOUDFLARE_API_TOKEN.
  # Never place provider credentials in Terraform files or committed tfvars.
}

locals {
  host_scope = "http.host eq \"${var.public_hostname}\""

  verified_bot = "cf.client.bot"

  trusted_ip_expr = length(concat(var.trusted_ipv4_cidrs, var.trusted_ipv6_cidrs)) > 0 ? format(
    "ip.src in {%s}",
    join(" ", concat(var.trusted_ipv4_cidrs, var.trusted_ipv6_cidrs))
  ) : "false"

  static_asset_expr = "(${local.host_scope} and http.request.method in {\"GET\" \"HEAD\"} and (http.request.uri.path matches \"(?i)\\\\.(?:css|js|mjs|json|png|jpe?g|gif|webp|svg|ico|woff2?|ttf|otf|map|xml|txt|pdf)$\"))"
  html_expr         = "(${local.host_scope} and http.request.method in {\"GET\" \"HEAD\"} and not (${local.static_asset_expr}))"
  login_expr        = "(${local.host_scope} and (http.request.uri.path eq \"/login\" or starts_with(http.request.uri.path, \"/api/login\") or starts_with(http.request.uri.path, \"/api/auth/\")))"
  reset_expr        = "(${local.host_scope} and lower(http.request.uri.path) contains \"reset\")"
  search_expr       = "(${local.host_scope} and (http.request.uri.path eq \"/search\" or starts_with(http.request.uri.path, \"/api/search\")))"
  form_expr         = "(${local.host_scope} and (http.request.uri.path eq \"/contact\" or starts_with(http.request.uri.path, \"/api/contact\")))"
  api_expr          = "(${local.host_scope} and starts_with(http.request.uri.path, \"/api/\"))"
  admin_expr        = "(${local.host_scope} and starts_with(http.request.uri.path, \"/admin\"))"
  webhook_expr      = "(${local.host_scope} and (starts_with(http.request.uri.path, \"/webhooks\") or starts_with(http.request.uri.path, \"/api/webhook\")))"

  # Existing repository integrations require these CSP sources. Keep report-only
  # until browser validation demonstrates that enforcement will not break pages.
  csp = join(" ", [
    "default-src 'self';",
    "base-uri 'self';",
    "object-src 'none';",
    "frame-ancestors 'self';",
    "form-action 'self' https://formspree.io;",
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com;",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com;",
    "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com data:;",
    "img-src 'self' data: blob: https:;",
    "media-src 'self' https:;",
    "connect-src 'self' https://formspree.io https://api.github.com;",
    "frame-src 'self' https://www.youtube-nocookie.com;",
    "manifest-src 'self';",
    "worker-src 'self' blob:;",
    "upgrade-insecure-requests"
  ])
}
