"""ClearGlassInc Artemis Corporate Lawyer Bot (Python).

Usage:
  export OPENAI_API_KEY="..."
  python tools/corporate_lawyer_bot.py --scenario "I'm a CEO facing a shareholder dispute over equity dilution."

Optional flags:
  --model gpt-5.3
  --temperature 0.2
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "prompts" / "corporate_lawyer_system_prompt.md"


def load_system_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"Missing prompt file: {PROMPT_PATH}")
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_user_prompt(scenario: str) -> str:
    return (
        "Current client scenario:\n"
        f"{scenario.strip()}\n\n"
        "Provide advice using the exact response contract in the system prompt."
    )


def run_bot(scenario: str, model: str, temperature: float) -> str:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    system_prompt = load_system_prompt()

    response = client.responses.create(
        model=model,
        temperature=temperature,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": build_user_prompt(scenario)},
        ],
    )

    return response.output_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ClearGlassInc Artemis Corporate Lawyer Bot.")
    parser.add_argument("--scenario", required=True, help="Client scenario to analyze.")
    parser.add_argument("--model", default="gpt-5.3", help="Model name.")
    parser.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = run_bot(args.scenario, args.model, args.temperature)
    print(output)


if __name__ == "__main__":
    main()
