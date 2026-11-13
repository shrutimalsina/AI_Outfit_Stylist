#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export STYLIST_SNAPSHOT STYLIST_IMAGE_ROOT
case "${1:-fixture}" in
    fixture)
        STYLIST_IMAGE_ROOT=data/processed/fixture
        STYLIST_SNAPSHOT=$(.venv/bin/python -m scripts.create_fixture)
        echo "Using the synthetic catalog."
        ;;
    real)
        STYLIST_IMAGE_ROOT=data/raw/polyvore_images
        if [[ ! -s data/reports/polyvore-snapshot.txt ]]; then
            echo "Build the real catalog first. See the README dataset instructions." >&2
            exit 1
        fi
        STYLIST_SNAPSHOT=$(<data/reports/polyvore-snapshot.txt)
        if [[ ! -d "$STYLIST_SNAPSHOT" || ! -d "$STYLIST_IMAGE_ROOT" ]]; then
            echo "The saved snapshot or image directory is missing." >&2
            exit 1
        fi
        export HF_HUB_OFFLINE=1
        echo "Using the evaluated Polyvore catalog."
        ;;
    *)
        echo "Usage: bash scripts/run_demo.sh [fixture|real]" >&2
        exit 2
        ;;
esac
export HF_HOME="${HF_HOME:-$PWD/data/raw/hf-cache}"
unset DATABASE_URL
echo "Start the UI separately with npm --prefix frontend run dev."
exec .venv/bin/uvicorn backend.app.main:app --host 127.0.0.1
