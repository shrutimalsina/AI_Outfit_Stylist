"""Register a validated snapshot and activate it in one PostgreSQL transaction."""

import argparse
import os
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import psycopg
from psycopg.types.json import Jsonb

from backend.app.recommendations.engine import Catalog
from pipeline.prepare_dataset import read_json, sha256


def publish(url, manifest_path, snapshot):
    catalog = Catalog(snapshot)
    if sha256(manifest_path) != catalog.metadata["source_sha256"]:
        raise ValueError("Snapshot source checksum differs from the supplied manifest")
    manifest = read_json(manifest_path)
    source, revision = manifest["dataset"], manifest["revision"]
    dataset = uuid5(NAMESPACE_URL, f"{source}@{revision}")
    items = {row["id"]: uuid5(dataset, f"item:{row['id']}") for row in manifest["items"]}
    with psycopg.connect(url.replace("postgresql+psycopg://", "postgresql://", 1)) as db:
        db.execute("SELECT pg_advisory_xact_lock(731022)")
        db.execute("INSERT INTO datasets VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                   (dataset, source, revision))
        with db.cursor() as cursor:
            cursor.executemany("INSERT INTO items VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", [
                (items[row["id"]], dataset, row["id"], row["category"], Jsonb(row))
                for row in manifest["items"]
            ])
            for outfit in manifest["outfits"]:
                outfit_id = uuid5(dataset, f"outfit:{outfit['id']}")
                cursor.execute("INSERT INTO outfits VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                               (outfit_id, dataset, outfit["id"], outfit["split"]))
                cursor.executemany("INSERT INTO outfit_items VALUES (%s,%s) ON CONFLICT DO NOTHING",
                                   [(outfit_id, items[item_id]) for item_id in outfit["item_ids"]])
            cursor.execute("""
                INSERT INTO catalog_snapshots (id,dataset_id,manifest_path,matrix_sha256,dimension)
                VALUES (%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING
            """, (snapshot.name, dataset, str(snapshot.resolve()), catalog.metadata["matrix_sha256"], 512))
            cursor.executemany("INSERT INTO snapshot_items VALUES (%s,%s) ON CONFLICT DO NOTHING",
                               [(snapshot.name, items[row["id"]]) for row in catalog.items])
            cursor.executemany("INSERT INTO item_embeddings VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                               [(snapshot.name, items[row["id"]], index)
                                for index, row in enumerate(catalog.items)])
            cursor.execute("UPDATE catalog_snapshots SET active=false WHERE active AND id<>%s", (snapshot.name,))
            cursor.execute("UPDATE catalog_snapshots SET active=true WHERE id=%s", (snapshot.name,))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    publish(os.environ["DATABASE_URL"], args.manifest, args.snapshot)
