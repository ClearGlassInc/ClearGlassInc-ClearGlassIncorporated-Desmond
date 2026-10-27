"""One governed smoke mission: PLANNER -> WORKER -> CRITIC.

Why this exists
---------------
The repository holds 32 ``agents/*/agent.json`` definitions and three
stdlib-only planners (``agent_army.orchestrator``, ``agent_os``,
``sentinel.demo``), but nothing that proves an agent in this SDK can be
invoked and complete a real task end to end. This module is that proof, and
it is built only from what ``clearglassinc_sdk`` already provides: ``Agent``,
``Runner``, ``Tool`` and the provider-agnostic ``LLMClient``.

Three properties matter here, in this order:

* **Contexts are isolated.** Each role is a separate ``Agent``, so each owns a
  separate ``Memory`` (``agent.py``: ``memory: Memory = field(default_factory=
  Memory)``). The worker is handed one plan step as text; it never receives the
  planner's transcript, and the critic never receives the worker's. ``--json``
  reports the isolation check so a regression is visible rather than assumed.

* **The claims and the verdict are real, not narrated.** The worker's file list
  comes from ``list_repo_files``, which globs the actual working tree. The
  critic's Confirmed/Unconfirmed verdict comes from ``verify_claims``, which
  stats each path on disk. Both are ordinary Python, so the offline provider
  cannot fake a pass: scripting only supplies the natural-language glue
  between turns. This mirrors the repository's standing rule that the agent
  proposes and the governor decides.

* **It runs with no credential.** ``CLEARGLASS_PROVIDER`` defaults to ``fake``,
  so the happy path needs no API key and no network. Setting the variable to
  ``anthropic`` runs the identical mission against a live model with no code
  change.

Usage::

    python -m clearglassinc_sdk.cli smoke
    python -m clearglassinc_sdk.cli smoke --json
    python -m clearglassinc_sdk.cli smoke --inject-bogus   # prove Unconfirmed

Exit status: 0 when every claim is Confirmed, 1 when any claim is
Unconfirmed or an agent fails.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from clearglassinc_sdk.agent import Agent
from clearglassinc_sdk.clients.base import CompletionResult, LLMClient, ToolCall
from clearglassinc_sdk.memory import Message
from clearglassinc_sdk.runner import Runner
from clearglassinc_sdk.tools import Tool

# Model pinning. The planner does the hard reasoning; the two downstream roles
# are ordinary workers. Only consulted when a real provider is selected — the
# offline default ignores them.
PLANNER_MODEL = "claude-opus-5"
WORKER_MODEL = "claude-sonnet-5"
CRITIC_MODEL = "claude-sonnet-5"

#: The worker's assignment. Narrow on purpose: one pattern, one directory.
SMOKE_PATTERN = "*.py"
SMOKE_DIRECTORY = "clearglassinc_sdk"

#: Claims are capped so a live model gets a bounded prompt and the critic a
#: bounded amount of work.
MAX_CLAIMS = 12

_BOGUS_CLAIM = "clearglassinc_sdk/this_file_does_not_exist.py"


# --------------------------------------------------------------------------- #
# Tools. These do the real work; the model only decides when to call them.
# --------------------------------------------------------------------------- #


def _repo_root() -> Path:
    """The repository root, derived from this file's location."""
    return Path(__file__).resolve().parent.parent.parent


def list_repo_files(directory: str, pattern: str) -> str:
    """List repository files under a directory matching a glob pattern.

    Returns one repository-relative path per line, sorted, capped at
    MAX_CLAIMS entries.
    """
    root = _repo_root()
    target = (root / directory).resolve()
    # Keep the tool inside the repository: a traversing argument returns
    # nothing rather than reaching the wider filesystem.
    if not target.is_dir() or root not in target.parents and target != root:
        return ""
    matches = sorted(
        str(path.relative_to(root)) for path in target.rglob(pattern) if path.is_file()
    )
    return "\n".join(matches[:MAX_CLAIMS])


