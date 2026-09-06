from pathlib import Path

from scripts.audit_github_actions import GitHubLoader, ROOT, Result, audit, json_inventory, load
import yaml


def workflow(tmp_path: Path, text: str) -> Result:
    path = tmp_path / "workflow.yml"
    path.write_text(text)
    data = yaml.load(text, Loader=GitHubLoader)
    result = Result(path=path, data=data)
    audit(result)
    return result


def test_loader_preserves_on_trigger(tmp_path: Path) -> None:
    result = workflow(
        tmp_path,
        """on: {workflow_dispatch: null}
permissions: {contents: read}
jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps: [{run: 'echo safe'}]
""",
    )
    assert "workflow_dispatch" in result.data["on"]
    assert result.status == "valid and ready"


def test_unpinned_action_fails_closed(tmp_path: Path) -> None:
    result = workflow(
        tmp_path,
        """on: {push: null}
permissions: {contents: read}
jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps: [{uses: actions/checkout@v4}]
""",
    )
    assert any("full commit SHA" in error for error in result.errors)
    assert result.status == "broken and requiring immediate patching"


def test_deploy_without_environment_requires_governance(tmp_path: Path) -> None:
    result = workflow(
        tmp_path,
        """on: {workflow_dispatch: null}
permissions: {contents: read}
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps: [{run: 'echo test'}]
  deploy:
    needs: test
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps: [{run: 'curl -fsS "$HOOK"'}]
""",
    )
    assert result.status == "unsafe and requiring governance changes before execution"


def test_scheduled_writer_requires_environment_boundary(tmp_path: Path) -> None:
    result = workflow(
        tmp_path,
        """on: {schedule: [{cron: '0 0 * * *'}]}
permissions: {contents: read}
jobs:
  publish:
    permissions: {contents: write}
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps: [{run: 'git push origin HEAD'}]
""",
    )
    assert any("unattended job 'publish'" in warning for warning in result.warnings)

    result.data["jobs"]["publish"]["environment"] = "automation-write"
    result.warnings.clear()
    audit(result)
    assert result.status == "valid and ready"


def test_pages_deploy_requires_official_artifact_gate(tmp_path: Path) -> None:
    result = workflow(
        tmp_path,
        """on: {workflow_dispatch: null}
permissions: {contents: read}
jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/upload-pages-artifact@1111111111111111111111111111111111111111
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    permissions: {pages: write, id-token: write}
    environment: github-pages
    steps:
      - uses: actions/deploy-pages@2222222222222222222222222222222222222222
""",
    )
    assert any("must need a job" in error for error in result.errors)

    result.data["jobs"]["deploy"]["needs"] = "build"
    result.errors.clear()
    audit(result)
    assert result.status == "valid and ready"


def test_artifact_consumer_requires_matching_producer(tmp_path: Path) -> None:
    result = workflow(
        tmp_path,
        """on: {workflow_dispatch: null}
permissions: {contents: read}
jobs:
  consume:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/download-artifact@1111111111111111111111111111111111111111
        with: {name: release}
""",
    )
    assert any("release" in error for error in result.errors)


def test_json_inventory_includes_execution_dependencies(tmp_path: Path) -> None:
    result = workflow(
        tmp_path,
        """on: {workflow_dispatch: null}
permissions: {contents: read}
concurrency: {group: checks, cancel-in-progress: true}
jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/setup-python@1111111111111111111111111111111111111111
        with: {cache: pip}
""",
    )
    record = json_inventory(result)
    assert record["caches"] == [{"job": "check", "type": "pip"}]
    assert record["concurrency"]["group"] == "checks"
    assert len(record["actions"]) == 1


def test_enterprise_patch_deploy_disables_checkout_credentials() -> None:
    result = load(ROOT / ".github/workflows/enterprise-patch-deploy.yml")
    audit(result)

    assert not any("checkout credentials" in warning for warning in result.warnings)
    assert result.status == "valid and ready"
