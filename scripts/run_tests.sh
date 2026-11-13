#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/ruff check backend pipeline scripts
.venv/bin/python -m pytest backend/tests "$@"
npm --prefix frontend run build
