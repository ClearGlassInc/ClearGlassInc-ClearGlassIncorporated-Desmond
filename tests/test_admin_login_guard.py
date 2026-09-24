"""The admin login's redirect, lockout and route-policy rules must hold.

Both admin login routes redirected off-site. ``/api/login`` accepted any
``next`` starting with ``/``, so ``//evil.example`` sent a freshly signed-in
operator to another host. ``/api/auth/login`` rejected ``//`` but not
``/\\evil.example`` or ``/\\t/evil.example``, which the WHATWG URL parser also
resolves off-site. Both used 307, so the browser re-POSTed the form, token
included, to the target. ``/api/login`` compared tokens with ``!==`` and never
locked out, and the middleware's allow-list left new pages such as
``/playbooks`` reachable without a session.

The rules now live in ``admin/lib/login-guard.ts`` and
``admin/lib/route-policy.ts``, which import nothing from Next.js, so Node's own
test runner checks them. The admin app has no JavaScript test runner of its
own; running the file from here puts it inside the root ``pytest tests/`` gate
that ``scripts/ci_local.py`` already runs.
"""

from __future__ import annotations

import shutil
import subprocess
from functools import cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEST_FILE = ROOT / "admin" / "tests" / "login-guard.test.mjs"
STRIP_TYPES = "--experimental-strip-types"


@cache
def _node_strips_types() -> bool:
    """Node 22.6+ loads .ts with the flag; older Node (ubuntu-latest's 20) cannot."""
    if shutil.which("node") is None:
        return False
    probe = subprocess.run(
        ["node", STRIP_TYPES, "-e", ""], capture_output=True, text=True, timeout=30
    )
    return probe.returncode == 0


def test_the_node_suite_exists() -> None:
    # Guards the guard: a moved test file would otherwise skip silently.
    assert TEST_FILE.is_file()


def test_admin_login_guard_node_suite() -> None:
    if not _node_strips_types():
        pytest.skip("needs Node 22.6+ for TypeScript type stripping")
    result = subprocess.run(
        ["node", STRIP_TYPES, "--no-warnings", "--test", str(TEST_FILE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]


def test_login_routes_use_the_shared_guard() -> None:
    """A route that drops the guard reintroduces the open redirect."""
    for route in ("admin/app/api/login/route.ts", "admin/app/api/auth/login/route.ts"):
        source = (ROOT / route).read_text(encoding="utf-8")
        assert "safeNextPath(" in source, route
        assert "constantTimeEqual(" in source, route
        assert "loginThrottle.isLocked(" in source, route
        assert "token !== expected" not in source, route
        # 307 would replay the POST body, token included, to the redirect target.
        assert "NextResponse.redirect(" in source and "status: 303" in source, route


def test_middleware_uses_the_default_deny_policy() -> None:
    source = (ROOT / "admin" / "middleware.ts").read_text(encoding="utf-8")
    assert 'from "@/lib/route-policy"' in source
    assert "PROTECTED_PREFIXES" not in source
