"""Lookup the single active catalog using PostgreSQL."""

import os

import psycopg


def active_snapshot():
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url, connect_timeout=2) as connection:
        row = connection.execute("SELECT manifest_path FROM catalog_snapshots WHERE active").fetchone()
    return row[0] if row else None


def record_request(request_id, snapshot_id, category):
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url, connect_timeout=2) as connection:
        connection.execute(
            "INSERT INTO recommendation_requests (id,snapshot_id,input_category) VALUES (%s,%s,%s)",
            (request_id, snapshot_id, category),
        )


def load_evaluation(run_id):
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url, connect_timeout=2) as connection:
        row = connection.execute("SELECT report FROM evaluation_runs WHERE id=%s", (run_id,)).fetchone()
    return row[0] if row else None
