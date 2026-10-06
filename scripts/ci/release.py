#!/usr/bin/env python3
"""Release one set of services to one environment, as a unit.

``reusable-deploy.yml`` runs this once per environment. For every service, in
the dependency order of ``components.COMPONENTS`` (the API before the apps that
call it):

1. resolve the image to an immutable digest — building and pushing it first in
   ``--build`` mode (previews, staging), or requiring that it already exists
   (production deploys exactly the digest staging tested, never a rebuild);
2. record the revision currently serving traffic (the rollback target);
3. deploy a candidate revision that receives **no** traffic, behind a tag URL;
4. smoke-test the candidate.

Only when every candidate is healthy, and only with ``--promote``, does traffic
move: each service is promoted and smoke-tested live. If anything fails after a
promotion, every service already promoted is routed back to the revision it was
serving — unless ``--auto-rollback`` is off (a release carrying database
migrations), in which case the job fails loudly and a human decides
(``rollback.yml``, ``docs/INCIDENT_RESPONSE.md``). Rollback is one shot, never
a loop: a rollback that fails is reported, not retried.

All cloud calls go through ``scripts/ci/deploy_target.sh``. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))

from components import COMPONENTS  # noqa: E402

ADAPTER = HERE.parent / "deploy_target.sh"
SMOKE = Path(os.environ.get("CG_SMOKE_SCRIPT", ROOT / ".github/actions/run-smoke-tests/smoke.sh"))
ENVIRONMENTS = ("preview", "staging", "production")


@dataclass
class ServiceResult:
    service: str
    target: str
    image: str = ""
    previous_revision: str = ""
    revision: str = ""
    candidate_url: str = ""
    url: str = ""
    status: str = "pending"  # pending|candidate-ok|promoted|failed|rolled-back|rollback-failed
    detail: str = ""


@dataclass
class Release:
    environment: str
    sha: str
    tag: str
    outcome: str = "pending"
    services: list[ServiceResult] = field(default_factory=list)


def child_env(extra: dict[str, str]) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in {"GITHUB_OUTPUT"}}
    env.update(extra)
    return env


def parse_kv(text: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line and not line.startswith("::"))


def adapter(action: str, **values: str) -> dict[str, str]:
    proc = subprocess.run(
        ["bash", str(ADAPTER), action], env=child_env(values), capture_output=True, text=True
    )
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"deploy_target {action} failed: {proc.stderr.strip().splitlines()[-1:] or proc.returncode}")
    return parse_kv(proc.stdout)


def smoke(url: str, checks: list[str]) -> bool:
    proc = subprocess.run(
        ["bash", str(SMOKE)],
        env=child_env({"SMOKE_BASE_URL": url, "SMOKE_CHECKS": "\n".join(checks)}),
        capture_output=True,
        text=True,
    )
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return proc.returncode == 0


def run(command: list[str]) -> str:
    proc = subprocess.run(command, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(command[:3])} failed: {proc.stderr.strip()[-400:]}")
    return proc.stdout


def resolve_digest(image: str) -> str:
    """Tag -> repo@sha256:digest. Fails if the image does not exist."""
    out = run(["docker", "buildx", "imagetools", "inspect", image, "--format", "{{json .Manifest}}"])
    digest = json.loads(out).get("digest", "")
    if not digest.startswith("sha256:"):
        raise RuntimeError(f"could not resolve a digest for {image}")
    return f"{image.rsplit(':', 1)[0]}@{digest}"


def preview_env(service: str) -> str:
    """The component's preview settings, with @random values freshly generated (and masked)."""
    pairs = []
    for key, value in COMPONENTS[service]["deploy"].get("preview_env", {}).items():
        if value == "@random":
            value = secrets.token_hex(24)
            print(f"::add-mask::{value}")
        if "," in value:
            raise ValueError(f"{service} preview value for {key} contains a comma")
        pairs.append(f"{key}={value}")
    return ",".join(pairs)


