#!/usr/bin/env bash
# SENTINEL demo runner.
#   ./run.sh         -> narrated mission scenarios (pure stdlib, no install)
#   ./run.sh serve   -> boot the FastAPI service (installs fastapi/uvicorn)
set -euo pipefail
cd "$(dirname "$0")"

if [[ "${1:-}" == "serve" ]]; then
  python -m pip install -q -r requirements.txt
  exec python -m sentinel.demo --serve
fi

exec python -m sentinel.demo
