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
