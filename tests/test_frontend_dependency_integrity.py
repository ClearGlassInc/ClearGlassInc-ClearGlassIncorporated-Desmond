# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
"""The Next.js apps must declare dependency sets that can actually install.

This exists because they once did not. On 2026-09-15 an auto-merged Dependabot
PR (#48) raised `react` to 19.3.0 in `admin/` while leaving `react-dom` at
18.3.1, because Dependabot groups react with `@types/react` but treats
`react-dom` as a separate update. The result was an app that `npm ci` refuses
outright:

    Conflicting peer dependency: react@18.3.1
    peer react@"^18.3.1" from react-dom@18.3.1

It merged unnoticed because GitHub Actions was not dispatching runners, so
`Commerce Frontend CI` — the gate that runs `npm ci` and would have caught it in
seconds — reported nothing at all.

These checks are deliberately pure-Python and read the committed manifests and
lockfiles directly. They need no network, no `node_modules`, and no runner, so
they hold even while Actions is down, which is precisely when a broken manifest
can reach `main` unchallenged. They are not a substitute for `npm ci`; they are
the part of it that can run anywhere, covering the one failure mode that has
actually bitten this repository.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APPS = ("storefront", "admin")

#: Packages whose major versions must agree within one app. React and react-dom
#: share internals and are published in lockstep; a mismatched pair is not a
#: version skew you can ship, it is an app that will not start.
LOCKSTEP_GROUPS: tuple[tuple[str, ...], ...] = (
    ("react", "react-dom"),
    ("@types/react", "@types/react-dom"),
)


def manifest(app: str) -> dict:
    return json.loads((ROOT / app / "package.json").read_text(encoding="utf-8"))


def lockfile(app: str) -> dict:
    return json.loads((ROOT / app / "package-lock.json").read_text(encoding="utf-8"))


def declared(app: str) -> dict[str, str]:
    """Every direct dependency the app declares, runtime and dev together."""
    data = manifest(app)
    return {**data.get("dependencies", {}), **data.get("devDependencies", {})}


def major(spec: str) -> int:
    """Major version from a semver range (`^19.3.0` -> 19). Raises on garbage."""
    cleaned = spec.lstrip("^~>=< ").split(".", 1)[0]
    return int(cleaned)


def resolved(app: str, package: str) -> str | None:
    """The version the lockfile actually pins for a top-level package."""
    return lockfile(app).get("packages", {}).get(f"node_modules/{package}", {}).get("version")


@pytest.mark.parametrize("app", APPS)
def test_the_app_has_a_manifest_and_a_lockfile(app: str) -> None:
    """A lockfile-respecting install needs both; CI runs `npm ci`, not `npm install`."""
    assert (ROOT / app / "package.json").is_file(), f"{app} has no package.json"
    assert (ROOT / app / "package-lock.json").is_file(), (
        f"{app} has no package-lock.json; `npm ci` cannot run without one"
    )


@pytest.mark.parametrize("app", APPS)
@pytest.mark.parametrize("group", LOCKSTEP_GROUPS, ids=lambda g: "+".join(g))
def test_declared_lockstep_packages_share_a_major_version(app: str, group: tuple[str, ...]) -> None:
    """The exact check that would have caught PR #48 before it merged."""
    deps = declared(app)
    present = {name: deps[name] for name in group if name in deps}
    if len(present) < 2:
        pytest.skip(f"{app} declares fewer than two of {group}")

    majors = {name: major(spec) for name, spec in present.items()}
    assert len(set(majors.values())) == 1, (
        f"{app}/package.json declares mismatched majors for packages that must move "
        f"together: {majors}. These share internals and are published in lockstep — "
        f"`npm ci` will refuse the install with ERESOLVE. Raise them in one change."
    )


@pytest.mark.parametrize("app", APPS)
@pytest.mark.parametrize("group", LOCKSTEP_GROUPS, ids=lambda g: "+".join(g))
def test_resolved_lockstep_packages_share_a_major_version(app: str, group: tuple[str, ...]) -> None:
    """The manifest can agree while the lockfile still pins a broken pair.

    A lockfile regenerated against a stale manifest, or hand-edited, can resolve
    versions the manifest never asked for — and `npm ci` installs the lockfile,
    not the manifest. So the pin is checked on its own.
    """
    pins = {name: resolved(app, name) for name in group}
    present = {name: version for name, version in pins.items() if version}
    if len(present) < 2:
        pytest.skip(f"{app} locks fewer than two of {group}")

    majors = {name: major(version) for name, version in present.items()}
    assert len(set(majors.values())) == 1, (
        f"{app}/package-lock.json pins mismatched majors: {majors}. `npm ci` installs "
        f"the lockfile, so this is what would actually be installed. Regenerate the "
        f"lockfile with npm after aligning package.json — never edit it by hand."
    )


@pytest.mark.parametrize("app", APPS)
def test_the_lockfile_agrees_with_the_manifest(app: str) -> None:
    """A lockfile that no longer satisfies the manifest makes `npm ci` fail."""
    root_entry = lockfile(app).get("packages", {}).get("", {})
    locked_deps = {
        **root_entry.get("dependencies", {}),
        **root_entry.get("devDependencies", {}),
    }
    if not locked_deps:
        pytest.skip(f"{app} lockfile records no root dependency block")

    drifted = {
        name: (spec, locked_deps[name])
        for name, spec in declared(app).items()
        if name in locked_deps and locked_deps[name] != spec
    }
    assert not drifted, (
        f"{app}: package-lock.json records different ranges than package.json for "
        f"{ {k: {'package.json': v[0], 'lock': v[1]} for k, v in drifted.items()} }. "
        f"`npm ci` fails when the two disagree. Run `npm install --package-lock-only`."
    )


@pytest.mark.parametrize("app", APPS)
def test_react_and_next_are_declared_at_all(app: str) -> None:
    """Guard the guard: the checks above pass vacuously on an empty manifest."""
    deps = declared(app)
    for required in ("next", "react", "react-dom"):
        assert required in deps, f"{app} no longer declares {required}; these are Next.js apps"
