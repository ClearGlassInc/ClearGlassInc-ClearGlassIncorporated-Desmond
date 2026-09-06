#!/usr/bin/env python3
"""
ClearGlass AI Automation Runtime v0.2
OpenAI API + Scheduler + Memory + Telegram/Slack alerts

Security rule:
- Never hardcode secrets.
- Set credentials through environment variables only.

Required environment:
  OPENAI_API_KEY

Optional environment:
  OPENAI_MODEL=gpt-4.1-mini
  CLEARGLASS_MEMORY_PATH=automation/memory/clearglass_memory.jsonl
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
  SLACK_WEBHOOK_URL

Run once:
  python automation/v0.2/clearglass_agent_runtime.py --task "Build tomorrow's ClearGlass execution plan"

Run scheduler:
  python automation/v0.2/clearglass_agent_runtime.py --schedule
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
DEFAULT_MEMORY_PATH = os.getenv("CLEARGLASS_MEMORY_PATH", "automation/memory/clearglass_memory.jsonl")


@dataclass
class AgentResult:
    agent: str
    output: str
    timestamp: str


class JsonlMemory:
    def __init__(self, path: str = DEFAULT_MEMORY_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, record: Dict[str, Any]) -> None:
        record["written_at"] = datetime.now(timezone.utc).isoformat()
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def recent(self, limit: int = 8) -> List[Dict[str, Any]]:
        lines = self.path.read_text(encoding="utf-8").splitlines()
        records = []
        for line in lines[-limit:]:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return records


class AlertBus:
    def __init__(self) -> None:
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    def send(self, title: str, body: str) -> None:
        message = f"{title}\n\n{body}"
        self._telegram(message)
        self._slack(message)

    def _telegram(self, message: str) -> None:
        if not self.telegram_token or not self.telegram_chat_id:
            return
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = json.dumps({"chat_id": self.telegram_chat_id, "text": message}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=10).read()
        except Exception as exc:
            print(f"Telegram alert failed: {exc}", file=sys.stderr)

    def _slack(self, message: str) -> None:
        if not self.slack_webhook_url:
            return
        payload = json.dumps({"text": message}).encode("utf-8")
        req = urllib.request.Request(self.slack_webhook_url, data=payload, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=10).read()
        except Exception as exc:
            print(f"Slack alert failed: {exc}", file=sys.stderr)


class ClearGlassRuntime:
    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        if OpenAI is None:
            raise RuntimeError("Missing dependency: pip install openai")
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI()
        self.model = model
        self.memory = JsonlMemory()
        self.alerts = AlertBus()

    def ask(self, agent: str, system: str, user: str) -> AgentResult:
        recent_memory = json.dumps(self.memory.recent(), ensure_ascii=False, indent=2)
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Recent memory:\n{recent_memory}\n\nTask:\n{user}"},
            ],
        )
        output = response.output_text.strip()
        result = AgentResult(agent=agent, output=output, timestamp=datetime.now(timezone.utc).isoformat())
        self.memory.append(asdict(result))
        return result

    def run(self, task: str) -> Dict[str, Any]:
        intake = self.ask(
            "Intake Agent",
            "You extract objective, constraints, required output, risk, owner, and deadline. Be concise and operational.",
            task,
        )
        planner = self.ask(
            "Planner Agent",
            "You convert the intake brief into ordered execution steps, dependencies, and acceptance criteria.",
            intake.output,
        )
        executor = self.ask(
            "Executor Agent",
            "You produce the artifact or execution draft. Prioritize shipping usable work over commentary.",
            planner.output,
        )
        auditor = self.ask(
            "Auditor Agent",
            "You audit for errors, missing assumptions, security issues, compliance risk, and operational drift.",
            executor.output,
        )
        logger = self.ask(
            "Logger Agent",
            "You summarize the run: status, success metric, blockers, and next action.",
            auditor.output,
        )
        result = {
            "task": task,
            "model": self.model,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "results": [asdict(x) for x in [intake, planner, executor, auditor, logger]],
        }
        self.memory.append({"agent": "Runtime", "output": result, "timestamp": datetime.now(timezone.utc).isoformat()})
        self.alerts.send("ClearGlass v0.2 Run Complete", logger.output[:3500])
        return result


def run_scheduler(runtime: ClearGlassRuntime, interval_minutes: int) -> None:
    task = "Run ClearGlass daily operations scan: priorities, blockers, revenue opportunities, security risks, and next actions."
    while True:
        print(f"[{datetime.now().isoformat()}] Scheduler run started")
        runtime.run(task)
        print(f"[{datetime.now().isoformat()}] Sleeping {interval_minutes} minutes")
        time.sleep(interval_minutes * 60)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default="Run ClearGlass daily operations scan")
    parser.add_argument("--schedule", action="store_true")
    parser.add_argument("--interval-minutes", type=int, default=1440)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    runtime = ClearGlassRuntime(model=args.model)
    if args.schedule:
        run_scheduler(runtime, args.interval_minutes)
    else:
        result = runtime.run(args.task)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
