#!/usr/bin/env bash
# Exit non-zero if any namespace, link, socket, process or key from G01 remains.
set -euo pipefail
cd "$(dirname "$0")/../.."
exec python3 -m shield.topology verify-clean
