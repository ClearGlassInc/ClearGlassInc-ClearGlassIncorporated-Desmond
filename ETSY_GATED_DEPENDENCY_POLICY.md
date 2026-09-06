# Etsy Gated Dependency Policy

> Mandatory execution guard for the ClearGlass commerce system.

## Policy statement

Etsy is a hard-gated dependency. No downstream Etsy-dependent workflow may start, resume, enqueue remote work, or perform a mutation unless the integration is proven fully healthy at execution time.

## Required READY evidence

The dependency gate opens only when every condition below is true:

1. Etsy OAuth authentication is active.
2. The access session and token are valid and unexpired.
3. Authorization has not been revoked.
4. The authenticated identity resolves to the intended owner-approved shop.
5. The server-derived shop ID and shop name match the configured ClearGlass mapping.
6. Every permission required by the requested workflow is present.
7. Synchronization configuration and store mapping are valid.
8. The latest non-destructive health check passed.
9. Audit logging and the Etsy kill switch are operational.
10. Required production owner approval remains valid.

A partial pass is a failure. Unknown state is a failure. Cached historical success is not sufficient when the current connection cannot be verified.

## Mandatory preflight gate

Every Etsy-dependent workflow must execute this gate immediately before its first downstream action:

```text
ETSY_DEPENDENCY_GATE =
  authentication == VALID
  AND token_status == ACTIVE
  AND authorization == NOT_REVOKED
  AND intended_shop_identity == VERIFIED
  AND required_permissions == PRESENT
  AND connection_health == HEALTHY
  AND sync_configuration == VALID
  AND audit_logging == HEALTHY
  AND kill_switch == AVAILABLE
  AND owner_approval == VALID
```

Only an exact `true` result may return `ALLOW`. Every other result returns `BLOCK`.

## Workflows covered

The gate applies to all Etsy-dependent operations, including:

- Product import or export
- Listing creation, editing, renewal, activation, deactivation, or publication
- Inventory or price synchronization
- Catalog reconciliation
- Order, receipt, or transaction retrieval
- Order modification, cancellation, refund, or fulfilment updates
- Buyer messaging
- Analytics or reporting that requires authenticated Etsy data
- Scheduled marketplace jobs
- Retry, replay, queue-consumer, webhook, and recovery workflows

No caller may bypass the gate because an earlier workflow stage passed it.

## Immediate blocking conditions

Execution must stop immediately when any of the following is detected:

```text
MISSING_CREDENTIAL_REFERENCE
MISSING_OAUTH_CONNECTION
AUTHENTICATION_REQUIRED
SESSION_EXPIRED
TOKEN_EXPIRED
TOKEN_REFRESH_FAILED
ACCESS_REVOKED
MFA_OR_MANUAL_APPROVAL_REQUIRED
SHOP_NOT_FOUND
SHOP_IDENTITY_MISMATCH
SHOP_SELECTION_REQUIRED
REQUIRED_SCOPE_MISSING
PARTIAL_PERMISSION_SET
CONNECTION_UNHEALTHY
API_AUTHORIZATION_FAILURE
SYNC_MAPPING_INVALID
AUDIT_LOGGING_UNHEALTHY
KILL_SWITCH_UNAVAILABLE
OWNER_APPROVAL_MISSING_OR_EXPIRED
UNKNOWN_CONNECTION_STATE
```

## Blocking response contract

A blocked workflow must:

1. Abort before any downstream Etsy operation.
2. Prevent new Etsy-dependent jobs from being accepted.
3. Pause or quarantine queued Etsy-dependent work.
4. Emit a secret-safe audit event.
5. Return one user-facing remediation request containing only the minimum action required.
6. Keep all remote mutation capabilities disabled.

Required response shape:

```text
Decision: BLOCK
Dependency: Etsy
Current state: <verified state>
Blocking condition: <single primary error code>
Affected workflow: <workflow identifier>
Required user action: <exact minimum remediation>
Automatic retry permitted: YES | NO
Retry condition: <evidence required before retry>
Audit event ID: <non-secret identifier>
Timestamp: <UTC timestamp>
```

## User-facing remediation rules

The request must be direct and specific:

- Missing connection: ask the user to complete Etsy OAuth through the approved connection surface.
- Expired or failed refresh: ask the user to reconnect Etsy.
- Revoked access: ask the user to reauthorize the ClearGlass Etsy application.
- MFA or Etsy approval required: ask the user to complete that step inside Etsy.
- Shop mismatch: report the expected and server-derived non-secret shop identifiers and require explicit correction or selection.
- Missing permission: name the missing capability and require reauthorization with the approved least-privilege scope.
- Unhealthy connection: report the health-check failure and require successful revalidation.

Never request passwords, two-factor codes, recovery codes, session cookies, access tokens, refresh tokens, API secrets, or private customer information in chat, source control, logs, pull requests, or support output.

## Recovery and retry

A blocked workflow may resume only after the entire dependency gate is rerun from the beginning and returns `ALLOW`. Clearing one error does not permit execution based on stale results from other gates.

Automatic retry is permitted only for transient network or Etsy service failures and only under the approved bounded backoff policy. Authentication, authorization, identity, permission, mapping, and owner-approval failures require explicit recovery evidence before retry.

## Audit requirements

Each gate evaluation must record:

```text
audit_event_id
workflow_id
clearGlass_store_id
environment
shop_id_non_secret
gate_decision
gate_results_without_secrets
primary_error_code
required_remediation
connection_verification_timestamp
policy_version
```

Secret values and buyer personal data must never be recorded.

## Final invariant

```text
ETSY_READY != TRUE  =>  ALL_ETSY_DOWNSTREAM_EXECUTION_DISABLED
```

There are no exceptions, fallback credentials, permissive modes, or partial-readiness shortcuts.

---

*ClearGlass Inc. · Factory Connect · Fail Closed by Default*