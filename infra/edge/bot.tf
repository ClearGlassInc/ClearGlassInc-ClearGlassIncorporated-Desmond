# Bot-management zone settings are independently stateful. The existing commerce
# Cloudflare stack can also manage this resource, so keep this disabled until
# Terraform state ownership and Cloudflare plan support are explicitly confirmed.

resource "cloudflare_bot_management" "public_perimeter" {
  count = var.enable_bot_management ? 1 : 0

  zone_id                         = var.zone_id
  sbfm_definitely_automated       = var.bot_definitely_automated_action
  sbfm_likely_automated           = var.bot_likely_automated_action
  sbfm_verified_bots              = "allow"
  sbfm_static_resource_protection = false
  optimize_wordpress              = false
}
