"""Live persistence round trip against a migrated PostgreSQL test database."""

import os

from fastapi.testclient import TestClient
import psycopg
import pytest

from backend.app.main import create_app
from backend.app.recommendations.engine import DEFAULT_POLICY, Catalog
from pipeline.publish_catalog import publish
from pipeline.register_evaluation import register
from pipeline.run_evaluation import run
from scripts.create_fixture import build


@pytest.mark.skipif(not os.getenv("STYLIST_TEST_DATABASE_URL"), reason="Dedicated PostgreSQL test URL required")
def test_publish_evaluate_and_recommend(tmp_path, monkeypatch):
    url = os.environ["STYLIST_TEST_DATABASE_URL"]
    monkeypatch.setenv("DATABASE_URL", url)
    snapshot = build(tmp_path)
    manifest = tmp_path / "manifest.json"
    publish(url, manifest, snapshot)
    publish(url, manifest, snapshot)
    report = run(manifest, snapshot, DEFAULT_POLICY, "valid")
    run_id = register(url, report)
    with TestClient(create_app(Catalog(snapshot), lambda: object(), tmp_path)) as client:
        assert client.get("/health/ready").status_code == 200
        saved = client.get(f"/api/v1/evaluations/{run_id}")
        assert saved.json()["eligible_cases"] == report["eligible_cases"]
        response = client.post("/api/v1/recommendations/by-item", json={"item_id": "1"})
        assert response.status_code == 200
    with psycopg.connect(url) as db:
        assert db.execute("SELECT count(*) FROM catalog_snapshots WHERE active").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM item_embeddings WHERE snapshot_id=%s",
                          (snapshot.name,)).fetchone()[0] == 4
        assert db.execute("SELECT count(*) FROM evaluation_cases WHERE run_id=%s",
                          (run_id,)).fetchone()[0] == len(report["cases"])
        assert db.execute("SELECT input_category FROM recommendation_requests WHERE id=%s",
                          (response.json()["request_id"],)).fetchone()[0] == "top"
