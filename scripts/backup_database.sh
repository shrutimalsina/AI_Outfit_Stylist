#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
output=${1:?Usage: bash scripts/backup_database.sh output.sql}
temporary=$(mktemp "${output}.XXXXXX")
trap 'rm -f -- "$temporary"' EXIT
docker compose exec -T database pg_dump -U stylist -d stylist > "$temporary"
mv -- "$temporary" "$output"
