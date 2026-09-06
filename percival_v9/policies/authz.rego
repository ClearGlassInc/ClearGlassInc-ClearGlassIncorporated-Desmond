# Percival v9 authorization policy (OPA sidecar bundle).
# Mirrors percival_v9/internal/policy/engine.py exactly:
#   - deny by default
#   - high/critical risk requires a registered approval (Escalation Gate)
# Data document shape: data.grants[identity] = [{name, risk}, ...]
#                      data.approvals[identity][capability] = true
# Query path (matches the deployment blueprint's POLICY_ENDPOINT):
#   /v1/data/percival/authz/allow
package percival.authz

import rego.v1

default allow := false

gated_risk := {"high", "critical"}

capability(cap) if {
	some grant in data.grants[input.identity]
	grant.name == input.capability
	cap := grant
}

allow if {
	some grant in data.grants[input.identity]
	grant.name == input.capability
	not grant.risk in gated_risk
}

allow if {
	some grant in data.grants[input.identity]
	grant.name == input.capability
	grant.risk in gated_risk
	data.approvals[input.identity][input.capability] == true
}
