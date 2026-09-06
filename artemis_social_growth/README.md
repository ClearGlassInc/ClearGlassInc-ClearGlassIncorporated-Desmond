# ClearGlassInc Artemis Social Growth Agent

This package defines a production-oriented, governed social advertising agent.
It can research, plan, draft, repurpose, evaluate, and propose improvements, but
it is **dry-run by default**. Publishing, scheduling, spend, outreach, account
connections, personal-data processing, and self-improvement promotion require
an exact, unexpired human approval.

## Package contents

| File | Purpose |
| --- | --- |
| `agent.json` | Discoverable identity, input contract, permissions, and hard guardrails. |
| `system_prompt.md` | Platform strategy, content workflow, measurement, compliance, and self-improvement contract. |
| `policy.py` | Dependency-free Python reference policy that binds approval to an artifact hash, action, account, expiry, and spend cap. |

## Runtime architecture

Use the prompt behind an authenticated server-side orchestrator. A minimal
production path is:

`authorized analytics -> sanitized context -> AIP workflow/agent -> draft artifact -> policy service -> human approval -> platform adapter -> append-only audit -> outcome/eval dataset`

Foundry can provide governed data integration and ontology-backed campaign
objects; AIP can host the copilot, evaluations, and bounded workflows; Apollo
can promote versioned runtime releases with canary and rollback controls; Gotham
should only supply authorized, sanitized operational context where a legitimate
workflow requires it. These are integration targets, not claims that a tenant or
connector has been provisioned.

Enforce identity, tenant, purpose, compartment, row/entity access, claim IDs,
tool allowlists, cost/time limits, and egress policy outside the model. Store
tokens in the deployment secret manager. Never send raw operational data,
personal data, source prompts, or credentials to a social platform or browser.

## Python policy example

```python
from datetime import datetime, timedelta, timezone

from agents.artemis_social_growth.policy import (
    Action,
    Approval,
    authorize,
    canonical_artifact_hash,
)

artifact = {"content_id": "post-001", "copy": "Approved factual copy"}
approval = Approval(
    approval_id="approval-001",
    artifact_sha256=canonical_artifact_hash(artifact),
    actions=frozenset({Action.PUBLISH}),
    accounts=frozenset({"linkedin:clearglassinc-artemis"}),
    expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
)
decision = authorize(
    action=Action.PUBLISH,
    artifact=artifact,
    account="linkedin:clearglassinc-artemis",
    approval=approval,
)
if not decision.allowed:
    raise PermissionError(f"{decision.code}: {decision.reason}")
```

The adapter must repeat authorization immediately before the platform call,
write an idempotency key and redacted audit event, verify the returned platform
identifier, and stop rather than retry ambiguous writes automatically.

## Status and next setup step

This is an agent definition and policy reference, not a running publisher and
not evidence of connected Palantir or social-platform services. Before runtime
activation, an owner must provide the required campaign inputs, authorize
accounts through official OAuth surfaces, configure the policy/audit services,
and validate platform-specific sandbox or draft-only adapters.
