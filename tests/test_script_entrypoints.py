"""Scripts that import a repository package must still run by path.

Workflows and docstrings run these as ``python bots/site_health_bot.py`` or
``python3 tools/tab_icons.py``. Run that way, ``sys.path[0]`` is the script's
own directory, not the repository root, so ``from tools...`` only resolves if
the script puts the root on the path itself.

On 2026-10-06 three scripts gained ``from tools.site_page_policy import ...``
without that bootstrap. ``health-monitor.yml`` then crashed at import on every
run and read the crash as "site unhealthy", and the generators the failing
tests tell you to run (``tools/tab_icons.py``, ``tools/shared_layers.py``)
could not be run at all. The test suite imports these modules from the root,
so nothing noticed.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIRS = ("tools", "bots", "scripts")

# Mimic `python <path>`: the script's directory first, the repository root and
# the working directory nowhere. run_name is not "__main__", so nothing runs
# beyond the module's top level (the health bot's main() fetches live pages).
PROBE = """\
import os, runpy, sys
path = sys.argv[1]
sys.path[:] = [os.path.dirname(path)] + [
    p for p in sys.path if p not in ("", os.getcwd(), sys.argv[2])
]
try:
    runpy.run_path(path, run_name="_entrypoint_probe")
except ModuleNotFoundError as exc:
    print(exc.name)
    sys.exit(3)
"""


def repo_packages() -> set[str]:
    return {
        p.name
        for p in ROOT.iterdir()
        if p.is_dir() and not p.name.startswith(".") and any(p.glob("*.py"))
    }


def entry_points() -> list[Path]:
    """Scripts with a __main__ guard and a top-level import of a repo package."""
    packages = repo_packages()
    found = []
    for directory in SCRIPT_DIRS:
        for path in sorted((ROOT / directory).glob("*.py")):
            source = path.read_text(encoding="utf-8", errors="ignore")
            if "__main__" not in source:
                continue
            imported = set()
            for node in ast.parse(source).body:
                if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    imported.add(node.module.split(".")[0])
                elif isinstance(node, ast.Import):
                    imported.update(alias.name.split(".")[0] for alias in node.names)
            if imported & packages:
                found.append(path)
    return found


def test_the_known_entry_points_are_discovered() -> None:
    names = {p.relative_to(ROOT).as_posix() for p in entry_points()}
    assert {
        "bots/site_health_bot.py",
        "tools/shared_layers.py",
        "tools/tab_icons.py",
    } <= names


@pytest.mark.parametrize(
    "path", entry_points(), ids=lambda p: p.relative_to(ROOT).as_posix()
)
def test_script_resolves_repository_imports_when_run_by_path(
    path: Path, tmp_path: Path
) -> None:
    result = subprocess.run(
        [sys.executable, "-c", PROBE, str(path), str(ROOT)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    missing = result.stdout.strip().splitlines()[-1:] or [""]
    if result.returncode == 3 and missing[0].split(".")[0] not in repo_packages():
        # A third-party dependency its own workflow installs (networkx for the
        # graph verifier). That is not what this test is about.
        pytest.skip(f"third-party module not installed here: {missing[0]}")
    assert result.returncode == 0, (
        f"`python {path.relative_to(ROOT)}` cannot import {missing[0]!r}; "
        "put the repository root on sys.path before importing it\n"
        + result.stderr[-2000:]
    )
