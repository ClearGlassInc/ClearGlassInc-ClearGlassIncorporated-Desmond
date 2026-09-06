# Priority Matrix Bot

Generates a daily execution brief from a configurable priority matrix.

## Run

```bash
python -m bots.priority_matrix_bot          # render to terminal + write latest.{md,json} + archive
python -m bots.priority_matrix_bot --print  # render only, no files written
python -m bots.priority_matrix_bot --config operations/priority_matrix/config.json
```

## Customize the day

The bot ships with a default matrix. To override it without editing code, copy
the template and edit your values:

```bash
cp operations/priority_matrix/config.example.json operations/priority_matrix/config.json
```

`config.json` is read automatically and merged over the defaults (any key you
omit falls back to the default). It is git-ignored so your daily plan stays local.

## Outputs

- `latest.md` / `latest.json` — most recent brief (committed sample).
- `archive/<timestamp>.{md,json}` — per-run history (git-ignored).

## Toggle

Set `PRIORITY_MATRIX_ENABLED=false` to disable generation (e.g. in CI).