def release(args: argparse.Namespace, cloud: dict[str, str]) -> Release:
    names = [name for name in COMPONENTS if name in args.services and "deploy" in COMPONENTS[name]]
    unknown = sorted(set(args.services) - set(names))
    if unknown:
        raise ValueError(f"not deployable: {', '.join(unknown)}")
    rel = Release(environment=args.environment, sha=args.sha, tag=args.tag)
    rel.services = [ServiceResult(name, f"{args.service_prefix}-{name}-{args.environment}") for name in names]

    def target(result: ServiceResult, **extra: str) -> dict[str, str]:
        return {**cloud, "SERVICE": result.target, "COMMIT_SHA": args.sha, **extra}

    # Phase 1: candidates. Nothing here moves user traffic.
    current = rel.services[0]
    try:
        for result in rel.services:
            current = result
            spec = COMPONENTS[result.service]
            image = f"{args.image_repository}/{result.service}:{args.sha}"
            if args.build:
                run(["docker", "build", "--tag", image, str(args.source / spec["path"])])
                run(["docker", "push", image])
            result.image = resolve_digest(image)
            result.previous_revision = adapter("describe", **target(result)).get("serving_revision", "")
            deployed = adapter(
                "deploy",
                **target(
                    result,
                    IMAGE=result.image,
                    TAG=args.tag,
                    PORT=str(spec["deploy"]["port"]),
                    ENV_VARS=preview_env(result.service) if args.environment == "preview" else "",
                ),
            )
            result.revision = deployed.get("revision", "")
            result.candidate_url = deployed.get("candidate_url", "")
            if not result.candidate_url:
                raise RuntimeError("deploy reported no candidate URL")
            if not smoke(result.candidate_url, spec["deploy"]["smoke"]):
                raise RuntimeError("candidate failed its smoke tests")
            result.status = "candidate-ok"
            result.url = result.candidate_url
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        current.status, current.detail = "failed", str(exc)
        rel.outcome = "failed"
        cleanup_tags(rel, args, target)
        return rel

    if not args.promote:
        rel.outcome = "success"
        return rel

    # Phase 2: promotion, in dependency order, each verified live.
    promoted: list[ServiceResult] = []
    try:
        for result in rel.services:
            current = result
            result.url = adapter("promote", **target(result, REVISION=result.revision)).get("url", "")
            promoted.append(result)
            result.status = "promoted"
            if not smoke(result.url, COMPONENTS[result.service]["deploy"]["smoke"]):
                raise RuntimeError("failed its smoke tests after promotion")
    except RuntimeError as exc:
        current.status, current.detail = "failed", str(exc)
        rel.outcome = "failed"
        if args.auto_rollback:
            rollback(promoted, target)
            rel.outcome = "rolled-back"
        else:
            print(
                "::error title=Rollback withheld::this release changes database migrations, so traffic was "
                "NOT moved back automatically. Decide with rollback.yml and docs/INCIDENT_RESPONSE.md."
            )
        cleanup_tags(rel, args, target)
        return rel

    rel.outcome = "success"
    cleanup_tags(rel, args, target)
    return rel


def rollback(promoted: list[ServiceResult], target) -> None:
    for result in reversed(promoted):
        if not result.previous_revision:
            result.detail += " · no previous revision to roll back to"
            continue
        try:
            adapter("rollback", **target(result, REVISION=result.previous_revision))
            result.status = "rolled-back"
            print(f"::warning title=Rolled back::{result.service} is serving {result.previous_revision} again")
        except RuntimeError as exc:
            result.status = "rollback-failed"
            result.detail += f" · rollback failed: {exc}"
            print(f"::error title=Rollback failed::{result.service}: {exc}")


def cleanup_tags(rel: Release, args: argparse.Namespace, target) -> None:
    """Previews keep their tag (it is the preview URL); release candidates do not."""
    if args.environment == "preview":
        return
    for result in rel.services:
        if result.revision:
            try:
                adapter("untag", **target(result, TAG=args.tag))
            except RuntimeError as exc:
                print(f"::warning title=Tag cleanup::{result.service}: {exc}")


def summary(rel: Release) -> str:
    lines = [
        f"### {rel.environment}: {rel.outcome}",
        "",
        f"Commit `{rel.sha[:12]}` · tag `{rel.tag}`",
        "",
        "| Service | Status | URL | Revision | Previous | Image | Detail |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rel.services:
        lines.append(
            f"| {r.service} | {r.status} | {r.url or '—'} | {r.revision or '—'} | {r.previous_revision or '—'} "
            f"| `{r.image.rsplit('@', 1)[-1][:19] if r.image else '—'}` | {r.detail or ''} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--environment", required=True, choices=ENVIRONMENTS)
    parser.add_argument("--services", required=True, help="comma-separated component names")
    parser.add_argument("--sha", required=True)
    parser.add_argument("--tag", required=True, help="revision tag, e.g. pr-12 or sha-abc1234")
    parser.add_argument("--image-repository", required=True)
    parser.add_argument("--service-prefix", default="cg")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--auto-rollback", action="store_true")
    parser.add_argument("--out", default="")
    parser.add_argument(
        "--source",
        type=Path,
        default=ROOT,
        help="checkout of the commit being released (build context); defaults to this checkout",
    )
    args = parser.parse_args(argv)
    args.services = [s.strip() for s in args.services.split(",") if s.strip()]

    if args.environment == "production" and args.build:
        parser.error("production never builds: it deploys the digest staging tested")
    if args.environment == "preview" and args.promote:
        parser.error("previews are tagged revisions; they never take traffic")

    cloud = {
        key: os.environ.get(key, "")
        for key in ("DEPLOY_PROVIDER", "DEPLOY_PROJECT", "DEPLOY_REGION")
    }
    try:
        rel = release(args, cloud)
    except ValueError as exc:
        print(f"::error title=Release::{exc}")
        return 2

    text = summary(rel)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(text)
    if args.out:
        Path(args.out).write_text(json.dumps({**asdict(rel)}, indent=2), encoding="utf-8")
    urls = {r.service: r.url for r in rel.services if r.url}
    outputs = {
        "outcome": rel.outcome,
        "urls": json.dumps(urls, separators=(",", ":")),
        "primary_url": next(iter(urls.values()), ""),
    }
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
            handle.writelines(f"{k}={v}\n" for k, v in outputs.items())
    return 0 if rel.outcome == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
