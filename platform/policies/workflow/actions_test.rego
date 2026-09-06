# platform/policies/workflow/actions_test.rego
#
# Unit tests for the workflow policy bundle. Run with:
#   conftest verify --policy platform/policies
# A bad policy can never ship because these tests gate the policy itself.
package main

import rego.v1

# --- deny: missing permissions block ---------------------------------------

test_deny_missing_permissions if {
	some msg in deny with input as {
		"on": {"push": {}},
		"jobs": {"build": {"steps": []}},
	}
	contains(msg, "explicit top-level 'permissions'")
}

test_allow_with_permissions if {
	count({m |
		some m in deny with input as {
			"on": {"push": {}},
			"permissions": {"contents": "read"},
			"jobs": {"build": {"steps": []}},
		}
		contains(m, "explicit top-level")
	}) == 0
}

# --- deny: write-all --------------------------------------------------------

test_deny_write_all if {
	some msg in deny with input as {
		"on": {"push": {}},
		"permissions": "write-all",
		"jobs": {"build": {"steps": []}},
	}
	contains(msg, "write-all")
}

# --- deny: pwn-request ------------------------------------------------------

test_deny_pwn_request if {
	some msg in deny with input as {
		"on": {"pull_request_target": {}},
		"permissions": {"contents": "read"},
		"jobs": {"build": {"steps": [{
			"uses": "actions/checkout@v4",
			"with": {"ref": "${{ github.event.pull_request.head.sha }}"},
		}]}},
	}
	contains(msg, "pwn-request")
}

# --- warn: unpinned action --------------------------------------------------

test_warn_unpinned_action if {
	some msg in warn with input as {
		"on": {"push": {}},
		"permissions": {"contents": "read"},
		"jobs": {"build": {"steps": [{"uses": "actions/checkout@v4"}]}},
	}
	contains(msg, "pinned to a full commit SHA")
}

test_no_warn_for_sha_pinned if {
	count({m |
		some m in warn with input as {
			"on": {"push": {}},
			"permissions": {"contents": "read"},
			"jobs": {"build": {"steps": [{"uses": "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683"}]}},
		}
	}) == 0
}

# Regression: YAML coerces `on:` to the key "true". Rules must still fire when
# the trigger block surfaces under "true" instead of "on".
test_warn_unpinned_action_with_coerced_on_key if {
	some msg in warn with input as {
		"true": {"push": {}},
		"permissions": {"contents": "read"},
		"jobs": {"build": {"steps": [{"uses": "actions/checkout@v5"}]}},
	}
	contains(msg, "pinned to a full commit SHA")
}

test_deny_pwn_request_with_coerced_on_key if {
	some msg in deny with input as {
		"true": {"pull_request_target": {}},
		"permissions": {"contents": "read"},
		"jobs": {"build": {"steps": [{
			"uses": "actions/checkout@v4",
			"with": {"ref": "${{ github.event.pull_request.head.sha }}"},
		}]}},
	}
	contains(msg, "pwn-request")
}

test_no_warn_for_local_action if {
	count({m |
		some m in warn with input as {
			"on": {"push": {}},
			"permissions": {"contents": "read"},
			"jobs": {"build": {"steps": [{"uses": "./.github/actions/local"}]}},
		}
	}) == 0
}
