locals {
  denied_ip_expr = length(concat(var.deny_ipv4_cidrs, var.deny_ipv6_cidrs)) > 0 ? format(
    "ip.src in {%s}",
    join(" ", concat(var.deny_ipv4_cidrs, var.deny_ipv6_cidrs))
  ) : "false"

  quarantine_ip_expr = length(concat(var.quarantine_ipv4_cidrs, var.quarantine_ipv6_cidrs)) > 0 ? format(
    "ip.src in {%s}",
    join(" ", concat(var.quarantine_ipv4_cidrs, var.quarantine_ipv6_cidrs))
  ) : "false"

  trusted_asn_expr = length(var.trusted_asns) > 0 ? format(
    "ip.src.asnum in {%s}",
    join(" ", [for asn in var.trusted_asns : tostring(asn)])
  ) : "false"

  denied_asn_expr = length(var.denied_asns) > 0 ? format(
    "ip.src.asnum in {%s}",
    join(" ", [for asn in var.denied_asns : tostring(asn)])
  ) : "false"

  challenge_asn_expr = length(var.challenge_asns) > 0 ? format(
    "ip.src.asnum in {%s}",
    join(" ", [for asn in var.challenge_asns : tostring(asn)])
  ) : "false"

  restricted_host_expr = length(compact([var.api_hostname, var.admin_hostname])) > 0 ? join(
    " or ",
    [for host in compact([var.api_hostname, var.admin_hostname]) : format("http.host eq \"%s\"", host)]
  ) : "false"

  allowed_country_expr = length(var.allowed_countries) > 0 ? format(
    "ip.src.country in {%s}",
    join(" ", [for country in var.allowed_countries : format("\"%s\"", upper(country))])
  ) : "true"
}
