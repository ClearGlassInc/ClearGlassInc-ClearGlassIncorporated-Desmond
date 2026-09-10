#!/usr/bin/env python3
"""Fail-closed preflight for the gated production deploy.

``auto-store.yml`` runs this as the first step of its ``deploy`` job, inside
the ``production`` environment, before any hook is called. It reads the deploy
configuration from the environment and refuses the release if anything about
it is unsafe or ambiguous.

It validates *shape*, never reachability: nothing here performs a network call,
so the check cannot be defeated by a timeout and cannot itself trigger a
deploy. What it enforces:

* a **bounded change-ticket reference**, so a production release is always
  traceable to an approved change. Free text is rejected — "urgent fix" is not
  an audit trail;
* **absolute HTTPS** for every endpoint. A deploy hook fetched over plaintext
  is a credential handed to anyone on the path, since the key is in the URL;
* **no URL credentials.** ``https://user:secret@host/`` leaks the secret into
  every log line, redirect and error message that echoes the URL, and GitHub's
  secret masking does not cover a value it was never given;
* **no fragment.** A ``#fragment`` is never sent to the server, so a hook
  carrying one is silently not the URL the author believed it was;
* **no query string on the control-plane URL**, which is joined with request
  paths — a stray ``?token=`` there would be dropped or duplicated depending on
  how it is joined. The Render hooks legitimately carry their key as a query
  parameter and are exempt;
* **distinct deploy and rollback hooks.** If they are equal, the rollback path
  redeploys the broken release. That failure only ever surfaces during an
  incident, which is the worst possible moment to discover it.

Every problem with the configuration is reported in one pass, so an operator
fixes them together rather than one failed run at a time. Error text never
includes a configured value — these are secrets, and this output is a public
build log.

Usage::

    python scripts/validate_production_deploy.py    # reads the environment
"""

from __future__ import annotations

import os
import re
import sys
from urllib.parse import urlsplit

# A change ticket must be a bounded reference: a short uppercase system prefix,
# a hyphen, and a number. Bounded is the point — it is checkable by a human and
# resolvable in the tracker.
CHANGE_TICKET_RE = re.compile(r"^[A-Z][A-Z0-9]{1,9}-\d{1,10}$")

REQUIRED_URLS = (
    "RENDER_DEPLOY_HOOK_URL",
    "RENDER_ROLLBACK_HOOK_URL",
    "CONTROL_PLANE_URL",
)

# Endpoints joined with request paths, where a query string cannot survive.
NO_QUERY_STRING = frozenset({"CONTROL_PLANE_URL"})


def _validate_url(name: str, raw: str) -> list[str]:
    """Every structural problem with one configured endpoint."""
    errors: list[str] = []
    try:
        parts = urlsplit(raw)
    except ValueError:
        return [f"{name} must be an absolute HTTPS URL"]

    if parts.scheme != "https" or not parts.hostname:
        errors.append(f"{name} must be an absolute HTTPS URL")
    if parts.username or parts.password:
        errors.append(f"{name} must not contain URL credentials")
    if parts.fragment:
        errors.append(f"{name} must not contain a fragment")
    if parts.query and name in NO_QUERY_STRING:
        errors.append(f"{name} must not contain a query string")
    return errors


def validate_configuration(configuration: dict[str, str]) -> list[str]:
    """Return every reason this configuration must not deploy, or ``[]``.

    Reports names only. A value is never echoed: these are secrets and the
    caller prints this straight into a public workflow log.
    """
    errors: list[str] = []

    ticket = (configuration.get("CHANGE_TICKET") or "").strip()
    if not ticket:
        # Named for the workflow input an operator actually types, not the
        # environment variable it is passed through as.
        errors.append("change_ticket input is required")
    elif not CHANGE_TICKET_RE.match(ticket):
        errors.append("change_ticket must be a bounded reference such as CHG-1234")

    for name in REQUIRED_URLS:
        value = (configuration.get(name) or "").strip()
        if not value:
            errors.append(f"{name} is required")
            continue
        errors.extend(_validate_url(name, value))

    deploy = (configuration.get("RENDER_DEPLOY_HOOK_URL") or "").strip()
    rollback = (configuration.get("RENDER_ROLLBACK_HOOK_URL") or "").strip()
    # Only meaningful once both are configured; two absent hooks are already
    # reported above and are not "the same hook".
    if deploy and rollback and deploy == rollback:
        errors.append("deploy and rollback hooks must be different")

    return errors


def main() -> int:
    errors = validate_configuration(dict(os.environ))
    if errors:
        print("Production deploy configuration rejected:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("Production deploy configuration validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
