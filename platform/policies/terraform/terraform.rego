# platform/policies/terraform/terraform.rego
#
# Guardrails for Terraform source (HCL parsed to JSON by Conftest's hcl2 parser).
# These catch the most common IaC footguns before plan/apply.
package main

import rego.v1

# Deny security groups open to the world on all ports.
deny contains msg if {
	some r in input.resource.aws_security_group_rule
	r.cidr_blocks[_] == "0.0.0.0/0"
	r.from_port == 0
	r.to_port == 0
	msg := "aws_security_group_rule must not open all ports (0-0) to 0.0.0.0/0"
}

# Warn on any provider/module not version-constrained — drift and surprise upgrades.
warn contains msg if {
	some name, block in input.terraform[_].required_providers
	not block.version
	msg := sprintf("provider '%s' should declare a version constraint", [name])
}

# Sensitive variables must be marked sensitive.
warn contains msg if {
	some name, block in input.variable
	regex.match(`(?i)(secret|key|token|password)`, name)
	not block.sensitive
	msg := sprintf("variable '%s' looks sensitive and should set sensitive = true", [name])
}
