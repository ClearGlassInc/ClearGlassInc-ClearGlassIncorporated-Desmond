"""auto-fix.yml's decision logic, held to what it must refuse.

The fix job runs pull-request code and its output is untrusted, so most of these
tests are about the trusted side saying no: forks, bots, the opt-out label, the
iteration cap, protected paths, renames, binaries, and generated-page edits that
stray outside their markers.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.ci import autofix

REPO = "ClearGlassInc/ClearGlassInc-ClearGlassIncorporated-Desmond"
SHA = "a" * 40


def run_payload(**overrides):
    payload = {
        "conclusion": "failure",
        "event": "pull_request",
        "head_sha": SHA,
        "head_branch": "feature/x",
        "head_repository": {"full_name": REPO},
    }
    payload.update(overrides)
    return payload


def pr_payload(**overrides):
    payload = {
        "number": 42,
        "user": {"login": "desmond", "type": "User"},
        "labels": [],
        "head": {"sha": SHA, "ref": "feature/x", "repo": {"full_name": REPO}},
    }
    payload.update(overrides)
    return payload


def job(name, conclusion="failure"):
    return {"name": name, "conclusion": conclusion, "html_url": f"https://example.test/{name}"}


def fix_commit():
    return {"commit": {"message": "auto-fix: ruff for #42\n\nAuto-Fix-Run: https://example.test/run"}}


# ── plan: refusals ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "run, pr, expected",
    [
        (run_payload(conclusion="success"), pr_payload(), "not failure"),
        (run_payload(event="push"), pr_payload(), "not a pull request run"),
        (run_payload(head_repository={"full_name": "evil/fork"}), pr_payload(), "fork"),
        (run_payload(), None, "no open pull request"),
        (run_payload(), pr_payload(head={"sha": SHA, "ref": "x", "repo": {"full_name": "evil/fork"}}), "fork"),
        (run_payload(), pr_payload(user={"login": "dependabot[bot]", "type": "Bot"}), "bot"),
        (run_payload(), pr_payload(user={"login": "renovate[bot]", "type": "User"}), "bot"),
        (run_payload(), pr_payload(labels=[{"name": "no-autofix"}]), "no-autofix"),
        (run_payload(), pr_payload(head={"sha": "b" * 40, "ref": "x", "repo": {"full_name": REPO}}), "moved"),
    ],
)
def test_plan_refuses(run, pr, expected):
    result = autofix.plan(run, [job("Lint (ruff)")], pr, [], repository=REPO)
    assert result.act is False
    assert expected in result.reason


def test_kill_switch_wins_over_everything():
    result = autofix.plan(run_payload(), [job("Lint (ruff)")], pr_payload(), [], repository=REPO, enabled=False)
    assert result.act is False and "disabled" in result.reason


def test_iteration_cap_downgrades_to_report_only():
    result = autofix.plan(
        run_payload(), [job("Lint (ruff)")], pr_payload(), [fix_commit(), fix_commit()], repository=REPO
    )
    assert result.act is True
    assert result.mode == "report"
    assert result.fixers == []
    assert "cap" in result.reason


def test_a_human_commit_titled_auto_fix_does_not_count_without_the_trailer():
    commits = [{"commit": {"message": "auto-fix: my own tidy-up"}, "author": {"login": "desmond"}}, fix_commit()]
    assert autofix.count_autofix_commits(commits) == 1


def test_earlier_bot_fix_commits_without_the_trailer_still_count():
    """#187's auto-fix committed 'auto-fix: ruff safe fixes for PR #N' with no trailer."""
    legacy = {"commit": {"message": "auto-fix: ruff safe fixes for PR #42"}, "author": {"login": "github-actions[bot]"}}
    assert autofix.count_autofix_commits([legacy, fix_commit()]) == 2


@pytest.mark.parametrize("branch", ["main", "staging"])
def test_integration_branches_are_never_auto_fixed(branch):
    result = autofix.plan(run_payload(head_branch=branch), [job("Lint (ruff)")],
                          pr_payload(head={"sha": SHA, "ref": branch, "repo": {"full_name": REPO}}), [],
                          repository=REPO)
    assert result.act is False and "integration branch" in result.reason


def test_unfixable_failures_report_only():
    result = autofix.plan(run_payload(), [job("Python Tests")], pr_payload(), [], repository=REPO)
    assert result.act is True and result.mode == "report" and result.fixers == []
    assert result.failed_jobs[0]["name"] == "Python Tests"


# ── plan: fixer mapping ──────────────────────────────────────────────────


