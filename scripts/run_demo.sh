#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export STYLIST_IMAGE_ROOT=data/processed/fixture
export STYLIST_SNAPSHOT
STYLIST_SNAPSHOT=$(.venv/bin/python -m scripts.create_fixture)
export HF_HOME="${HF_HOME:-$PWD/data/raw/hf-cache}"
unset DATABASE_URL
echo "Synthetic catalog demonstration. Start the UI separately with npm --prefix frontend run dev."
exec .venv/bin/uvicorn backend.app.main:app --host 127.0.0.1
