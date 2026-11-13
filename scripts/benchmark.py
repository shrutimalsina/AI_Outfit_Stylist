"""Benchmark a catalog and one query image with the pinned CLIP model."""

import argparse
from importlib.metadata import version
from pathlib import Path
import platform
from time import perf_counter

import httpx
import numpy as np
from PIL import Image

from backend.app.ml.encoder import ClipEncoder
from backend.app.recommendations.engine import Catalog
from pipeline.prepare_dataset import sha256, write_json


def measure(operation, samples):
    operation()
    elapsed = []
    for _ in range(samples):
        start = perf_counter()
        operation()
        elapsed.append(perf_counter() - start)
    return {
        "samples": samples,
        "median_seconds": float(np.median(elapsed)),
        "p95_seconds": float(np.percentile(elapsed, 95)),
    }


def benchmark(args):
    catalog = Catalog(args.snapshot)
    with Image.open(args.image) as image:
        rgb = image.convert("RGB")
    with rgb:
        started = perf_counter()
        encode = ClipEncoder(args.device)
        query = encode([rgb])[0]
        cold_seconds = perf_counter() - started
        inference = measure(lambda: encode([rgb]), args.samples)
        batch = [rgb] * args.batch_size
        extraction = measure(lambda: encode(batch), args.samples)
    ranking = measure(lambda: catalog.recommend(query, args.category), args.samples)
    report = {
        "snapshot": catalog.metadata,
        "catalog_rows": len(catalog.items),
        "catalog_matrix_bytes": catalog.matrix.nbytes,
        "query_sha256": sha256(args.image),
        "category": args.category,
        "device": args.device,
        "hardware": args.hardware,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "packages": {name: version(name) for name in ("numpy", "torch", "transformers", "httpx")},
        "cold_model_and_first_inference_seconds": cold_seconds,
        "warmed_single_image_inference": inference,
        "warmed_ranking": ranking,
        "warmed_batch_inference": {
            **extraction,
            "images_per_batch": args.batch_size,
            "images_per_second_at_median": args.batch_size / extraction["median_seconds"],
        },
    }
    if args.api:
        payload = args.image.read_bytes()
        with httpx.Client(base_url=args.api, timeout=120) as client:
            response = client.get("/api/v1/catalog")
            response.raise_for_status()
            if response.json()["snapshot_id"] != catalog.metadata["snapshot_id"]:
                raise ValueError("API and local benchmark are using different snapshots")

            def upload():
                response = client.post("/api/v1/recommendations", data={"category": args.category},
                                       files={"image": (args.image.name, payload)})
                response.raise_for_status()

            report["warmed_http_upload"] = measure(upload, args.samples)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("image", type=Path)
    parser.add_argument("category")
    parser.add_argument("output", type=Path)
    parser.add_argument("--hardware", required=True, help="Reference hardware description")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--api", help="Optional API or proxy base URL")
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    if args.samples < 1 or args.batch_size < 1:
        parser.error("Sample count and batch size must be positive")
    write_json(args.output, benchmark(args))


if __name__ == "__main__":
    main()
