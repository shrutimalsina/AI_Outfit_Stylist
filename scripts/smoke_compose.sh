#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export COMPOSE_FILE=docker-compose.yml:docker-compose.production.yml
export COMPOSE_PROJECT_NAME="stylist-smoke-${GITHUB_RUN_ID:-$$}"
export POSTGRES_PASSWORD=local_smoke_only
mode=${1:-fixture}
case "$mode" in
    fixture)
        export STYLIST_IMAGE_ROOT=/app/data/processed/compose-fixture
        manifest="$STYLIST_IMAGE_ROOT/manifest.json"
        ;;
    real)
        export STYLIST_IMAGE_ROOT=/app/data/raw/polyvore_images
        manifest=/app/data/processed/original-polyvore.json
        saved=$(<data/reports/polyvore-snapshot.txt)
        snapshot="/app/data/embeddings/${saved##*/}"
        test -f "data/processed/original-polyvore.json"
        test -f "data/embeddings/${saved##*/}/metadata.json"
        test -d data/raw/polyvore_images
        ;;
    *)
        echo "Usage: bash scripts/smoke_compose.sh [fixture|real]" >&2
        exit 2
        ;;
esac
command -v docker >/dev/null || { echo "Docker with Compose is required." >&2; exit 1; }
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
if [[ "$mode" == fixture ]]; then
    snapshot=$(docker compose -f docker-compose.yml run --rm --no-deps -T backend python -m scripts.create_fixture "$STYLIST_IMAGE_ROOT")
fi
docker compose exec -T backend python -m pipeline.publish_catalog "$manifest" "$snapshot"
docker compose restart backend

base="http://127.0.0.1:$STYLIST_HTTP_PORT"
curl -fsS --retry 30 --retry-delay 2 --retry-all-errors --retry-max-time 60 "$base/api/v1/catalog" > /dev/null
curl -fsS "$base/health/live" > /dev/null
page=$(curl -fsS "$base/")
[[ "$page" == *"AI Outfit Stylist"* ]]
if [[ "$mode" == real ]]; then
    curl -fsS --max-time 120 "$base/health/ready" >/dev/null
    query=$(python3 -c '
import json, sys
with open(sys.argv[1]) as stream:
    print(next(row["image"] for row in json.load(stream) if row["category"] == "top"))
' "data/embeddings/${saved##*/}/items.json")
    curl -fsS --max-time 120 -F category=top -F "image=@data/raw/polyvore_images/$query" \
        "$base/api/v1/recommendations"
else
    curl -fsS -H 'Content-Type: application/json' -d '{"item_id":"1","top_k":3}' \
        "$base/api/v1/recommendations/by-item"
fi | python3 -c '
import json, sys
result = json.load(sys.stdin)
assert [item["category"] for item in result["recommendations"]] == ["bottom", "outerwear", "footwear"]
for item in result["recommendations"]:
    print(item["image_url"])
' | while IFS= read -r image_url; do
    curl -fsS "$base$image_url" > /dev/null
done
echo "Compose smoke test passed"
