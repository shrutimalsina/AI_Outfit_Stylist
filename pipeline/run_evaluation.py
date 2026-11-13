"""Compare CLIP and category-matched random retrieval on a held-out split."""

import argparse
from collections import Counter, defaultdict
from importlib.metadata import version
from itertools import permutations
from pathlib import Path
import platform
from statistics import mean, pstdev

import numpy as np

from backend.app.evaluation.metrics import hidden_rank, summarize
from backend.app.recommendations.engine import ALGORITHM_VERSION, DEFAULT_POLICY, Catalog
from pipeline.prepare_dataset import read_json, sha256, write_json

BASELINE_SEEDS = tuple(range(100))


def evaluate(catalog, manifest, split):
    if split not in {"valid", "test"}:
        raise ValueError("Evaluation requires the valid or test split")
    generators = [np.random.default_rng(seed) for seed in BASELINE_SEEDS]
    random_hits = [0] * len(generators)
    clip_ranks = []
    category_ranks = defaultdict(list)
    cases = []
    reasons = Counter()
    outfits = [outfit for outfit in manifest["outfits"] if outfit["split"] == split]
    catalog_items = catalog.items
    for outfit in outfits:
        for query_id, hidden_id in permutations(outfit["item_ids"], 2):
            case = {"outfit_id": outfit["id"], "query_id": query_id, "hidden_id": hidden_id}
            cases.append(case)
            query_row = catalog.rows.get(query_id)
            hidden_row = catalog.rows.get(hidden_id)
            if query_row is None:
                reason = "query_missing_from_catalog"
            elif hidden_row is None:
                reason = "hidden_missing_from_catalog"
            else:
                query_category = catalog_items[query_row]["category"]
                hidden_category = catalog_items[hidden_row]["category"]
                reason = None if hidden_category in catalog.policy[query_category] else "ineligible_category"
            if reason:
                case["exclusion"] = reason
                reasons[reason] += 1
                continue
            matches, _ = catalog.recommend_by_item(query_id)
            rank = hidden_rank(matches, hidden_id)
            case.update(hidden_category=hidden_category, clip_rank=rank,
                        recommendations=[match.item_id for match in matches])
            clip_ranks.append(rank)
            category_ranks[hidden_category].append(rank)
            for index, rng in enumerate(generators):
                sampled, _ = catalog.random(query_category, rng, query_id=query_id)
                random_hits[index] += hidden_rank(sampled, hidden_id) is not None

    count = len(clip_ranks)
    baseline = [hits / count for hits in random_hits] if count else []
    metrics = summarize(clip_ranks)
    random_mean = mean(baseline) if baseline else None
    return {
        "split": split,
        "eligible_cases": count,
        "excluded_cases": sum(reasons.values()),
        "exclusion_reasons": dict(reasons),
        "evaluated_outfits": len(outfits),
        "ingestion_exclusions": [
            outfit for outfit in manifest.get("excluded_outfits", []) if outfit["split"] == split
        ],
        "clip": metrics,
        "clip_by_hidden_category": {
            category: {"cases": len(ranks), **summarize(ranks)}
            for category, ranks in category_ranks.items()
        },
        "random": {
            "seeds": list(BASELINE_SEEDS), "recall_at_3_by_seed": baseline,
            "recall_at_3_mean": random_mean,
            "recall_at_3_population_std": pstdev(baseline) if baseline else None,
        },
        "recall_at_3_difference": metrics["recall_at_3"] - random_mean if count else None,
        "cases": cases,
    }


def run(manifest_path, snapshot, policy, split):
    catalog = Catalog(snapshot, policy)
    source_digest = sha256(manifest_path)
    if catalog.metadata.get("source_sha256") != source_digest:
        raise ValueError("Snapshot and evaluation manifest have different provenance")
    manifest = read_json(manifest_path)
    report = evaluate(catalog, manifest, split)
    report["provenance"] = {
        "dataset": manifest["dataset"], "dataset_revision": manifest["revision"],
        "split_policy": manifest["split_policy"], "sampling_seed": manifest["seed"],
        "manifest_sha256": source_digest, "catalog": catalog.metadata,
        "policy_sha256": sha256(policy), "algorithm": ALGORITHM_VERSION,
        "candidate_universe": "All eligible catalog items, including held-out split items",
        "case_enumeration": "All ordered pairs of distinct items within each sampled outfit",
        "top_k": 3, "platform": platform.platform(), "machine": platform.machine(),
        "python": platform.python_version(),
        "dependencies": {name: version(name) for name in ("numpy", "PyYAML")},
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--split", choices=("valid", "test"), required=True)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    args = parser.parse_args()
    write_json(args.output, run(args.manifest, args.snapshot, args.policy, args.split))


if __name__ == "__main__":
    main()
