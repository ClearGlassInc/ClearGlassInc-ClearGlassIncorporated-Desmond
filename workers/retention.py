"""Bounded, auditable retention worker for ClearGlass Live Signal Fabric."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class RetentionResult:
    evaluated_at: str
    deleted: int
    mode: str


def retention_run(*, execute: bool = False) -> RetentionResult:
    """Default to a no-op; deletion requires explicit operator approval and DB integration."""
    if execute and os.getenv("LIVE_FABRIC_RETENTION_APPROVED") != "true":
        raise PermissionError("retention execution requires recorded owner approval")
    return RetentionResult(
        datetime.now(UTC).isoformat(),
        0,
        "approved-not-integrated" if execute else "dry-run",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(retention_run(execute=args.execute).__dict__, sort_keys=True))
