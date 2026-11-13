"""Generate an explicitly synthetic catalog for local integration checks."""

from pathlib import Path
import argparse

import numpy as np
from PIL import Image, ImageDraw

from pipeline.extract_embeddings import extract
from pipeline.prepare_dataset import sha256, write_json


def build(root):
    root.mkdir(parents=True, exist_ok=True)
    items = []
    categories = ["top", "bottom", "outerwear", "footwear"]
    for index, category in enumerate(categories):
        item_id = str(index + 1)
        path = root / f"{item_id}.png"
        with Image.new("RGB", (128, 128), "#e8dcca") as image:
            ImageDraw.Draw(image).rectangle((24, 24, 104, 104), fill=["#364e54", "#556e5e", "#83604e", "#776888"][index])
            image.save(path)
        items.append({"id": item_id, "category": category, "image": path.name,
                      "image_sha256": sha256(path), "title": f"Synthetic {category}"})
    manifest = root / "manifest.json"
    write_json(manifest, {
        "dataset": "synthetic-integration-fixture", "revision": "fixture-v1",
        "seed": 42, "split_policy": "fixture", "items": items,
        "outfits": [{"id": "fixture", "split": "valid", "item_ids": ["1", "2", "3", "4"]}],
    })
    snapshot = extract(manifest, root, root / "snapshots",
                       lambda: lambda images: np.ones((len(images), 512), dtype=np.float32))
    write_json(root / "fixture.json", {"snapshot": str(snapshot.resolve())})
    return snapshot


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, nargs="?", default=Path("data/processed/fixture"))
    print(build(parser.parse_args().root))
