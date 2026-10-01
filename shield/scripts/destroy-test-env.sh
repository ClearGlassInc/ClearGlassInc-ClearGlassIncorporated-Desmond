#!/usr/bin/env bash
# Destroy the disposable G01 topology: processes, namespaces, links, keys, state.
set -euo pipefail
cd "$(dirname "$0")/../.."
exec python3 -m shield.topology down
