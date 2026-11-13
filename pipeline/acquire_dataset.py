"""Fetch the pinned Polyvore release with your authorized Hugging Face session."""

import argparse
from pathlib import Path

from huggingface_hub import snapshot_download
from huggingface_hub.errors import GatedRepoError

DATASET = "mvasil/polyvore-outfits"
REVISION = "22cc0c748c293a598e1df561a76abe96273cb76a"
FILES = [
    "polyvore_item_metadata.json", "categories.csv",
    "disjoint/train.json", "disjoint/valid.json", "disjoint/test.json",
    "data/disjoint/train.parquet", "data/disjoint/validation.parquet",
    "data/disjoint/test.parquet",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/raw/polyvore_outfits"))
    args = parser.parse_args()
    try:
        print(snapshot_download(
            repo_id=DATASET, repo_type="dataset", revision=REVISION,
            allow_patterns=FILES, local_dir=args.output,
        ))
    except GatedRepoError:
        parser.exit(1, "Request access on the authors' dataset page, then sign in with hf auth login.\n")


if __name__ == "__main__":
    main()
