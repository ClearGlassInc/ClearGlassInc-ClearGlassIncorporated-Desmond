# Contributing to ClearGlassInc Artemis

## Branch strategy

| Branch | Purpose |
|---|---|
| `main` | Production. Protected. All changes via pull request. |
| `claude/<scope>-<id>` | AI-assisted automation branches. Merged by the ops team. |
| `feature/<scope>` | Human-authored feature work. |
| `fix/<scope>` | Bug fixes and hotpatches. |

Branch names should be lowercase, hyphen-separated, and scoped to the change area (e.g., `feature/finance-forecast-api`).

## Development workflow

1. Branch from `main`.
2. Make the smallest safe change that accomplishes the goal.
3. Run tests locally before pushing.
4. Open a pull request against `main` with a clear title and description.
5. CI must pass before merge.

## Python tooling

Python 3.11 is required. All bot and script logic lives in `bots/` and `scripts/`.

```bash
# Set up environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run all tests
python -m pytest

# Run a single module
python -m pytest tests/test_operations_finance_bot.py -v
```

Test configuration is defined in `pyproject.toml`. Do not modify `tests/conftest.py` without a clear reason — it manages the Python path for all test imports.

## Finance automation (operations finance bot)

The finance model in `bots/operations_finance_bot.py` uses Python's `Decimal` for all monetary arithmetic. Do not use `float` for any financial calculation.

**Adding a new financial metric:**
1. Add the input field to `ModelInputs` (frozen dataclass).
2. Add the computed field to `ModelOutputs` (frozen dataclass).
3. Update `load_inputs()` to read from `os.getenv()`.
4. Update `calculate_outputs()` with the formula.
5. Update `build_markdown()` to include the metric in the output report.
6. Add a corresponding test in `tests/test_operations_finance_bot.py`.
7. Expose the input as a `workflow_dispatch` parameter in `.github/workflows/operations-finance-bot.yml`.

**Output files:**
- `operations/output/latest.md` — human-readable finance report (most recent run).
- `operations/output/latest.json` — machine-readable payload for downstream integration.
- `operations/output/archive/<timestamp>.md` — immutable historical record.

## CI and workflow standards

- All workflows must declare explicit `permissions:` blocks (principle of least privilege).
- Scheduled bots commit output with `[skip ci]` in the message to prevent feedback loops.
- Workflow dispatch inputs must mirror all environment variables the target script reads.
- Test jobs must cache pip dependencies using `cache: pip`.

## Security

Do not commit secrets, API keys, tokens, or credentials. Use GitHub Actions secrets for all sensitive values. See `SECURITY.md` for the vulnerability reporting process.

## Code style

- No speculative abstractions. Solve the problem at hand.
- Financial calculations use `Decimal` throughout.
- Dataclasses are frozen (`frozen=True`) to enforce immutability on model inputs and outputs.
- Output files are UTF-8 encoded.
- No runtime dependencies beyond the Python standard library unless explicitly added to `requirements.txt`.
