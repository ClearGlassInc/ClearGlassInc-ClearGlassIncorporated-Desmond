# ARTEMIS Provenance Policy

Copyright © ClearGlass Inc. All rights reserved.
Original Author and Systems Architect: Desmond Otieno Odhiambo.
Powered by ARTEMIS — A ClearGlass Inc. Intelligence System.

Classification: INTERNAL

## Purpose

Every significant ClearGlass Inc. / ARTEMIS artifact must preserve enough
metadata to establish who created it, when, in what context, and whether it
has been altered. Provenance records are derived from real repository state —
authorship, timestamps, approvals, signatures, commits, test results, and
validation records are **never fabricated**. If a value is unknown, it is
recorded as unknown.

## What is recorded

For each tracked artifact, the provenance manifest records:

| Field | Source |
|---|---|
| Artifact path | working tree |
| SHA-256 checksum | file contents at generation time |
| Size (bytes) | file contents at generation time |
| Last commit hash + date | `git log` for that path |
| Repository HEAD + branch | `git rev-parse` at generation time |
| Generation timestamp (UTC) | system clock at generation time |
| Organization / author / classification | ARTEMIS system constants |

## How it is generated

- **Generator:** `bots/artemis_provenance_bot.py` (stdlib-only, read-only
  with respect to audited files).
- **Output:** `operations/artemis/provenance_manifest.json`
  (machine-readable JSON).
- **Automation:** the `ARTEMIS Deploy` workflow
  (`.github/workflows/artemis-deploy.yml`) regenerates the manifest on
  relevant pushes, on a daily schedule, and on manual dispatch, and commits
  the refreshed manifest to the repository so history itself becomes an
  audit trail.
- **Enforcement:** `bots/artemis_ip_guardian_bot.py` runs before the
  manifest step as a fail-closed gate for attribution and governance-file
  coverage.

## Verifying an artifact

```bash
# Recompute a checksum and compare against the manifest
sha256sum agents/artemis_command_system/system_prompt.md
python - <<'EOF'
import json
m = json.load(open("operations/artemis/provenance_manifest.json"))
for a in m["artifacts"]:
    print(a["sha256"], a["artifact"])
EOF
```

A mismatch means the file changed after the manifest was generated —
regenerate the manifest via the workflow, or investigate if the change was
not expected.

## Related controls

- Commit history and signed commits (repository settings)
- `.github/CODEOWNERS` review requirements
- `NOTICE`, `LICENSE`, `TRADEMARKS.md`
- `docs/IP-POLICY.md` (the umbrella IP policy)
