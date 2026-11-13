"""Render real-data evaluation and catalog recommendation figures."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image

from backend.app.recommendations.engine import Catalog
from pipeline.prepare_dataset import read_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("report", "snapshot", "images", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = read_json(args.report)
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    baseline = report["random"]
    ax.bar(["CLIP", "Category-matched random"],
           [report["clip"]["recall_at_3"], baseline["recall_at_3_mean"]],
           yerr=[0, baseline["recall_at_3_population_std"]], color=["#28594e", "#978463"])
    ax.set(ylabel="Recall@3", title=f"Hidden-item recovery · {report['split']} split")
    fig.savefig(args.output / "recall-comparison.png", dpi=180)
    plt.close(fig)

    catalog = Catalog(args.snapshot)
    case = next(row for row in report["cases"] if row.get("recommendations"))
    matches, _ = catalog.recommend_by_item(case["query_id"])
    fig, axes = plt.subplots(1, len(matches) + 1, figsize=(10, 3), layout="constrained")
    labels = [(case["query_id"], "Query")] + [
        (match.item_id, f"{match.category}\ncosine {match.similarity:.3f}") for match in matches
    ]
    for ax, (item_id, label) in zip(axes, labels, strict=True):
        item = catalog.items[catalog.rows[item_id]]
        with Image.open(args.images / item["image"]) as image:
            ax.imshow(image.convert("RGB"))
        ax.set_title(label)
        ax.axis("off")
    fig.savefig(args.output / "outfit-recommendations.png", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    main()
