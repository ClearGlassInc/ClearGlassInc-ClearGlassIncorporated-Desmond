"""A stateful stand-in for the four gcloud calls scripts/ci/deploy_target.sh makes.

State (each Cloud Run service's revisions and traffic table) lives in
$FAKE_GCLOUD_STATE; every invocation is appended to $FAKE_GCLOUD_LOG as JSON.
"""
from __future__ import annotations

import json
import os
import sys

STATE_PATH = os.environ["FAKE_GCLOUD_STATE"]
ARGS = sys.argv[1:]

with open(os.environ["FAKE_GCLOUD_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(ARGS) + "\n")

with open(STATE_PATH, encoding="utf-8") as handle:
    STATE = json.load(handle)


def flag(name: str) -> str | None:
    return ARGS[ARGS.index(name) + 1] if name in ARGS else None


def save() -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as handle:
        json.dump(STATE, handle)


def describe(name: str) -> int:
    service = STATE.get(name)
    if service is None:
        return 1
    print(json.dumps(service))
    return 0


def deploy(name: str) -> int:
    service = STATE.get(name)
    if service is None:
        return 1
    revision = f"{name}-{len(service['revisions']) + 1:05d}"
    service["revisions"].append(
        {"name": revision, "image": flag("--image"), "env": flag("--update-env-vars")}
    )
    tag = flag("--tag")
    traffic = [t for t in service["status"]["traffic"] if t.get("tag") != tag]
    traffic.append(
        {"revisionName": revision, "percent": 0, "tag": tag, "url": f"https://{tag}---{name}-x.a.run.app"}
    )
    service["status"]["traffic"] = traffic
    service["status"]["latestCreatedRevisionName"] = revision
    save()
    return 0


def update_traffic(name: str) -> int:
    service = STATE[name]
    if "--to-revisions" in ARGS:
        target = (flag("--to-revisions") or "").split("=")[0]
        traffic = [t for t in service["status"]["traffic"] if t.get("tag")]
        for entry in traffic:
            entry["percent"] = 100 if entry["revisionName"] == target else 0
        if not any(entry["revisionName"] == target for entry in traffic):
            traffic.append({"revisionName": target, "percent": 100})
        service["status"]["traffic"] = traffic
    if "--remove-tags" in ARGS:
        gone = flag("--remove-tags")
        kept = []
        for entry in service["status"]["traffic"]:
            if entry.get("tag") != gone:
                kept.append(entry)
            elif entry.get("percent"):
                entry.pop("tag")
                entry.pop("url", None)
                kept.append(entry)
        service["status"]["traffic"] = kept
    save()
    return 0


def main() -> int:
    if ARGS[:3] == ["run", "services", "describe"]:
        return describe(ARGS[3])
    if ARGS[:2] == ["run", "deploy"]:
        return deploy(ARGS[2])
    if ARGS[:3] == ["run", "services", "update-traffic"]:
        return update_traffic(ARGS[3])
    print(f"fake gcloud: unsupported {ARGS}", file=sys.stderr)
    return 2


sys.exit(main())
