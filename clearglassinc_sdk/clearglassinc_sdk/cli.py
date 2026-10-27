"""Command-line entrypoint: `clearglassinc chat` / `smoke` / `version`.

Provider selection is via environment variables so no code changes are needed
to swap backends:

    CLEARGLASS_PROVIDER=openai|anthropic|fake   (default: fake)
    OPENAI_API_KEY / ANTHROPIC_API_KEY
    CLEARGLASS_MODEL                            (provider-specific default if unset)

A missing package or credential is a configuration mistake, not a bug, so it
exits 2 with a single actionable line. It used to raise through `main` and
print a five-frame traceback, which buries the one fact the operator needs.
"""

from __future__ import annotations

import argparse
import os
import sys

from clearglassinc_sdk import Agent, Runner, __version__
from clearglassinc_sdk.clients.base import LLMClient

#: Exit code for "the environment is not configured for the chosen provider".
#: Distinct from 1, which means the agents ran and the result was a failure.
EXIT_PROVIDER_UNAVAILABLE = 2

#: Which credential each provider needs, and which extra installs its SDK.
_PROVIDER_REQUIREMENTS = {
    "anthropic": ("ANTHROPIC_API_KEY", "anthropic"),
    "openai": ("OPENAI_API_KEY", "openai"),
}


class ProviderUnavailable(Exception):
    """The selected provider cannot be used: no SDK installed, or no key set."""


def _build_client() -> LLMClient:
    provider = os.environ.get("CLEARGLASS_PROVIDER", "fake").lower()
    model = os.environ.get("CLEARGLASS_MODEL")

    if provider not in _PROVIDER_REQUIREMENTS and provider != "fake":
        raise ProviderUnavailable(
            f"CLEARGLASS_PROVIDER='{provider}' is not a provider. "
            "Use 'anthropic', 'openai', or 'fake' (offline, no key needed)."
        )

    if provider in _PROVIDER_REQUIREMENTS:
        key_name, extra = _PROVIDER_REQUIREMENTS[provider]
        if not os.environ.get(key_name):
            raise ProviderUnavailable(
                f"{key_name} is not set, which CLEARGLASS_PROVIDER='{provider}' requires. "
                "Export it, or unset CLEARGLASS_PROVIDER to run offline."
            )
        try:
            if provider == "anthropic":
                from clearglassinc_sdk.clients.anthropic_client import AnthropicClient

                return AnthropicClient(model=model or "claude-sonnet-5")
            from clearglassinc_sdk.clients.openai_client import OpenAIClient

            return OpenAIClient(model=model or "gpt-4o-mini")
        except ImportError:
            raise ProviderUnavailable(
                f"The '{extra}' package is not installed, which "
                f"CLEARGLASS_PROVIDER='{provider}' requires. "
                f"Install it with: pip install clearglassinc-sdk[{extra}]"
            ) from None

    from clearglassinc_sdk.testing import FakeLLMClient

    return FakeLLMClient()


def _cmd_chat(args: argparse.Namespace) -> int:
    client = _build_client()
    agent = Agent(
        name=args.name,
        instructions=args.instructions,
    )
    runner = Runner(agent, client)

    print(f"ClearGlassInc Agent SDK v{__version__} — agent '{agent.name}' ready. Ctrl+D to exit.")
    while True:
        try:
            prompt = input("> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not prompt.strip():
            continue
        result = runner.run(prompt)
        print(result.output)


def _cmd_smoke(args: argparse.Namespace) -> int:
    """One governed mission across three isolated agents. See `smoke.py`."""
    from clearglassinc_sdk.smoke import run_smoke

    provider = os.environ.get("CLEARGLASS_PROVIDER", "fake").lower()
    # The offline default uses the scripted client, whose facts still come from
    # the real tools. Any configured provider runs the same mission live.
    client = None if provider == "fake" else _build_client()
    if client is None and args.json is False:
        print("[SMOKE] provider=fake (offline; no credential required)")
    return run_smoke(client, inject_bogus=args.inject_bogus, as_json=args.json)


def _cmd_version(_args: argparse.Namespace) -> int:
    print(__version__)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clearglassinc", description="ClearGlassInc Agent SDK CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    chat_parser = subparsers.add_parser("chat", help="Start an interactive chat session with an agent")
    chat_parser.add_argument("--name", default="ClearGlassInc Agent")
    chat_parser.add_argument(
        "--instructions",
        default="You are a high-performance, futuristic automation agent.",
    )
    chat_parser.set_defaults(func=_cmd_chat)

    smoke_parser = subparsers.add_parser(
        "smoke",
        help="Run one governed mission: PLANNER -> WORKER -> CRITIC (offline by default)",
    )
    smoke_parser.add_argument(
        "--json", action="store_true", help="Emit the mission report as JSON only"
    )
    smoke_parser.add_argument(
        "--inject-bogus",
        action="store_true",
        help="Append one nonexistent path to the worker's claims, to prove the "
        "critic reports Unconfirmed and the command exits non-zero",
    )
    smoke_parser.set_defaults(func=_cmd_smoke)

    version_parser = subparsers.add_parser("version", help="Print the SDK version")
    version_parser.set_defaults(func=_cmd_version)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ProviderUnavailable as exc:
        # One line, no traceback: the operator needs the fix, not the frames.
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_PROVIDER_UNAVAILABLE


if __name__ == "__main__":
    sys.exit(main())
