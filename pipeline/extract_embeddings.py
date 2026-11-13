"""Extract resumable CLIP embeddings and atomically publish a catalog directory."""

import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

import numpy as np
from PIL import Image

from backend.app.ml.encoder import DIMENSION, MODEL_ID, MODEL_REVISION, ClipEncoder, normalize
from pipeline.prepare_dataset import read_json, sha256, write_json


def save_matrix(path, matrix):
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            np.save(stream, matrix, allow_pickle=False)
            stream.flush()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


def extract(manifest_path, image_root, output_root, encoder_factory=ClipEncoder, batch_size=32):
    if batch_size < 1:
        raise ValueError("Batch size must be positive")
    manifest_hash = sha256(manifest_path)
    items = [item for item in read_json(manifest_path)["items"] if item["category"] != "unknown"]
    ids = [item["id"] for item in items]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("Expected a nonempty catalog with unique item IDs")
    paths = [(image_root / item["image"]).resolve() for item in items]
    for item, path in zip(items, paths, strict=True):
        if not path.is_relative_to(image_root.resolve()) or sha256(path) != item["image_sha256"]:
            raise ValueError(f"Image path or checksum mismatch for {item['id']}")
    key = hashlib.sha256(f"clip-v1:{MODEL_REVISION}:{manifest_hash}".encode()).hexdigest()
    output_root.mkdir(parents=True, exist_ok=True)
    snapshot = output_root / key
    if snapshot.exists():
        return snapshot
    cache = output_root / f".{key}.resume"
    cache.mkdir(exist_ok=True)
    encoder = None
    index = 0
    while index < len(items):
        if (cache / f"{index}.npy").exists():
            index += 1
            continue
        stop = index
        while stop < min(index + batch_size, len(items)) and not (cache / f"{stop}.npy").exists():
            stop += 1
        images = []
        try:
            for path in paths[index:stop]:
                with Image.open(path) as image:
                    images.append(image.convert("RGB"))
            if encoder is None:
                encoder = encoder_factory()
            try:
                batch = normalize(encoder(images))
            except RuntimeError as error:
                if len(images) == 1 or "out of memory" not in str(error).lower():
                    raise
                batch_size = max(1, len(images) // 2)
                continue
            if len(batch) != len(images):
                raise ValueError("Encoder returned a different number of rows than input images")
            for row, vector in enumerate(batch, start=index):
                save_matrix(cache / f"{row}.npy", vector)
            index = stop
        finally:
            for image in images:
                image.close()
    matrix = np.stack([np.load(cache / f"{row}.npy", allow_pickle=False) for row in range(len(items))])
    if matrix.shape != (len(items), DIMENSION) or matrix.dtype != np.float32:
        raise ValueError("Invalid cached embedding matrix shape or dtype")
    if not np.isfinite(matrix).all() or not np.allclose(np.linalg.norm(matrix, axis=1), 1, atol=1e-5):
        raise ValueError("Invalid cached embedding values")
    with TemporaryDirectory(dir=output_root) as staging:
        temporary = Path(staging)
        save_matrix(temporary / "embeddings.npy", matrix)
        write_json(temporary / "items.json", items)
        write_json(temporary / "metadata.json", {
            "snapshot_id": key, "model": MODEL_ID, "revision": MODEL_REVISION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "dimension": DIMENSION, "count": len(ids), "source_sha256": manifest_hash,
            "matrix_sha256": sha256(temporary / "embeddings.npy"),
            "manifest_sha256": sha256(temporary / "items.json"),
        })
        try:
            temporary.rename(snapshot)
        except OSError:
            if not snapshot.is_dir():
                raise
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("image_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()
    print(extract(args.manifest, args.image_root, args.output,
                  lambda: ClipEncoder(args.device), args.batch_size))


if __name__ == "__main__":
    main()
