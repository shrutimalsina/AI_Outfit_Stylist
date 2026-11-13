"""Validate a release catalog, source manifest, and offline model cache."""

import argparse
from pathlib import Path

from PIL import Image

from backend.app.ml.encoder import ClipEncoder
from backend.app.recommendations.engine import Catalog
from pipeline.prepare_dataset import read_json, sha256


def check(manifest_path, snapshot, image_root, *, allow_fixture=False):
    catalog = Catalog(snapshot)
    if sha256(manifest_path) != catalog.metadata["source_sha256"]:
        raise ValueError("Source manifest does not match the catalog snapshot")
    source = read_json(manifest_path)
    if source["dataset"] != "mvasil/polyvore-outfits" and not allow_fixture:
        raise ValueError("Expected a Polyvore release. Use --allow-fixture only for a demo.")
    image_root = image_root.resolve()
    for item in catalog.items:
        image = (image_root / item["image"]).resolve()
        if not image.is_relative_to(image_root) or sha256(image) != item["image_sha256"]:
            raise ValueError(f"Image location or checksum mismatch for {item['id']}")
    return len(catalog.items)


def main():
    import os

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("image_root", type=Path)
    parser.add_argument("--allow-fixture", action="store_true")
    args = parser.parse_args()
    count = check(args.manifest, args.snapshot, args.image_root, allow_fixture=args.allow_fixture)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
    with Image.new("RGB", (64, 64)) as probe:
        ClipEncoder()([probe])
    print(f"Validated {count} catalog items and ran offline CLIP inference")


if __name__ == "__main__":
    main()
