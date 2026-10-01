#!/usr/bin/env bash
# Build the disposable G01 topology. Prints safe identities (fingerprints only).
set -euo pipefail
cd "$(dirname "$0")/../.."
exec python3 -m shield.topology up
