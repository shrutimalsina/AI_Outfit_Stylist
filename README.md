# AI Outfit Stylist

Junior Seminar research question: Can category-aware retrieval using pretrained CLIP image embeddings recover hidden items from curated outfits more often than a category-matched random baseline?

This repository currently contains dataset preparation and CLIP extraction. See [architecture](ARCHITECTURE.md) and the [project journal](PROJECT_JOURNAL.md) for implementation status.

## Reproduce the checkpoint

From the repository root:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-checkpoint.txt
.venv/bin/python -m unittest discover -s backend/tests/unit -v
```

Use the [authors' Polyvore Outfits release](https://huggingface.co/datasets/mvasil/polyvore-outfits). The authors specify [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Cite Vasileva et al., [Learning Type-Aware Embeddings for Fashion Compatibility](https://arxiv.org/abs/1803.09196), ECCV 2018. This pipeline changes the release by sampling complete outfits, validating images and mapping category labels.

Place the unpacked release at `data/raw/polyvore_outfits` with `polyvore_item_metadata.json`, `disjoint/{train,valid,test}.json`, and `images/<item_id>.jpg`. Set `POLYVORE_REVISION` to the actual source commit or archive checksum.

```sh
.venv/bin/python -m pipeline.prepare_dataset data/raw/polyvore_outfits \
  data/processed/manifest.json --revision "${POLYVORE_REVISION:?Set the source revision}"
```

Seed 42 samples up to 3,000 training, 500 validation and 500 test outfits from the official item-disjoint split. The manifest records source hashes, selected items and all validation rejections encountered during sampling. An outfit with an invalid item is excluded as a unit. Valid images with unmapped categories retain the label `unknown` so the recommendation phase can exclude them from retrieval.

## Extract CLIP embeddings

Install the pinned ML checkpoint requirements, then run:

```sh
.venv/bin/python -m pip install -r backend/requirements-ml-checkpoint.txt
HF_HOME="$PWD/data/raw/hf-cache" .venv/bin/python -m pipeline.extract_embeddings \
  data/processed/manifest.json data/raw/polyvore_outfits data/embeddings
```

CPU is the default. Each completed row is cached so the same command can resume an interrupted run. A published snapshot contains the float32 NumPy matrix, the ordered item manifest, and checksums. Unknown categories are excluded from the snapshot.

## Rank catalog items

Pass a published snapshot directory and a source item ID:

```sh
.venv/bin/python - "$SNAPSHOT_DIR" "$ITEM_ID" <<'PY'
from pathlib import Path
import sys

from backend.app.recommendations.engine import Catalog

catalog = Catalog(Path(sys.argv[1]))
matches, warnings = catalog.recommend_by_item(sys.argv[2], top_k=3)
for match in matches:
    print(match.position, match.category, match.item_id, match.similarity)
for warning in warnings:
    print(warning)
PY
```

The engine selects one item per category in policy order and breaks equal cosine scores by lexicographic item ID. Scores measure visual similarity. Empty slots produce warnings, and later eligible slots can fill the result up to the requested limit.

## Evaluate hidden-item recovery

Run validation during development. Use `--split test` for final reporting after the policy is frozen.

```sh
.venv/bin/python -m pipeline.run_evaluation data/processed/manifest.json \
  "$SNAPSHOT_DIR" data/reports/validation.json --split valid
```

The report includes per-case outcomes, exclusions, Recall@1, Recall@3, MRR@3, and a 100-seed category-matched random comparison. See [the evaluation protocol](docs/evaluation-protocol.md) for interpretation.

## Run the notebooks

```sh
.venv/bin/python -m pip install -r backend/requirements-app.txt
.venv/bin/python -m scripts.create_fixture
PATH="$PWD/.venv/bin:$PATH" .venv/bin/jupyter lab notebooks
```

Open the four notebooks in order. They default to an explicitly synthetic fixture. Set `STYLIST_MANIFEST`, `STYLIST_IMAGE_ROOT`, and `STYLIST_SNAPSHOT` to use real data. Set `STYLIST_SPLIT=test` only for the final evaluation.

## Run the application locally

Set `DATABASE_URL` to a reachable PostgreSQL 17 database. Set `STYLIST_IMAGE_ROOT` to the image directory, and set `SNAPSHOT_DIR` to the published filesystem artifact from extraction.

```sh
.venv/bin/alembic -c backend/alembic.ini upgrade head
.venv/bin/python -m pipeline.publish_catalog data/processed/manifest.json "$SNAPSHOT_DIR"
HF_HOME="$PWD/data/raw/hf-cache" .venv/bin/uvicorn backend.app.main:app --host 127.0.0.1
```

In a second terminal run `cd frontend && npm ci && npm run dev` and open the address printed by Vite. API documentation is at `http://127.0.0.1:8000/docs`. Restart the backend after publishing a different snapshot so it loads the new catalog.

For a synthetic demonstration, generate the fixture above, publish its manifest and snapshot in place of the real ones, and set `STYLIST_IMAGE_ROOT=data/processed/fixture`.

## Tests and containers

Run `make test` and `make lint`. To start the Compose services, copy `.env.example` to `.env`, choose a local password, and run `docker compose up --build -d`. Publish the snapshot using paths under `/app/data` with `docker compose exec backend python -m pipeline.publish_catalog /app/data/processed/manifest.json /app/data/embeddings/<snapshot-id>`, then run `docker compose restart backend` and visit `http://localhost:5173`.

The local Compose stack binds the UI to loopback. For public deployment configure HTTPS and secret management, preserve the database and catalog volume, and route requests through a reverse proxy with upload and rate limits. Back up PostgreSQL with `docker compose exec -T database pg_dump -U stylist -d stylist > stylist.sql` and back up the catalog directory separately.
