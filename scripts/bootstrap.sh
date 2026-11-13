#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3.11 -m venv .venv
.venv/bin/python -m pip install uv==0.8.22
UV_PROJECT_ENVIRONMENT="$PWD/.venv" .venv/bin/uv sync --project backend --locked --all-extras --inexact
npm --prefix frontend ci