def verify_claims(claims: str) -> str:
    """Check each claimed repository path against the filesystem.

    Returns one ``Confirmed <path>`` or ``Unconfirmed <path>`` line per claim.
    """
    root = _repo_root()
    verdicts: list[str] = []
    for line in claims.splitlines():
        claim = line.strip().lstrip("-*0123456789. ").strip()
        if not claim:
            continue
        exists = (root / claim).is_file()
        verdicts.append(f"{'Confirmed' if exists else 'Unconfirmed'} {claim}")
    return "\n".join(verdicts)


# --------------------------------------------------------------------------- #
# Offline provider. Supplies the language between turns, never the facts.
# --------------------------------------------------------------------------- #


@dataclass
class ScriptedSmokeClient(LLMClient):
    """The offline stand-in for a model, used when no provider is configured.

    It decides *when* to call a tool and relays what the tool returned. It
    never invents a path or a verdict: every fact in the transcript comes from
    ``list_repo_files`` or ``verify_claims``. That is what makes the offline
    run meaningful rather than a rehearsal.
    """

    plan_steps: list[str] = field(default_factory=list)

    def _last_tool_result(self, messages: list[Message]) -> str | None:
        for message in reversed(messages):
            if message.role == "tool":
                return message.content
        return None

    def complete(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float = 0.7,
    ) -> CompletionResult:
        tool_result = self._last_tool_result(messages)
        if tool_result is not None:
            # A tool has run: report exactly what it returned.
            return CompletionResult(content=tool_result)

        available = {schema["name"] for schema in (tools or [])}
        prompt = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            "",
        )

        if "list_repo_files" in available:
            return CompletionResult(
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_list",
                        name="list_repo_files",
                        arguments={"directory": SMOKE_DIRECTORY, "pattern": SMOKE_PATTERN},
                    )
                ],
            )
        if "verify_claims" in available:
            return CompletionResult(
                content="",
                tool_calls=[
                    ToolCall(
                        id="call_verify",
                        name="verify_claims",
                        arguments={"claims": _claims_block(prompt)},
                    )
                ],
            )
        # No tools: this is the planner.
        return CompletionResult(content="\n".join(self.plan_steps))


def _claims_block(prompt: str) -> str:
    """Pull the claim list out of the critic's prompt."""
    _, _, block = prompt.partition("CLAIMS:")
    return block.strip() or prompt.strip()


# --------------------------------------------------------------------------- #
# The mission.
# --------------------------------------------------------------------------- #


def _plan_steps() -> list[str]:
    return [
        f"1. List every {SMOKE_PATTERN} file under {SMOKE_DIRECTORY}/ using the file-listing tool.",
        "2. Report the paths found, one per line, with no commentary.",
        "3. Hand the reported paths to the critic for verification against disk.",
    ]


def build_planner() -> Agent:
    return Agent(
        name="PLANNER",
        instructions=(
            "You are the planner. Emit exactly three numbered steps that "
            "instruct a worker to enumerate repository files and a critic to "
            "verify the result. Output the steps only, no preamble."
        ),
        model=PLANNER_MODEL,
        temperature=0.0,
    )


def build_worker() -> Agent:
    worker = Agent(
        name="WORKER",
        instructions=(
            "You are the worker. Carry out the single step you are given by "
            "calling the file-listing tool. Then output the file paths exactly "
            "as the tool returned them, one per line, with no commentary and "
            "no paths you did not receive from the tool."
        ),
        model=WORKER_MODEL,
        temperature=0.0,
    )
    worker.add_tool(
        Tool(
            name="list_repo_files",
            description="List repository files under a directory matching a glob pattern.",
            func=list_repo_files,
        )
    )
    return worker


def build_critic() -> Agent:
    critic = Agent(
        name="CRITIC",
        instructions=(
            "You are the critic. You do not trust the claims you are given. "
            "Pass them to the verification tool and report its verdict "
            "verbatim: one Confirmed or Unconfirmed line per claim."
        ),
        model=CRITIC_MODEL,
        temperature=0.0,
    )
    critic.add_tool(
        Tool(
            name="verify_claims",
            description="Check each claimed repository path against the filesystem.",
            func=verify_claims,
        )
    )
    return critic


def _log(role: str, message: str) -> None:
    for line in message.splitlines() or [""]:
        print(f"[{role}] {line}")


