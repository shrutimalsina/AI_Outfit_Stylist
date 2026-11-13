#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export COMPOSE_FILE=docker-compose.yml:docker-compose.production.yml
export COMPOSE_PROJECT_NAME="stylist-smoke-${GITHUB_RUN_ID:-$$}"
export POSTGRES_PASSWORD=local_smoke_only
export STYLIST_IMAGE_ROOT=/app/data/processed/compose-fixture
export STYLIST_HTTP_PORT=${STYLIST_HTTP_PORT:-15175}

cleanup() {
    status=$?
    if (( status != 0 )); then
        docker compose logs --no-color || true
    fi
    docker compose down --volumes || true
}
trap cleanup EXIT

docker compose config --quiet
docker compose up --build --wait --wait-timeout 120
snapshot=$(docker compose -f docker-compose.yml run --rm --no-deps -T backend python -m scripts.create_fixture "$STYLIST_IMAGE_ROOT")
docker compose exec -T backend python -m pipeline.publish_catalog "$STYLIST_IMAGE_ROOT/manifest.json" "$snapshot"
docker compose restart backend

base="http://127.0.0.1:$STYLIST_HTTP_PORT"
curl -fsS --retry 30 --retry-delay 2 --retry-all-errors --retry-max-time 60 "$base/api/v1/catalog" > /dev/null
curl -fsS "$base/health/live" > /dev/null
page=$(curl -fsS "$base/")
[[ "$page" == *"AI Outfit Stylist"* ]]
curl -fsS -H 'Content-Type: application/json' -d '{"item_id":"1","top_k":3}' \
    "$base/api/v1/recommendations/by-item" | python3 -c '
import json, sys
result = json.load(sys.stdin)
assert [item["category"] for item in result["recommendations"]] == ["bottom", "outerwear", "footwear"]
print(result["recommendations"][0]["image_url"])
' | while IFS= read -r image_url; do
    curl -fsS "$base$image_url" > /dev/null
done
echo "Compose smoke test passed"
