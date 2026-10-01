"""Test-only telemetry with a closed field allowlist.

An event carrying any field outside ALLOWED_FIELDS is refused with an
exception rather than filtered, so a new field cannot slip into evidence
unreviewed. Values are short strings or numbers describing state, never
keys, payloads, addresses or identities.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ALLOWED_FIELDS = frozenset(
    {
        "environment_id",
        "test_id",
        "run_id",
        "commit_sha",
        "component",
        "event_type",
        "state",
        "timestamp",
        "result",
        "error_class",
        "config_version",
        "gateway_state",
        "tunnel_state",
        "handshake_state",
        "dns_policy_state",
        "credential_state",
        "telemetry_scope",
        "production_equivalence",
    }
)
LABELS = {"telemetry_scope": "TEST_ONLY", "production_equivalence": "NOT_ESTABLISHED"}
MAX_VALUE_LENGTH = 80


class Telemetry:
    def __init__(self, path: Path | None, **context: str):
        self.path = path
        self.context = context
        self.events: list[dict[str, object]] = []
        check(context)

    def emit(self, **fields: object) -> dict[str, object]:
        event: dict[str, object] = {
            **self.context,
            **fields,
            **LABELS,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        }
        check(event)
        self.events.append(event)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as out:
                out.write(json.dumps(event, sort_keys=True) + "\n")
        return event


def check(event: dict[str, object]) -> None:
    unknown = set(event) - ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"telemetry fields outside the allowlist: {sorted(unknown)}")
    for key, value in event.items():
        if not isinstance(value, (str, int, float, bool)):
            raise ValueError(f"telemetry field {key} must be a scalar")
        if isinstance(value, str) and len(value) > MAX_VALUE_LENGTH:
            raise ValueError(f"telemetry field {key} is longer than {MAX_VALUE_LENGTH}")
