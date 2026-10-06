#!/usr/bin/env python3
"""Decide, run, verify and report the auto-fix for a failed CI run on a pull request.

``auto-fix.yml`` drives this in three jobs with three trust levels:

``plan``     trusted, read-only. Reads the workflow_run, the PR and its commits and
             decides whether to act, which fixers to run, and whether the iteration
             cap leaves room for another fix commit.
``fix``      UNTRUSTED. Runs the fixers against the PR head with a read-only token
             and no secrets, then writes ``patch.diff`` and ``report.json``. Nothing
             it produces is believed until ``apply`` has checked it.
``apply``    trusted, the only job that can write. Validates the patch against the
             repository's own automation policy (``scripts/automation_governance.py``,
             loaded from the default branch, never from the PR), applies it, proves
             generated-block edits stayed inside their markers, commits it as a
             Verified commit pinned to the failing head (a branch that moved is left
             alone), and upserts one PR comment.

Fixers are deterministic tools only (ruff's safe fixes, the repository's own
generators, a component's own ``lint:fix`` / ``format`` scripts). Nothing here asks
a model to write code; ``codex-autofix.yml`` is the manual, LLM-backed path.

Stdlib only, no network: the workflow fetches the API payloads with ``gh`` and
passes them in as files, which keeps every decision here testable offline.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve()
# Import the policy and the component table from the checkout this file came
# from. In auto-fix.yml that is always the default branch, never the PR, so a
# pull request cannot loosen the rules it is being checked against.
for _path in (HERE.parent, HERE.parents[1]):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from automation_governance import POLICY_VERSION, protected_reason  # noqa: E402
from components import COMPONENTS  # noqa: E402

COMMIT_PREFIX = "auto-fix:"
RUN_TRAILER = "Auto-Fix-Run:"
OPT_OUT_LABEL = "no-autofix"
DEFAULT_MAX_ITERATIONS = 2
#: Integration branches are never auto-fixed, even when a PR is opened from one.
PROTECTED_BRANCHES = frozenset({"main", "staging"})
MAX_FILES = 200
MAX_CHANGED_LINES = 4000
MAX_ISSUES_SHOWN = 50

#: Files the repository's generators own outright. A fix may rewrite them whole.
GENERATED_FILES = frozenset(
    {
        "sitemap.xml",
        "feed.xml",
        "data/seo/page-intents.json",
        "data/site-index.json",
        "SITE_WIRING_PLAN.md",
        "blog/posts.json",
    }
)
#: Generated regions inside hand-written pages (tools/internal_links.py,
#: tools/insights_index.py). An edit to a page the PR did not touch is accepted
#: only if everything outside these blocks is byte-identical afterwards.
GENERATED_BLOCK = re.compile(r"<!-- (cg-[a-z-]+):start -->.*?<!-- \1:end -->", re.DOTALL)

#: The repository's generators, in the order CI's search-integrity job checks them.
GENERATORS = (
    "tools/generate_search_assets.py",
    "tools/internal_links.py",
    "tools/insights_index.py",
)

STACK_JOB = re.compile(r"^Stack \((?P<component>[^)]+)\) / (?P<stage>.+)$")

#: TypeScript diagnostics common enough to deserve a first suggestion.
TS_HINTS = {
    "TS2304": "Name is not declared: add the missing import or declaration.",
    "TS2305": "Module has no such export: check the export name or the module path.",
    "TS2307": "Module not found: check the import path, or add the dependency to package.json.",
    "TS2322": "Type mismatch: make the value match the declared type, or widen the type on purpose.",
    "TS2339": "Property does not exist on the type: check the spelling or extend the type.",
    "TS2345": "Argument type mismatch: convert the argument or correct the parameter type.",
    "TS2532": "Value may be undefined: narrow it with a check or use optional chaining.",
    "TS18048": "Value may be undefined: narrow it with a check or use optional chaining.",
    "TS6133": "Declared but never read: remove it, or prefix with _ if it must stay.",
    "TS7006": "Implicit any: annotate the parameter type.",
    "TS7031": "Implicit any in a destructured binding: annotate the parameter type.",
}


# ── plan ───────────────────────────────────────────────────────────────────


@dataclass
class Plan:
    act: bool
    reason: str
    mode: str = "skip"  # fix | report | skip
    pr: int = 0
    branch: str = ""
    head_sha: str = ""
    fixers: list[str] = field(default_factory=list)
    node_components: list[str] = field(default_factory=list)
    failed_jobs: list[dict[str, str]] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = DEFAULT_MAX_ITERATIONS

    def outputs(self) -> dict[str, str]:
        return {
            "act": "true" if self.act else "false",
            "reason": self.reason,
            "mode": self.mode,
            "pr": str(self.pr),
            "branch": self.branch,
            "head_sha": self.head_sha,
            "fixers": ",".join(self.fixers),
            "node_components": ",".join(self.node_components),
            "iteration": str(self.iteration),
            "max_iterations": str(self.max_iterations),
        }


def is_bot(user: dict[str, Any]) -> bool:
    return user.get("type") == "Bot" or str(user.get("login", "")).endswith("[bot]")


def count_autofix_commits(commits: list[dict[str, Any]]) -> int:
    """Fix commits already on the PR: ours carry the run trailer; earlier ones were
    bot-authored. A human commit merely titled "auto-fix:" does not use the budget."""
    count = 0
    for item in commits:
        message = (item.get("commit") or {}).get("message", "")
        if not message.startswith(COMMIT_PREFIX):
            continue
        if RUN_TRAILER in message or str((item.get("author") or {}).get("login", "")).endswith("[bot]"):
            count += 1
    return count


def fixers_for(failed_jobs: list[dict[str, str]]) -> tuple[list[str], list[str]]:
    """Map failing CI job names to (fixers, node components needing diagnostics)."""
    fixers: list[str] = []
    node: list[str] = []

    def add(item: str) -> None:
        if item not in fixers:
            fixers.append(item)

    for job in failed_jobs:
        name = job["name"]
        if name == "Lint (ruff)":
            add("ruff")
        elif name == "Search discovery and structured data":
            add("generators")
        match = STACK_JOB.match(name)
        if match and match.group("stage") == "Lint & types":
            component = match.group("component")
            spec = COMPONENTS.get(component)
            if spec is None:
                continue
            if spec["language"] == "python":
                add("ruff")
            elif spec["language"] == "node":
                add(f"node:{component}")
                if component not in node:
                    node.append(component)
    return fixers, node


def plan(
    run: dict[str, Any],
    jobs: list[dict[str, Any]],
    pr: dict[str, Any] | None,
    commits: list[dict[str, Any]],
    *,
    repository: str,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    enabled: bool = True,
) -> Plan:
    """Fail closed: every branch that is not clearly safe returns act=False."""
    if not enabled:
        return Plan(False, "auto-fix disabled by the AUTOFIX_ENABLED repository variable")
    if run.get("conclusion") != "failure":
        return Plan(False, f"CI concluded {run.get('conclusion')!r}, not failure")
    if run.get("event") not in {"pull_request", "workflow_dispatch"}:
        return Plan(False, f"run event {run.get('event')!r} is not a pull request run")
    head_repo = (run.get("head_repository") or {}).get("full_name")
    if head_repo != repository:
        return Plan(False, f"head repository {head_repo!r} is a fork; auto-fix never writes to forks")
    if run.get("head_branch") in PROTECTED_BRANCHES:
        return Plan(False, f"{run.get('head_branch')!r} is an integration branch; it is never auto-fixed")
    if not pr:
        return Plan(False, f"no open pull request for branch {run.get('head_branch')!r}")
    if (pr.get("head") or {}).get("repo", {}).get("full_name") != repository:
        return Plan(False, "pull request head is a fork")
    if is_bot(pr.get("user") or {}):
        return Plan(False, f"pull request author {pr['user'].get('login')} is a bot")
    labels = {label.get("name") for label in pr.get("labels") or []}
    if OPT_OUT_LABEL in labels:
        return Plan(False, f"pull request carries the {OPT_OUT_LABEL!r} label")
    if (pr.get("head") or {}).get("sha") != run.get("head_sha"):
        return Plan(False, "the branch moved after this CI run; the newer run decides")

    failed = [
        {"name": job.get("name", ""), "url": job.get("html_url", ""), "conclusion": job.get("conclusion", "")}
        for job in jobs
        if job.get("conclusion") in {"failure", "timed_out"}
    ]
    iteration = count_autofix_commits(commits)
    fixers, node = fixers_for(failed)
    base = Plan(
        True,
        "",
        pr=int(pr["number"]),
        branch=str(pr["head"]["ref"]),
        head_sha=str(run["head_sha"]),
        node_components=node,
        failed_jobs=failed,
        iteration=iteration,
        max_iterations=max_iterations,
    )
    if iteration >= max_iterations:
        base.mode = "report"
        base.reason = f"iteration cap reached ({iteration}/{max_iterations}); reporting only"
    elif not fixers:
        base.mode = "report"
        base.reason = "no failing check has a deterministic fixer; reporting only"
    else:
        base.mode = "fix"
        base.fixers = fixers
        base.reason = f"running {', '.join(fixers)}"
    return base


# ── fix (untrusted job) ──────────────────────────────────────────────────


def sh(command: list[str], cwd: Path) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def package_scripts(component_dir: Path) -> dict[str, str]:
    try:
        return json.loads((component_dir / "package.json").read_text(encoding="utf-8")).get("scripts", {})
    except (OSError, ValueError):
        return {}


def changed_python(changed: list[str], root: Path) -> list[str]:
    return [p for p in changed if p.endswith(".py") and (root / p).is_file()]


def ruff_issues(files: list[str], root: Path) -> list[dict[str, Any]]:
    if not files:
        return []
    _, out, _ = sh(["ruff", "check", "--output-format=json", "--exit-zero", *files], root)
    try:
        raw = json.loads(out or "[]")
    except ValueError:
        return []
    issues = []
    for item in raw:
        path = Path(item.get("filename", ""))
        try:
            rel = str(path.resolve().relative_to(root.resolve()))
        except ValueError:
            rel = str(path)
        fix = item.get("fix") or {}
        if fix.get("applicability") == "unsafe":
            suggestion = f"Unsafe autofix available — run `ruff check --fix --unsafe-fixes {rel}` and review: {fix.get('message') or ''}".strip()
        elif fix.get("message"):
            suggestion = str(fix["message"])
        else:
            suggestion = "No automatic fix; see the rule documentation."
        issues.append(
            {
                "source": "ruff",
                "path": rel,
                "line": int((item.get("location") or {}).get("row") or 0),
                "code": item.get("code") or "",
                "message": item.get("message") or "",
                "url": item.get("url") or "",
                "suggestion": suggestion,
            }
        )
    return issues


TSC_LINE = re.compile(r"^(?P<path>[^()\s][^()]*)\((?P<line>\d+),(?P<col>\d+)\): error (?P<code>TS\d+): (?P<msg>.+)$")


def parse_tsc(output: str, component_path: str) -> list[dict[str, Any]]:
    issues = []
    for line in output.splitlines():
        match = TSC_LINE.match(line.strip())
        if not match:
            continue
        code = match.group("code")
        issues.append(
            {
                "source": "tsc",
                "path": f"{component_path.rstrip('/')}/{match.group('path')}",
                "line": int(match.group("line")),
                "code": code,
                "message": match.group("msg"),
                "url": "",
                "suggestion": TS_HINTS.get(code, "Fix the type error; `tsc --noEmit` reproduces it locally."),
            }
        )
    return issues


def tsc_issues(component: str, root: Path) -> list[dict[str, Any]]:
    path = COMPONENTS[component]["path"]
    tsc = root / path / "node_modules" / ".bin" / "tsc"
    if not (root / path / "tsconfig.json").is_file() or not tsc.exists():
        return []
    _, out, err = sh([str(tsc), "--noEmit", "--pretty", "false"], root / path)
    return parse_tsc(out + err, path)


def diagnostics(changed: list[str], node_components: list[str], root: Path) -> list[dict[str, Any]]:
    issues = ruff_issues(changed_python(changed, root), root)
    for component in node_components:
        issues.extend(tsc_issues(component, root))
    return issues


def run_fixers(fixers: list[str], changed: list[str], root: Path) -> list[dict[str, Any]]:
    """Run each fixer; report what it ran and its exit code. Never raises on tool failure."""
    ran: list[dict[str, Any]] = []
    for fixer in fixers:
        if fixer == "ruff":
            files = changed_python(changed, root)
            if not files:
                ran.append({"fixer": "ruff", "command": "ruff check --fix (no changed .py files)", "exit": 0})
                continue
            code, _, _ = sh(["ruff", "check", "--fix", "--exit-zero", *files], root)
            ran.append({"fixer": "ruff", "command": f"ruff check --fix <{len(files)} changed file(s)>", "exit": code})
        elif fixer == "generators":
            for script in GENERATORS:
                if (root / script).is_file():
                    code, _, _ = sh([sys.executable, script], root)
                    ran.append({"fixer": "generators", "command": f"python3 {script}", "exit": code})
        elif fixer.startswith("node:"):
            component = fixer.split(":", 1)[1]
            spec = COMPONENTS.get(component)
            if spec is None:
                continue
            directory = root / spec["path"]
            scripts = package_scripts(directory)
            for script in ("lint:fix", "format"):
                if script in scripts:
                    code, _, _ = sh(["npm", "run", script], directory)
                    ran.append({"fixer": fixer, "command": f"npm run {script} ({component})", "exit": code})
            if not any(s in scripts for s in ("lint:fix", "format")):
                ran.append({"fixer": fixer, "command": f"{component} defines no lint:fix or format script", "exit": 0})
    return ran


def cmd_fix(args: argparse.Namespace) -> int:
    root = Path(args.repo_root).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    changed = [line.strip() for line in Path(args.changed).read_text().splitlines() if line.strip()]
    fixers = [f for f in args.fixers.split(",") if f]
    node = [c for c in args.node_components.split(",") if c]

    before = diagnostics(changed, node, root)
    ran = run_fixers(fixers, changed, root) if args.mode == "fix" else []
    after = diagnostics(changed, node, root) if ran else before

    _, patch, _ = sh(["git", "diff", "--no-ext-diff", "--no-color", "--no-renames"], root)
    _, untracked, _ = sh(["git", "ls-files", "--others", "--exclude-standard"], root)
    (out / "patch.diff").write_text(patch, encoding="utf-8")
    report = {
        "fixers": ran,
        "issues_before": before,
        "issues_after": after,
        "untracked": [line for line in untracked.splitlines() if line.strip()],
    }
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"fixers run: {len(ran)}; patch bytes: {len(patch)}; issues before/after: {len(before)}/{len(after)}")
    return 0


# ── check-patch / verify-applied (trusted job) ───────────────────────────


@dataclass
class PatchFile:
    path: str
    added: int = 0
    removed: int = 0
    flags: list[str] = field(default_factory=list)


def parse_patch(text: str) -> list[PatchFile]:
    files: list[PatchFile] = []
    current: PatchFile | None = None
    header = re.compile(r"^diff --git a/(.+) b/(.+)$")
    in_hunk = False
    for line in text.splitlines():
        match = header.match(line)
        if match:
            a, b = match.groups()
            current = PatchFile(path=b)
            if a != b:
                current.flags.append("rename")
            files.append(current)
            in_hunk = False
            continue
        if current is None:
            continue
        if line.startswith("@@"):
            in_hunk = True
            continue
        if not in_hunk:
            if line.startswith("new file mode"):
                current.flags.append("new file")
            elif line.startswith("deleted file mode"):
                current.flags.append("deleted file")
            elif line.startswith(("old mode", "new mode")):
                current.flags.append("mode change")
            elif line.startswith(("Binary files", "GIT binary patch")):
                current.flags.append("binary")
            elif "120000" in line and line.startswith(("new file mode", "index")):
                current.flags.append("symlink")
            continue
        if line.startswith("+") and not line.startswith("+++"):
            current.added += 1
        elif line.startswith("-") and not line.startswith("---"):
            current.removed += 1
    return files


def check_patch(
    text: str,
    changed: set[str],
    fixers: list[str],
    *,
    max_files: int = MAX_FILES,
    max_lines: int = MAX_CHANGED_LINES,
) -> dict[str, Any]:
    """Static checks on the untrusted patch. Any refusal blocks the whole patch."""
    files = parse_patch(text)
    refusals: list[str] = []
    needs_block_check: list[str] = []
    if not files:
        return {"ok": False, "empty": True, "refusals": [], "files": [], "needs_block_check": []}
    if len(files) > max_files:
        refusals.append(f"patch touches {len(files)} files (limit {max_files})")
    total = sum(f.added + f.removed for f in files)
    if total > max_lines:
        refusals.append(f"patch changes {total} lines (limit {max_lines})")
    generators_ran = "generators" in fixers
    for f in files:
        if f.flags:
            refusals.append(f"{f.path}: {', '.join(sorted(set(f.flags)))} is never auto-applied")
        reason = protected_reason(f.path)
        if reason:
            refusals.append(f"{f.path}: protected by automation policy v{POLICY_VERSION} ({reason})")
            continue
        if f.path in changed:
            continue
        if generators_ran and f.path in GENERATED_FILES:
            continue
        if generators_ran and f.path.endswith(".html"):
            needs_block_check.append(f.path)
            continue
        refusals.append(f"{f.path}: not part of this pull request and not a generated file")
    return {
        "ok": not refusals,
        "empty": False,
        "refusals": refusals,
        "files": [{"path": f.path, "added": f.added, "removed": f.removed} for f in files],
        "lines": total,
        "needs_block_check": needs_block_check,
    }


def outside_generated_blocks(text: str) -> str:
    return GENERATED_BLOCK.sub(lambda m: f"<!-- {m.group(1)}:block -->", text)


def verify_applied(repo: Path, paths: list[str]) -> list[str]:
    """After applying: every html edit outside the PR must sit inside generated blocks."""
    refusals = []
    for path in paths:
        proc = subprocess.run(
            ["git", "show", f"HEAD:{path}"], cwd=repo, capture_output=True, text=True
        )
        if proc.returncode != 0:
            refusals.append(f"{path}: not present at the PR head")
            continue
        after = (repo / path).read_text(encoding="utf-8", errors="surrogateescape")
        if outside_generated_blocks(proc.stdout) != outside_generated_blocks(after):
            refusals.append(f"{path}: changed outside its generated cg-* blocks")
    return refusals


# ── commit (trusted job) ─────────────────────────────────────────────────

COMMIT_MUTATION = (
    "mutation($input: CreateCommitOnBranchInput!) {"
    " createCommitOnBranch(input: $input) { commit { oid url } } }"
)


def staged_file_changes(repo: Path) -> dict[str, list[dict[str, str]]]:
    """The staged diff as createCommitOnBranch FileChanges (contents base64-encoded)."""

    def staged(diff_filter: str) -> list[str]:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--no-renames", f"--diff-filter={diff_filter}"],
            cwd=repo, capture_output=True, text=True, check=True,
        ).stdout
        return [line for line in out.splitlines() if line.strip()]

    additions = [
        {"path": path, "contents": base64.b64encode((repo / path).read_bytes()).decode("ascii")}
        for path in staged("AM")
    ]
    deletions = [{"path": path} for path in staged("D")]
    return {"additions": additions, "deletions": deletions}


def commit_request(
    repo: Path, *, repository: str, branch: str, head_sha: str, headline: str, body: str
) -> dict[str, Any]:
    """GraphQL request for a Verified commit that only lands on exactly ``head_sha``.

    ``expectedHeadOid`` is fixed to the commit CI failed on and is never refreshed:
    if the author pushed meanwhile, GitHub rejects the commit instead of writing
    the fixed files over their newer work.
    """
    return {
        "query": COMMIT_MUTATION,
        "variables": {
            "input": {
                "branch": {"repositoryNameWithOwner": repository, "branchName": branch},
                "message": {"headline": headline, "body": body},
                "expectedHeadOid": head_sha,
                "fileChanges": staged_file_changes(repo),
            }
        },
    }


# ── render ───────────────────────────────────────────────────────────────


def cell(value: Any, limit: int = 300) -> str:
    text = " ".join(str(value).split())
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text.replace("|", "\\|").replace("`", "'").replace("<", "&lt;").replace(">", "&gt;")


def render(
    *,
    repository: str,
    plan_out: dict[str, str],
    failed_jobs: list[dict[str, str]],
    report: dict[str, Any] | None,
    check: dict[str, Any] | None,
    outcome: str,
    commit_sha: str,
    run_url: str,
) -> str:
    """The body of the one sticky comment (the post-pr-comment action adds the marker
    and header). outcome: pushed | refused | no-changes | moved | report-only | fix-failed."""
    iteration = int(plan_out.get("iteration", "0")) + (1 if outcome == "pushed" else 0)
    cap = plan_out.get("max_iterations", str(DEFAULT_MAX_ITERATIONS))
    lines: list[str] = []
    headline = {
        "pushed": f"Committed `{commit_sha[:12]}` (Verified) to this branch. CI is re-running on it.",
        "refused": "Fixes were produced but **not pushed**: the patch failed a safety check.",
        "no-changes": "Ran the fixers; they changed nothing. The failures below need a human.",
        "moved": "The branch moved while fixes were prepared; nothing was pushed. The next CI run decides.",
        "report-only": f"Not fixing: {cell(plan_out.get('reason', ''))}.",
        "fix-failed": "The fix job failed before producing a patch; see the run log.",
        "commit-failed": "The fix passed every check but GitHub refused the commit; see the run log.",
    }.get(outcome, outcome)
    lines += [headline, "", f"Fix commits on this PR: **{iteration}/{cap}** · [run log]({run_url})", ""]

    if report and report.get("fixers"):
        lines += ["### What ran", "", "| Fixer | Command | Exit |", "|---|---|---|"]
        for item in report["fixers"]:
            lines.append(f"| {cell(item['fixer'])} | `{cell(item['command'])}` | {item['exit']} |")
        lines.append("")
    if check and check.get("files") and outcome == "pushed":
        lines += ["### Files changed by the fix", ""]
        lines += [f"- `{cell(f['path'])}` (+{f['added']} −{f['removed']})" for f in check["files"][:MAX_ISSUES_SHOWN]]
        lines.append("")
    if check and check.get("refusals"):
        lines += ["### Why it was not pushed", ""]
        lines += [f"- {cell(reason)}" for reason in check["refusals"]]
        lines += ["", "Run the same fixers locally and commit the result (see `AUTOMATION.md`).", ""]

    # Line numbers refer to the tree the links point at: the fix commit when one
    # was pushed, otherwise the PR head the diagnostics ran against first.
    if report:
        issues = report.get("issues_after" if outcome == "pushed" else "issues_before") or []
    else:
        issues = []
    link_sha = commit_sha if outcome == "pushed" else plan_out.get("head_sha", "")
    if issues:
        lines += [f"### Needs a human ({len(issues)})", "", "| Location | Rule | Problem | Suggested fix |", "|---|---|---|---|"]
        for issue in issues[:MAX_ISSUES_SHOWN]:
            url = f"https://github.com/{repository}/blob/{link_sha}/{issue['path']}#L{issue['line']}"
            rule = f"[{cell(issue['code'])}]({issue['url']})" if issue.get("url") else cell(issue["code"])
            lines.append(
                f"| [`{cell(issue['path'])}:{issue['line']}`]({url}) | {rule} | {cell(issue['message'])} | {cell(issue['suggestion'])} |"
            )
        if len(issues) > MAX_ISSUES_SHOWN:
            lines.append(f"| … | | {len(issues) - MAX_ISSUES_SHOWN} more — see the run log | |")
        lines.append("")
    if failed_jobs:
        lines += ["### Failing checks", ""]
        lines += [f"- [{cell(job['name'])}]({job['url']}) — {cell(job['conclusion'])}" for job in failed_jobs]
        lines.append("")
    lines += [
        "<sub>Deterministic fixers only (ruff safe fixes, the repo generators, component lint:fix/format scripts). "
        f"Never pushes to forks, protected paths, or past {cap} fix commits. "
        f"Add the `{OPT_OUT_LABEL}` label to opt this PR out.</sub>",
    ]
    body = "\n".join(lines)
    return body[:65000]


# ── CLI ──────────────────────────────────────────────────────────────────


def load(path: str | None, default: Any) -> Any:
    if not path:
        return default
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def emit(outputs: dict[str, str]) -> None:
    for key, value in outputs.items():
        print(f"{key}={value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("plan")
    p.add_argument("--run", required=True)
    p.add_argument("--jobs", required=True)
    p.add_argument("--pr", required=True, help="JSON list from GET /pulls?head=…; first open PR is used")
    p.add_argument("--commits", required=True)
    p.add_argument("--repository", required=True)
    p.add_argument("--max-iterations", type=int, default=DEFAULT_MAX_ITERATIONS)
    p.add_argument("--enabled", default="true")
    p.add_argument("--failed-jobs-out", default="")

    f = sub.add_parser("fix")
    f.add_argument("--repo-root", default=".")
    f.add_argument("--changed", required=True)
    f.add_argument("--fixers", default="")
    f.add_argument("--node-components", default="")
    f.add_argument("--mode", choices=("fix", "report"), default="fix")
    f.add_argument("--out", required=True)

    c = sub.add_parser("check-patch")
    c.add_argument("--patch", required=True)
    c.add_argument("--changed", required=True)
    c.add_argument("--fixers", default="")
    c.add_argument("--out", required=True)

    v = sub.add_parser("verify-applied")
    v.add_argument("--repo", required=True)
    v.add_argument("--check", required=True, help="check-patch output; refusals are appended to it")

    m = sub.add_parser("commit-request")
    m.add_argument("--repo", required=True)
    m.add_argument("--repository", required=True)
    m.add_argument("--branch", required=True)
    m.add_argument("--head-sha", required=True)
    m.add_argument("--headline", required=True)
    m.add_argument("--body", default="")
    m.add_argument("--out", required=True)

    r = sub.add_parser("render")
    r.add_argument("--repository", required=True)
    r.add_argument("--plan", required=True, help="file of key=value plan outputs")
    r.add_argument("--failed-jobs", default="")
    r.add_argument("--report", default="")
    r.add_argument("--check", default="")
    r.add_argument("--outcome", required=True)
    r.add_argument("--commit-sha", default="")
    r.add_argument("--run-url", required=True)
    args = parser.parse_args(argv)

    if args.command == "plan":
        prs = load(args.pr, [])
        pr = prs[0] if isinstance(prs, list) and prs else (prs if isinstance(prs, dict) and prs else None)
        jobs = load(args.jobs, {})
        jobs = jobs.get("jobs", []) if isinstance(jobs, dict) else jobs
        result = plan(
            load(args.run, {}),
            jobs,
            pr,
            load(args.commits, []),
            repository=args.repository,
            max_iterations=args.max_iterations,
            enabled=args.enabled.lower() != "false",
        )
        if args.failed_jobs_out:
            Path(args.failed_jobs_out).write_text(json.dumps(result.failed_jobs), encoding="utf-8")
        emit(result.outputs())
        return 0

    if args.command == "fix":
        return cmd_fix(args)

    if args.command == "check-patch":
        changed = {line.strip() for line in Path(args.changed).read_text().splitlines() if line.strip()}
        fixers = [x for x in args.fixers.split(",") if x]
        result = check_patch(Path(args.patch).read_text(encoding="utf-8"), changed, fixers)
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
        emit({"ok": "true" if result["ok"] else "false", "empty": "true" if result["empty"] else "false"})
        return 0

    if args.command == "verify-applied":
        check = load(args.check, {})
        refusals = verify_applied(Path(args.repo), check.get("needs_block_check", []))
        if refusals:
            check["ok"] = False
            check.setdefault("refusals", []).extend(refusals)
            Path(args.check).write_text(json.dumps(check, indent=2), encoding="utf-8")
        emit({"ok": "true" if not refusals else "false"})
        return 0

    if args.command == "commit-request":
        request = commit_request(
            Path(args.repo), repository=args.repository, branch=args.branch,
            head_sha=args.head_sha, headline=args.headline, body=args.body,
        )
        Path(args.out).write_text(json.dumps(request), encoding="utf-8")
        changes = request["variables"]["input"]["fileChanges"]
        print(f"additions={len(changes['additions'])}")
        print(f"deletions={len(changes['deletions'])}")
        return 0

    if args.command == "render":
        plan_out = {}
        for line in Path(args.plan).read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                plan_out[key] = value
        print(
            render(
                repository=args.repository,
                plan_out=plan_out,
                failed_jobs=load(args.failed_jobs, []),
                report=load(args.report, None),
                check=load(args.check, None),
                outcome=args.outcome,
                commit_sha=args.commit_sha,
                run_url=args.run_url,
            )
        )
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