def test_failing_checks_map_to_their_fixers():
    jobs = [
        job("Lint (ruff)"),
        job("Search discovery and structured data"),
        job("Stack (storefront) / Lint & types"),
        job("Stack (control-plane) / Lint & types"),
        job("Stack (admin) / Tests"),  # tests are never "fixed"
        job("Lighthouse budgets", "success"),
    ]
    result = autofix.plan(run_payload(), jobs, pr_payload(), [], repository=REPO)
    assert result.mode == "fix"
    assert result.fixers == ["ruff", "generators", "node:storefront"]
    assert result.node_components == ["storefront"]
    assert {j["name"] for j in result.failed_jobs} == {j["name"] for j in jobs[:5]}


def test_unknown_stack_component_is_ignored_not_trusted():
    fixers, node = autofix.fixers_for([{"name": "Stack (../../etc) / Lint & types"}])
    assert fixers == [] and node == []


# ── check-patch ──────────────────────────────────────────────────────────


def diff_for(path: str, extra_header: str = "", old: str = "x = 1", new: str = "x = 2") -> str:
    return (
        f"diff --git a/{path} b/{path}\n{extra_header}"
        f"--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-{old}\n+{new}\n"
    )


def test_a_patch_inside_the_pr_is_accepted():
    result = autofix.check_patch(diff_for("bots/x.py"), {"bots/x.py"}, ["ruff"])
    assert result["ok"] is True
    assert result["files"] == [{"path": "bots/x.py", "added": 1, "removed": 1}]


def test_an_empty_patch_is_reported_as_empty_not_ok():
    result = autofix.check_patch("", {"bots/x.py"}, ["ruff"])
    assert result["ok"] is False and result["empty"] is True


@pytest.mark.parametrize(
    "path",
    [
        "control-plane/app/payments.py",
        "control-plane/app/routers/checkout.py",
        ".github/workflows/ci.yml",
        "storefront/package-lock.json",
        "control-plane/migrations/011_x.sql",
        "terms.html",
    ],
)
def test_protected_paths_are_refused_even_when_the_pr_touches_them(path):
    result = autofix.check_patch(diff_for(path), {path}, ["ruff", "generators"])
    assert result["ok"] is False
    assert any("protected" in reason for reason in result["refusals"])


def test_files_outside_the_pr_are_refused():
    result = autofix.check_patch(diff_for("bots/other.py"), {"bots/x.py"}, ["ruff"])
    assert result["ok"] is False
    assert "not part of this pull request" in result["refusals"][0]


def test_generated_files_are_allowed_only_when_the_generators_ran():
    patch = diff_for("sitemap.xml", old="<a/>", new="<b/>")
    assert autofix.check_patch(patch, set(), ["generators"])["ok"] is True
    assert autofix.check_patch(patch, set(), ["ruff"])["ok"] is False


def test_generated_html_outside_the_pr_needs_the_block_check():
    result = autofix.check_patch(diff_for("about.html", old="<p>a</p>", new="<p>b</p>"), set(), ["generators"])
    assert result["ok"] is True
    assert result["needs_block_check"] == ["about.html"]


@pytest.mark.parametrize(
    "header",
    [
        "new file mode 100644\n",
        "deleted file mode 100644\n",
        "old mode 100644\nnew mode 100755\n",
        "Binary files a/x and b/x differ\n",
    ],
)
def test_structural_changes_are_never_applied(header):
    result = autofix.check_patch(diff_for("bots/x.py", header), {"bots/x.py"}, ["ruff"])
    assert result["ok"] is False


def test_renames_are_refused():
    patch = "diff --git a/bots/a.py b/bots/b.py\nrename from bots/a.py\nrename to bots/b.py\n"
    result = autofix.check_patch(patch, {"bots/a.py", "bots/b.py"}, ["ruff"])
    assert result["ok"] is False


def test_size_limits():
    patch = "".join(diff_for(f"bots/f{i}.py") for i in range(5))
    changed = {f"bots/f{i}.py" for i in range(5)}
    assert autofix.check_patch(patch, changed, ["ruff"], max_files=4)["ok"] is False
    assert autofix.check_patch(patch, changed, ["ruff"], max_lines=9)["ok"] is False
    assert autofix.check_patch(patch, changed, ["ruff"])["ok"] is True


# ── verify-applied ───────────────────────────────────────────────────────

PAGE = """<html><body><h1>Title</h1>
<!-- cg-related:start --><a href="/a">A</a><!-- cg-related:end -->
<p>Body</p></body></html>
"""


@pytest.fixture
def page_repo(tmp_path: Path) -> Path:
    if shutil.which("git") is None:
        pytest.skip("git not available")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "about.html").write_text(PAGE)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
        check=True,
    )
    return tmp_path


def test_an_edit_inside_the_generated_block_passes(page_repo: Path):
    (page_repo / "about.html").write_text(PAGE.replace('<a href="/a">A</a>', '<a href="/b">B</a>'))
    assert autofix.verify_applied(page_repo, ["about.html"]) == []


def test_an_edit_outside_the_generated_block_is_refused(page_repo: Path):
    (page_repo / "about.html").write_text(PAGE.replace("<p>Body</p>", "<p>Pwned</p>"))
    assert "outside" in autofix.verify_applied(page_repo, ["about.html"])[0]


