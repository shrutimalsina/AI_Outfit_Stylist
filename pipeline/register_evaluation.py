"""Register a completed evaluation against its published snapshot."""

import argparse
import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from pipeline.prepare_dataset import read_json


def register(url, report):
    metadata = report["provenance"]["catalog"]
    snapshot = metadata["snapshot_id"]
    run_id = uuid4()
    url = url.replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(url) as db:
        row = db.execute(
            "SELECT dataset_id, matrix_sha256 FROM catalog_snapshots WHERE id=%s",
            (snapshot,),
        ).fetchone()
        if not row or row[1] != metadata["matrix_sha256"]:
            raise ValueError("Publish the matching catalog snapshot before registering an evaluation")
        dataset_id = row[0]
        items = dict(db.execute("SELECT source_id,id FROM items WHERE dataset_id=%s", (dataset_id,)))
        outfits = dict(db.execute("SELECT source_id,id FROM outfits WHERE dataset_id=%s", (dataset_id,)))
        cases = []
        for case in report["cases"]:
            outfit, query, hidden = (
                outfits.get(case["outfit_id"]), items.get(case["query_id"]), items.get(case["hidden_id"]),
            )
            if not all((outfit, query, hidden)):
                if "exclusion" not in case:
                    raise ValueError("Eligible evaluation case references missing source metadata")
                continue
            cases.append((run_id, outfit, query, hidden, Jsonb(case)))
        db.execute("INSERT INTO evaluation_runs (id,snapshot_id,report) VALUES (%s,%s,%s)",
                   (run_id, snapshot, Jsonb({**report, "run_id": str(run_id)})))
        with db.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO evaluation_cases (run_id,outfit_id,query_id,hidden_id,outcome) VALUES (%s,%s,%s,%s,%s)",
                cases,
            )
    return run_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    print(register(os.environ["DATABASE_URL"], read_json(parser.parse_args().report)))
