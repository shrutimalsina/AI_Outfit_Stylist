"""Join original Polyvore split metadata with local Re-PolyVore images."""

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import random
import re

from PIL import Image

from pipeline.prepare_dataset import DEFAULT_LIMITS, read_json, sha256, write_json

CATEGORY_MAP = {
    "top": "top", "pants": "bottom", "skirt": "bottom", "dress": "dress",
    "jumpsuit": "dress", "outwear": "outerwear", "shoes": "footwear",
    **dict.fromkeys(("bag", "bracelet", "brooch", "earrings", "eyewear", "gloves",
                     "hairwear", "hats", "legwear", "necklace", "neckwear", "rings",
                     "watches"), "accessory"),
}


def prepare(metadata, image_root, limits=DEFAULT_LIMITS, seed=42):
    images = defaultdict(list)
    for path in sorted((image_root / "Re-PolyVore").rglob("*")):
        if path.is_file() and path.suffix.lower() == ".jpg":
            if re.fullmatch(r"[0-9]+_[0-9]+", path.stem):
                images[path.stem].append(path)
    if not images:
        raise ValueError("No SetID_ItemIndex JPEGs found")
    checksums = {}
    audits = {}
    exceptions = []
    selected_items = {}
    selected_outfits = []
    seen_outfits = set()
    for split, limit in limits.items():
        path = metadata / f"{split}_no_dup.json"
        checksums[path.name] = sha256(path)
        counts = Counter()
        candidates = []
        complete = 0
        source = read_json(path)
        for outfit in source:
            outfit_id = str(outfit["set_id"])
            if outfit_id in seen_outfits:
                raise ValueError(f"Outfit appears more than once: {outfit_id}")
            seen_outfits.add(outfit_id)
            rows = []
            for item in outfit["items"]:
                item_id = f"{outfit_id}_{item['index']}"
                counts["metadata_items"] += 1
                paths = images.get(item_id, [])
                counts["filename_matches"] += bool(paths)
                reason = None
                if len(paths) != 1:
                    reason = "ambiguous" if paths else "missing"
                else:
                    image_path = paths[0]
                    try:
                        with Image.open(image_path) as image:
                            if image.format != "JPEG":
                                raise ValueError("Expected JPEG")
                            image.load()
                    except (OSError, ValueError, Image.DecompressionBombError):
                        reason = "corrupt"
                if reason:
                    counts[reason] += 1
                    exceptions.append({"split": split, "item_id": item_id, "reason": reason})
                    continue
                category = CATEGORY_MAP.get(image_path.parent.name, "unknown")
                counts["valid_images"] += 1
                rows.append({
                    "id": item_id, "title": item.get("name"), "category": category,
                    "source_category": image_path.parent.name,
                    "source_category_id": item.get("categoryid"),
                    "image": image_path.relative_to(image_root).as_posix(),
                })
            if len(rows) >= 2:
                complete += len(rows) == len(outfit["items"])
                candidates.append((outfit_id, rows, len(outfit["items"])))
            else:
                counts["excluded_outfits_fewer_than_two_images"] += 1
        counts["complete_outfits"] = complete
        counts["partial_outfits_with_two_images"] = len(candidates) - complete
        counts["source_outfits"] = len(source)
        random.Random(f"{seed}:{split}").shuffle(candidates)
        for outfit_id, rows, original_count in candidates[:limit]:
            for row in rows:
                row["image_sha256"] = sha256(image_root / row["image"])
                selected_items[row["id"]] = row
            selected_outfits.append({"id": outfit_id, "split": split,
                                     "source_item_count": original_count,
                                     "item_ids": [row["id"] for row in rows]})
        counts["selected_outfits"] = min(limit, len(candidates))
        counts["match_percent"] = 100 * counts["filename_matches"] / max(1, counts["metadata_items"])
        audits[split] = dict(counts)
    manifest = {
        "dataset": "original-polyvore-re-polyvore-join",
        "revision": "local-split-sha256-and-image-manifest",
        "split_policy": "official-original-outfit-splits", "seed": seed,
        "source_checksums": checksums, "limits": limits,
        "items": [selected_items[key] for key in sorted(selected_items)],
        "outfits": selected_outfits, "compatibility": audits,
    }
    return manifest, {"splits": audits, "item_exceptions": exceptions, "indexed_image_ids": len(images)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metadata", type=Path)
    parser.add_argument("images", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("audit", type=Path)
    args = parser.parse_args()
    manifest, audit = prepare(args.metadata, args.images)
    write_json(args.manifest, manifest)
    write_json(args.audit, audit)
    print(audit["splits"], flush=True)


if __name__ == "__main__":
    main()