# ── diagnostics and rendering ────────────────────────────────────────────


def test_tsc_output_becomes_repo_relative_issues_with_hints():
    output = "app/page.tsx(12,5): error TS2322: Type 'string' is not assignable to type 'number'.\nnoise\n"
    issues = autofix.parse_tsc(output, "storefront")
    assert issues == [
        {
            "source": "tsc",
            "path": "storefront/app/page.tsx",
            "line": 12,
            "code": "TS2322",
            "message": "Type 'string' is not assignable to type 'number'.",
            "url": "",
            "suggestion": autofix.TS_HINTS["TS2322"],
        }
    ]


def test_render_links_to_the_tree_the_line_numbers_belong_to():
    issue = {"source": "ruff", "path": "bots/x.py", "line": 3, "code": "F821", "message": "Undefined name `y`",
             "url": "https://docs.astral.sh/ruff/rules/undefined-name", "suggestion": "Define y"}
    report = {"fixers": [{"fixer": "ruff", "command": "ruff check --fix", "exit": 0}],
              "issues_before": [issue], "issues_after": [{**issue, "line": 2}]}
    plan_out = {"iteration": "0", "max_iterations": "2", "head_sha": SHA, "reason": "x"}
    pushed = autofix.render(repository=REPO, plan_out=plan_out, failed_jobs=[], report=report,
                            check={"files": []}, outcome="pushed", commit_sha="c" * 40, run_url="u")
    refused = autofix.render(repository=REPO, plan_out=plan_out, failed_jobs=[], report=report,
                             check={"refusals": ["nope"]}, outcome="refused", commit_sha="", run_url="u")
    assert "Verified" in pushed
    assert f"/blob/{'c' * 40}/bots/x.py#L2" in pushed
    assert "**1/2**" in pushed
    assert f"/blob/{SHA}/bots/x.py#L3" in refused
    assert "**0/2**" in refused and "nope" in refused


def test_render_neutralises_markdown_and_html_in_untrusted_text():
    issue = {"source": "tsc", "path": "a|b.ts", "line": 1, "code": "TS1", "message": "<img src=x> `x` | y",
             "url": "", "suggestion": "s"}
    body = autofix.render(repository=REPO, plan_out={"head_sha": SHA}, failed_jobs=[],
                          report={"fixers": [], "issues_before": [issue]}, check=None,
                          outcome="report-only", commit_sha="", run_url="u")
    assert "<img" not in body
    assert "a\\|b.ts" in body


# ── fix, end to end on a throwaway repository ───────────────────────────


@pytest.mark.skipif(shutil.which("ruff") is None or shutil.which("git") is None, reason="needs ruff and git")
def test_fix_produces_a_patch_and_before_after_diagnostics(tmp_path: Path):
    repo = tmp_path / "pr"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "mod.py").write_text("import os\nimport sys\n\nprint(sys.argv, undefined_name)\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"], check=True)
    changed = tmp_path / "changed.txt"
    changed.write_text("mod.py\n")
    out = tmp_path / "out"

    code = autofix.main(["fix", "--repo-root", str(repo), "--changed", str(changed), "--fixers", "ruff",
                         "--mode", "fix", "--out", str(out)])

    assert code == 0
    patch = (out / "patch.diff").read_text()
    assert "-import os" in patch
    report = json.loads((out / "report.json").read_text())
    before = {i["code"] for i in report["issues_before"]}
    after = {i["code"] for i in report["issues_after"]}
    assert {"F401", "F821"} <= before
    assert after == {"F821"}  # the unused import was fixed; the undefined name needs a human
    assert report["issues_after"][0]["path"] == "mod.py"
    assert autofix.check_patch(patch, {"mod.py"}, ["ruff"])["ok"] is True


def test_commit_request_pins_the_failing_head_and_carries_the_staged_files(page_repo: Path):
    (page_repo / "about.html").write_text(PAGE.replace("<p>Body</p>", "<p>Fixed</p>"))
    subprocess.run(["git", "-C", str(page_repo), "add", "about.html"], check=True)
    request = autofix.commit_request(page_repo, repository=REPO, branch="feature/x", head_sha=SHA,
                                     headline="auto-fix: ruff for #42", body="Auto-Fix-Run: u")
    data = request["variables"]["input"]
    assert data["expectedHeadOid"] == SHA
    assert data["branch"] == {"repositoryNameWithOwner": REPO, "branchName": "feature/x"}
    assert data["fileChanges"]["deletions"] == []
    [addition] = data["fileChanges"]["additions"]
    assert addition["path"] == "about.html"
    import base64
    assert b"<p>Fixed</p>" in base64.b64decode(addition["contents"])
    assert "createCommitOnBranch" in request["query"]
