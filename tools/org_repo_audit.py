#!/usr/bin/env python3
"""Static audit of every reachable ClearGlassInc-family repository.

Clones each repo shallowly, measures what is actually there, then deletes the
clone. Every number written is measured; nothing is assumed or defaulted.
"""
from __future__ import annotations
import json
import subprocess
import shutil
import sys
import tempfile
from pathlib import Path

REPOS = [
 "ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond","ClearGlassInc/Opal-Koboi",
 "ClearGlasslabs/Opal-Koboi","ClearGlassIncorp/hermes-agent","ClearGlasslabs/hermes-agent",
 "ClearGlassIncorp/Opal-Koboi","ClearGlasslabs/ClearCast","ClearGlassInc/Gaurdian",
 "ClearGlasslabs/ClearGlassInc.","ClearGlasslabs/clearglass-marketing-os","ClearGlasslabs/ClearCut",
 "ClearGlasslabs/ClearWire","ClearGlasslabs/claude-agent-sdk-python","ClearGlasslabs/gods-eye-view",
 "ClearGlassInc/clearglass-academy","ClearGlasslabs/nexus-hub","ClearGlasslabs/vscode",
 "ClearGlasslabs/SocialPwned","ClearGlasslabs/claude-code","ClearGlasslabs/claude-ads",
 "ClearGlasslabs/azure-powershell","ClearGlasslabs/agent-reach",
 "ClearGlassInc/clearglass-network-overdrive","ClearGlassInc/demo-repository",
 "ClearGlassInc/safe-add-animations.ps1","ClearGlasslabs/workflow-artifacts",
 "ClearGlasslabs/PwnedPasswordsDownloader","ClearGlasslabs/freedatabreaches",
 "ClearGlasslabs/EmailAddressExtractor","ClearGlasslabs/ClearClean",
 "ClearGlassIncorp/EmailAddressExtractor",
]

def run(cmd, cwd=None, timeout=300):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, check=False)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"

def npm_vulns(root: Path):
    """Advisory counts from lockfiles, resolved without installing."""
    total = {"critical":0,"high":0,"moderate":0,"low":0}
    audited = 0
    for lock in list(root.rglob("package-lock.json"))[:6]:
        if "node_modules" in lock.parts:
            continue
        rc, out, _ = run(["npm","audit","--package-lock-only","--json"],
                         cwd=str(lock.parent), timeout=240)
        if not out.strip():
            continue
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            continue
        meta = (data.get("metadata") or {}).get("vulnerabilities") or {}
        if not meta:
            continue
        audited += 1
        for k in total:
            total[k] += int(meta.get(k, 0))
    return total, audited

def audit(full: str, workdir: Path):
    owner, name = full.split("/", 1)
    dest = workdir / name
    rc, _, err = run(["git","clone","--depth","1","--quiet",
                      f"https://github.com/{full}", str(dest)], timeout=600)
    if rc != 0:
        return {"repository": full, "reachable": "no",
                "note": err.strip().splitlines()[-1][:120] if err.strip() else "clone failed"}

    wf_dir = dest/".github"/"workflows"
    workflows = sorted(list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml"))) if wf_dir.is_dir() else []

    # Workflow files parked outside .github/ never run — the defect in the flagship repo.
    stray = []
    for d in ("workflows",):
        p = dest/d
        if p.is_dir():
            stray += list(p.glob("*.yml")) + list(p.glob("*.yaml"))

    # Unpinned external actions: a mutable tag can be repointed by its owner.
    import re
    SHA = re.compile(r"@[0-9a-f]{40}$")
    unpinned = 0
    for wf in workflows:
        try:
            text = wf.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for ref in re.findall(r"uses:\s*([^\s#]+)", text):
            if ref.startswith("./") or ref.startswith("docker://"):
                continue
            if not SHA.search(ref):
                unpinned += 1

    py_manifests = [p for p in dest.rglob("requirements*.txt") if "node_modules" not in p.parts]
    py_manifests += [p for p in dest.rglob("pyproject.toml") if "node_modules" not in p.parts]
    pkgs = [p for p in dest.rglob("package.json") if "node_modules" not in p.parts]
    locks = [p for p in dest.rglob("package-lock.json") if "node_modules" not in p.parts]

    # "Bots" as the user's own pattern list defines them.
    bots = 0
    for pat in ("bots/*.py","scripts/osint/*.py","deploy/*.sh","security/*.py"):
        bots += len(list(dest.glob(pat)))
    bots += len(workflows)

    tests = len([p for p in dest.rglob("test_*.py") if "node_modules" not in p.parts])
    tests += len([p for p in dest.rglob("*.test.*") if "node_modules" not in p.parts])

    vulns, audited = npm_vulns(dest) if locks else ({"critical":0,"high":0,"moderate":0,"low":0}, 0)

    rc, head, _ = run(["git","log","-1","--format=%cI"], cwd=str(dest))
    shutil.rmtree(dest, ignore_errors=True)

    return {
        "repository": full, "reachable": "yes",
        "workflows_registered": len(workflows),
        "workflows_stray_unrunnable": len(stray),
        "unpinned_actions": unpinned,
        "python_manifests": len(py_manifests),
        "node_packages": len(pkgs), "node_lockfiles": len(locks),
        "packages_without_lockfile": max(0, len(pkgs) - len(locks)),
        "bots_active": bots,
        "test_files": tests,
        "vuln_critical": vulns["critical"], "vuln_high": vulns["high"],
        "vuln_moderate": vulns["moderate"], "vuln_low": vulns["low"],
        "lockfiles_audited": audited,
        "last_commit": head.strip(),
    }

def main():
    out = []
    with tempfile.TemporaryDirectory(prefix="cg-audit-") as tmp:
        workdir = Path(tmp)
        for i, repo in enumerate(REPOS, 1):
            print(f"[{i}/{len(REPOS)}] {repo}", flush=True)
            try:
                out.append(audit(repo, workdir))
            except Exception as exc:
                out.append({"repository": repo, "reachable": "error", "note": str(exc)[:120]})
            print("   ", json.dumps(out[-1])[:180], flush=True)
    Path(sys.argv[1]).write_text(json.dumps(out, indent=2))
    print("wrote", sys.argv[1])

if __name__ == "__main__":
    main()
