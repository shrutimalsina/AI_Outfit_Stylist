#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3.11 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-app.txt
npm --prefix frontend ci
