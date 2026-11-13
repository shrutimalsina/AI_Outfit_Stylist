#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3.11 --version
node --version
npm --version
if command -v docker >/dev/null; then
    docker compose version
else
    echo "Docker Compose unavailable; native development remains available."
fi
if [[ -x .venv/bin/python ]]; then
    .venv/bin/python -m pip check
fi
