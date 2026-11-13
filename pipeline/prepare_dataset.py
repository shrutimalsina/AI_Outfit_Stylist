"""Prepare a deterministic manifest from an unpacked Polyvore Outfits release."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import re
from tempfile import NamedTemporaryFile

from PIL import Image

CATEGORIES = {
    "tops": "top",
    "bottoms": "bottom",
    "all-body": "dress",
    "dresses": "dress",
    "outerwear": "outerwear",
    "shoes": "footwear",
    "accessories": "accessory",
    "bags": "accessory",
    "jewellery": "accessory",
    "jewelry": "accessory",
    "sunglasses": "accessory",
    "hats": "accessory",
}
DEFAULT_LIMITS = {"train": 3000, "valid": 500, "test": 500}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def inspect_item(root, metadata, item_id):
    if not re.fullmatch(r"[0-9]+", item_id):
        raise ValueError(f"Unexpected Polyvore item ID: {item_id!r}")
    if item_id not in metadata:
        return None, "missing_metadata"
    relative = f"images/{item_id}.jpg"
    path = root / relative
    try:
        with Image.open(path) as image:
            if image.format != "JPEG":
                return None, "unexpected_image_format"
            image.load()
    except FileNotFoundError:
        return None, "missing_image"
    except (OSError, ValueError, Image.DecompressionBombError):
        return None, "corrupt_image"

    source_category = metadata[item_id].get("semantic_category") or ""
    return {
        "id": item_id,
        "category": CATEGORIES.get(source_category.lower().strip(), "unknown"),
        "source_category": source_category,
        "title": metadata[item_id].get("title"),
        "image": relative,
        "image_sha256": sha256(path),
    }, None


def prepare(root, revision, limits=None, seed=42):
    limits = DEFAULT_LIMITS if limits is None else limits
    metadata_path = root / "polyvore_item_metadata.json"
    metadata = read_json(metadata_path)
    checksums = {metadata_path.name: sha256(metadata_path)}
    validated = {}
    selected_items = {}
    selected_outfits = []
    excluded_outfits = []
    source_counts = {}
    outfit_splits = {}
    item_splits = {}

    for split, limit in limits.items():
        split_path = root / "disjoint" / f"{split}.json"
        source = sorted(read_json(split_path), key=lambda outfit: str(outfit["set_id"]))
        checksums[f"disjoint/{split}.json"] = sha256(split_path)
        source_counts[split] = len(source)
        for outfit in source:
            outfit_id = str(outfit["set_id"])
            if outfit_id in outfit_splits:
                raise ValueError(f"Duplicate outfit ID: {outfit_id}")
            outfit_splits[outfit_id] = split
            for row in outfit["items"]:
                item_id = str(row["item_id"])
                if item_splits.setdefault(item_id, split) != split:
                    raise ValueError(f"Item {item_id} crosses official disjoint splits")

        random.Random(f"{seed}:{split}").shuffle(source)
        count = 0
        for outfit in source:
            if count >= limit:
                break
            outfit_id = str(outfit["set_id"])
            item_ids = list(dict.fromkeys(str(row["item_id"]) for row in outfit["items"]))
            reasons = []
            if len(item_ids) < 2:
                reasons.append({"reason": "fewer_than_two_unique_items"})
            for item_id in item_ids:
                if item_id not in validated:
                    validated[item_id] = inspect_item(root, metadata, item_id)
                _, reason = validated[item_id]
                if reason:
                    reasons.append({"item_id": item_id, "reason": reason})
            if reasons:
                excluded_outfits.append({"id": outfit_id, "split": split, "reasons": reasons})
                continue
            selected_outfits.append({"id": outfit_id, "split": split, "item_ids": item_ids})
            selected_items.update((item_id, validated[item_id][0]) for item_id in item_ids)
            count += 1

    return {
        "schema_version": 1,
        "dataset": "mvasil/polyvore-outfits",
        "revision": revision,
        "split_policy": "disjoint",
        "seed": seed,
        "limits": limits,
        "source_checksums": checksums,
        "source_counts": source_counts,
        "selected_counts": dict(Counter(outfit["split"] for outfit in selected_outfits)),
        "items": [selected_items[item_id] for item_id in sorted(selected_items)],
        "outfits": sorted(selected_outfits, key=lambda outfit: (outfit["split"], outfit["id"])),
        "excluded_outfits": excluded_outfits,
        "exclusion_counts": dict(Counter(
            reason["reason"] for outfit in excluded_outfits for reason in outfit["reasons"]
        )),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--revision", required=True, help="Source commit or release checksum")
    args = parser.parse_args()
    manifest = prepare(args.root, args.revision)
    write_json(args.output, manifest)
    print(json.dumps({
        "selected_outfits": manifest["selected_counts"],
        "items": len(manifest["items"]),
        "excluded_outfits": len(manifest["excluded_outfits"]),
    }))


if __name__ == "__main__":
    main()
