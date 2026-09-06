# Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
# Proprietary and confidential. See LICENSE for terms.
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "operations" / "output" / "repo_task_audit"
ARCHIVE_DIR = OUTPUT_DIR / "archive"

CHECKBOX_RE = re.compile(r"^\s*[-*]\s*\[(?P<state>[ xX])\]\s*(?P<body>.+)$")
BOT_HINT_RE = re.compile(r"\b(bot|agent|automation)\b", re.IGNORECASE)


@dataclass(frozen=True)
class TaskRecord:
    file: str
    line: int
    done: bool
    text: str


@dataclass(frozen=True)
class RepoTaskAuditStatus:
    run_utc: str
    scanned_files: int
    bot_task_total: int
    bot_task_completed: int
    bot_task_pending: int


def _is_bot_task(text: str) -> bool:
    return bool(BOT_HINT_RE.search(text))


def collect_bot_tasks(root: Path = ROOT) -> list[TaskRecord]:
    tasks: list[TaskRecord] = []
    for file_path in sorted(root.rglob("*.md")):
        if ".git" in file_path.parts:
            continue
        rel = file_path.relative_to(root)
        for number, raw_line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
            match = CHECKBOX_RE.match(raw_line)
            if not match:
                continue
            body = match.group("body").strip()
            if not _is_bot_task(body):
                continue
            tasks.append(
                TaskRecord(
                    file=str(rel),
                    line=number,
                    done=match.group("state").lower() == "x",
                    text=body,
                )
            )
    return tasks


def build_status(tasks: list[TaskRecord], scanned_files: int) -> RepoTaskAuditStatus:
    completed = sum(1 for task in tasks if task.done)
    total = len(tasks)
    return RepoTaskAuditStatus(
        run_utc=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        scanned_files=scanned_files,
        bot_task_total=total,
        bot_task_completed=completed,
        bot_task_pending=total - completed,
    )


def build_markdown(status: RepoTaskAuditStatus, tasks: list[TaskRecord]) -> str:
    lines = [
        "# Repo Task Audit Bot Output",
        "",
        f"- Run (UTC): {status.run_utc}",
        f"- Markdown files scanned: {status.scanned_files}",
        f"- Bot tasks total: {status.bot_task_total}",
        f"- Bot tasks completed: {status.bot_task_completed}",
        f"- Bot tasks pending: {status.bot_task_pending}",
        "",
        "## Pending bot tasks",
    ]

    pending = [task for task in tasks if not task.done]
    if not pending:
        lines.append("- None. All bot-tagged tasks are complete.")
    else:
        lines.extend(
            f"- `{task.file}:{task.line}` — {task.text}"
            for task in pending
        )

    return "\n".join(lines) + "\n"


def write_outputs(status: RepoTaskAuditStatus, tasks: list[TaskRecord]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    latest_md = OUTPUT_DIR / "latest.md"
    latest_json = OUTPUT_DIR / "latest.json"
    stamp = status.run_utc.replace("+00:00", "Z").replace(":", "")
    archive_md = ARCHIVE_DIR / f"{stamp}.md"

    latest_md.write_text(build_markdown(status, tasks), encoding="utf-8")
    latest_json.write_text(
        json.dumps(
            {
                "status": asdict(status),
                "tasks": [asdict(task) for task in tasks],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    archive_md.write_text(build_markdown(status, tasks), encoding="utf-8")


def run(root: Path = ROOT) -> RepoTaskAuditStatus:
    scanned = sum(1 for _ in root.rglob("*.md"))
    tasks = collect_bot_tasks(root)
    status = build_status(tasks, scanned)
    write_outputs(status, tasks)
    return status


if __name__ == "__main__":
    summary = run(ROOT)
    print(
        "Repo task audit complete:",
        f"{summary.bot_task_completed}/{summary.bot_task_total} bot tasks complete",
    )
