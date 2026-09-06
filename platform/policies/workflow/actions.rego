# platform/policies/workflow/actions.rego
#
# Policy-as-code for GitHub Actions workflows. Evaluated by Conftest in the
# `policy-gate` workflow. Two severities:
#
#   deny  -> hard failure, blocks merge (genuinely dangerous misconfigurations)
#   warn  -> advisory, surfaced in the gate but non-blocking (hardening targets)
#
# Promotion path: once every workflow is SHA-pinned, move the pinning rule from
# `warn` to `deny` (see actions_pinning below) to make supply-chain pinning a
# hard gate.
package main

import rego.v1

# ---------------------------------------------------------------------------
# HARD DENY — dangerous misconfigurations the org already complies with.
# ---------------------------------------------------------------------------

# A workflow must declare an explicit top-level permissions block. Omitting it
# inherits the (overly broad) repository default token scope.
deny contains msg if {
	is_workflow
	not input.permissions
	msg := "workflow must declare an explicit top-level 'permissions' block (least privilege)"
}

# Never request write-all — it grants the job a fully privileged GITHUB_TOKEN.
deny contains msg if {
	is_workflow
	input.permissions == "write-all"
	msg := "workflow must not request 'permissions: write-all'; declare least-privilege scopes"
}

# pull_request_target + checkout of the PR head is the classic "pwn request"
# RCE pattern: untrusted code runs with a privileged token.
deny contains msg if {
	is_workflow
	has_trigger("pull_request_target")
	some job in object.get(input, "jobs", {})
	some step in object.get(job, "steps", [])
	startswith(object.get(step, "uses", ""), "actions/checkout")
	ref := object.get(object.get(step, "with", {}), "ref", "")
	contains(ref, "head")
	msg := "pull_request_target must not check out the PR head ref (pwn-request RCE risk)"
}

# ---------------------------------------------------------------------------
# WARN — hardening targets. Promote to deny once the fleet is compliant.
# ---------------------------------------------------------------------------

# Every external action should be pinned to a full 40-char commit SHA. Tags and
# branches are mutable and are a supply-chain attack vector.
warn contains msg if {
	is_workflow
	some job in object.get(input, "jobs", {})
	some step in object.get(job, "steps", [])
	uses := object.get(step, "uses", "")
	uses != ""
	not startswith(uses, "./") # local actions are exempt
	not is_sha_pinned(uses)
	msg := sprintf("action '%s' should be pinned to a full commit SHA", [uses])
}

is_sha_pinned(uses) if regex.match(`@[0-9a-f]{40}$`, uses)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Heuristic: a parsed YAML doc is a workflow if it has both a trigger block and
# `jobs`. NOTE: YAML 1.1 parsers coerce the bare key `on:` to boolean true (the
# "Norway problem"), so after parsing the trigger block surfaces under the key
# "true". We accept either form.
is_workflow if {
	input.jobs
	_ := on_block
}

# The trigger block, regardless of how the YAML key was coerced.
on_block := input.on

on_block := input["true"] if not input.on

# True if the workflow declares the named trigger (handles object and scalar
# forms: `on: { pull_request_target: ... }` and `on: pull_request_target`).
has_trigger(name) if on_block[name]

has_trigger(name) if on_block == name