def run_smoke(
    client: LLMClient | None = None,
    *,
    inject_bogus: bool = False,
    as_json: bool = False,
) -> int:
    """Run the planner -> worker -> critic mission. Returns a process exit code."""
    llm = client if client is not None else ScriptedSmokeClient(plan_steps=_plan_steps())

    planner = build_planner()
    worker = build_worker()
    critic = build_critic()

    # ---- PLANNER ---------------------------------------------------------- #
    plan_result = Runner(planner, llm).run(
        f"Plan the verification of every {SMOKE_PATTERN} file under {SMOKE_DIRECTORY}/."
    )
    steps = [line.strip() for line in plan_result.output.splitlines() if line.strip()]
    if not as_json:
        _log("PLANNER", f"{len(steps)} step plan:")
        _log("PLANNER", plan_result.output)

    # ---- WORKER ----------------------------------------------------------- #
    # Handed one step as text. Not the planner's Agent, Memory or transcript.
    assignment = steps[0] if steps else "List the repository files."
    worker_result = Runner(worker, llm).run(assignment)
    claims = [line.strip() for line in worker_result.output.splitlines() if line.strip()]
    if inject_bogus:
        claims.append(_BOGUS_CLAIM)
    if not as_json:
        _log("WORKER", f"tool calls resolved in {worker_result.steps} step(s)")
        _log("WORKER", f"{len(claims)} claim(s):")
        _log("WORKER", "\n".join(claims))

    # ---- CRITIC ----------------------------------------------------------- #
    # Receives only the claim list, never the worker's transcript.
    critic_result = Runner(critic, llm).run(
        "Verify every claimed path against the filesystem.\n\nCLAIMS:\n" + "\n".join(claims)
    )
    verdicts = [line.strip() for line in critic_result.output.splitlines() if line.strip()]
    confirmed = [v for v in verdicts if v.startswith("Confirmed")]
    unconfirmed = [v for v in verdicts if v.startswith("Unconfirmed")]
    if not as_json:
        _log("CRITIC", f"{len(verdicts)} verdict(s):")
        _log("CRITIC", "\n".join(verdicts))

    # ---- Context isolation, asserted rather than assumed ------------------ #
    isolation_ok = _contexts_isolated(planner, worker, critic)

    ok = (
        bool(claims)
        and bool(verdicts)
        and len(verdicts) == len(claims)
        and not unconfirmed
        and isolation_ok
    )

    if as_json:
        print(
            json.dumps(
                {
                    "status": "OK" if ok else "FAIL",
                    "provider": os.environ.get("CLEARGLASS_PROVIDER", "fake"),
                    "contexts_isolated": isolation_ok,
                    "planner": {"model": PLANNER_MODEL, "steps": steps},
                    "worker": {"model": WORKER_MODEL, "claims": claims},
                    "critic": {
                        "model": CRITIC_MODEL,
                        "confirmed": confirmed,
                        "unconfirmed": unconfirmed,
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        _log("CRITIC", f"{len(confirmed)} Confirmed, {len(unconfirmed)} Unconfirmed")
        _log("SMOKE", f"contexts isolated: {isolation_ok}")
        _log("SMOKE", "OK" if ok else "FAIL")

    return 0 if ok else 1


def _contexts_isolated(planner: Agent, worker: Agent, critic: Agent) -> bool:
    """True when no role's memory holds another role's instructions.

    Isolation is structural — a fresh ``Memory`` per ``Agent`` — so this is a
    regression guard, not the mechanism.
    """
    memories = {
        "PLANNER": planner.memory.history(),
        "WORKER": worker.memory.history(),
        "CRITIC": critic.memory.history(),
    }
    if len({id(history) for history in memories.values()}) != 3:
        return False
    fingerprints = {
        "PLANNER": planner.instructions,
        "WORKER": worker.instructions,
        "CRITIC": critic.instructions,
    }
    for role, history in memories.items():
        blob = "\n".join(message.content for message in history)
        for other_role, fingerprint in fingerprints.items():
            if other_role != role and fingerprint in blob:
                return False
    return True
