"""Lookup the single active catalog using PostgreSQL."""

import os

import psycopg


def active_snapshot():
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url, connect_timeout=2) as connection:
        row = connection.execute("SELECT manifest_path FROM catalog_snapshots WHERE active").fetchone()
    return row[0] if row else None
