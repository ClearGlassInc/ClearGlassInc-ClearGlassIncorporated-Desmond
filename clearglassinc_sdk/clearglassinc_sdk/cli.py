"""Command-line entrypoint: `clearglassinc chat` / `clearglassinc version`.

Provider selection is via environment variables so no code changes are needed
to swap backends:

    CLEARGLASS_PROVIDER=openai|anthropic|fake   (default: fake)
    OPENAI_API_KEY / ANTHROPIC_API_KEY
    CLEARGLASS_MODEL                            (provider-specific default if unset)
"""

from __future__ import annotations

import argparse
import os
import sys

from clearglassinc_sdk import Agent, Runner, __version__
from clearglassinc_sdk.clients.base import LLMClient


def _build_client() -> LLMClient:
    provider = os.environ.get("CLEARGLASS_PROVIDER", "fake").lower()
    model = os.environ.get("CLEARGLASS_MODEL")

    if provider == "openai":
        from clearglassinc_sdk.clients.openai_client import OpenAIClient

        return OpenAIClient(model=model or "gpt-4o-mini")
    if provider == "anthropic":
        from clearglassinc_sdk.clients.anthropic_client import AnthropicClient

        return AnthropicClient(model=model or "claude-sonnet-5")

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

    version_parser = subparsers.add_parser("version", help="Print the SDK version")
    version_parser.set_defaults(func=_cmd_version)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
