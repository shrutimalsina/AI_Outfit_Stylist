"""Shared deterministic ranking and category-matched random selection."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml

from backend.app.ml.encoder import DIMENSION, MODEL_ID, MODEL_REVISION, normalize

ALGORITHM_VERSION = "category-cosine-v1"
DEFAULT_POLICY = Path(__file__).resolve().parents[3] / "config/categories.yaml"
CATEGORIES = frozenset(("top", "bottom", "dress", "outerwear", "footwear", "accessory"))


class NoCandidatesError(ValueError):
    """The policy has no eligible candidates for this query."""


@dataclass(frozen=True)
class Match:
    item_id: str
    category: str
    position: int
    similarity: float | None


class Catalog:
    def __init__(self, directory, policy_path=DEFAULT_POLICY):
        self.metadata = json.loads((directory / "metadata.json").read_text())
        for key, expected in (
            ("snapshot_id", directory.name), ("model", MODEL_ID),
            ("revision", MODEL_REVISION), ("dimension", DIMENSION),
        ):
            if self.metadata.get(key) != expected:
                raise ValueError(f"Invalid catalog {key}")
        matrix_path = directory / "embeddings.npy"
        items_path = directory / "items.json"
        for path, key in ((matrix_path, "matrix_sha256"), (items_path, "manifest_sha256")):
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if digest != self.metadata.get(key):
                raise ValueError(f"Checksum mismatch for {path.name}")

        self.items = json.loads(items_path.read_text())
        self.matrix = np.load(matrix_path, allow_pickle=False, mmap_mode="r")
        count = len(self.items)
        if (not count or self.metadata.get("count") != count
                or self.matrix.shape != (count, DIMENSION) or self.matrix.dtype != np.float32):
            raise ValueError("Invalid catalog matrix shape or dtype")
        for start in range(0, count, 4096):
            batch = self.matrix[start:start + 4096]
            if not np.isfinite(batch).all() or not np.allclose(
                np.linalg.norm(batch, axis=1), 1, rtol=0, atol=1e-5,
            ):
                raise ValueError("Catalog vectors must be finite and normalized")

        self.rows = {}
        for row, item in enumerate(self.items):
            item_id = item.get("id")
            if (not isinstance(item_id, str) or not item_id or item_id in self.rows
                    or item.get("category") not in CATEGORIES):
                raise ValueError("Catalog items require unique IDs and supported categories")
            self.rows[item_id] = row
        ordered_ids = sorted(self.rows)
        self.category_rows = {
            category: np.array([
                self.rows[item_id] for item_id in ordered_ids
                if self.items[self.rows[item_id]]["category"] == category
            ], dtype=np.intp)
            for category in CATEGORIES
        }
        self.policy = yaml.safe_load(Path(policy_path).read_text())
        if not isinstance(self.policy, dict) or self.policy.keys() != CATEGORIES:
            raise ValueError("Policy must define all supported categories")
        for category, slots in self.policy.items():
            if (not isinstance(slots, list) or len(slots) != 3
                    or any(slot not in CATEGORIES for slot in slots)
                    or len(set(slots)) != 3 or category in slots):
                raise ValueError(f"Invalid recommendation slots for {category}")

    def recommend(self, embedding, category, *, query_id=None, top_k=3):
        query = normalize(np.asarray(embedding)[None, :])[0]
        return self._select(category, query_id, top_k, query=query)

    def recommend_by_item(self, item_id, *, top_k=3):
        row = self.rows[item_id]
        return self.recommend(
            self.matrix[row], self.items[row]["category"], query_id=item_id, top_k=top_k,
        )

    def alternatives(self, embedding, primary, limit):
        query = normalize(np.asarray(embedding)[None, :])[0]
        ranked = {}
        for match in primary:
            candidates = self.category_rows[match.category]
            candidates = candidates[candidates != self.rows[match.item_id]]
            scores = self.matrix[candidates] @ query
            order = np.argsort(-scores, kind="stable")[:limit]
            ranked[match.category] = [
                Match(self.items[candidates[index]]["id"], match.category, match.position,
                      float(np.clip(scores[index], -1, 1)))
                for index in order
            ]
        return ranked

    def random(self, category, rng, *, query_id=None, top_k=3):
        return self._select(category, query_id, top_k, rng=rng)

    def _select(self, category, query_id, top_k, *, query=None, rng=None):
        if category not in self.policy:
            raise ValueError(f"Unsupported query category: {category}")
        if type(top_k) is not int or not 1 <= top_k <= 3:
            raise ValueError("top_k must be an integer from 1 to 3")
        excluded = self.rows.get(query_id)
        matches = []
        warnings = []
        for slot in self.policy[category]:
            candidates = self.category_rows[slot]
            if excluded is not None and self.items[excluded]["category"] == slot:
                candidates = candidates[candidates != excluded]
            if not candidates.size:
                warnings.append(f"No eligible candidates for {slot}")
                continue
            if query is None:
                row = rng.choice(candidates)
                score = None
            else:
                scores = self.matrix[candidates] @ query
                best = scores.argmax()
                row = candidates[best]
                score = float(np.clip(scores[best], -1, 1))
            matches.append(Match(self.items[row]["id"], slot, len(matches) + 1, score))
            if len(matches) == top_k:
                break
        if not matches:
            raise NoCandidatesError("No eligible candidates")
        return matches, warnings
