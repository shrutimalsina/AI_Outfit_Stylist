from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from backend.app.ml.encoder import MODEL_ID, MODEL_REVISION
from backend.app.recommendations.engine import Catalog, NoCandidatesError
from pipeline.extract_embeddings import save_matrix
from pipeline.prepare_dataset import sha256, write_json


class RankingTest(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        items = [
            {"id": item_id, "category": category}
            for item_id, category in (
                ("query", "top"), ("z", "bottom"), ("b", "bottom"),
                ("a", "bottom"), ("shoe", "footwear"),
            )
        ]
        matrix = np.eye(512, dtype=np.float32)[[0, 0, 0, 1, 1]]
        save_matrix(self.root / "embeddings.npy", matrix)
        write_json(self.root / "items.json", items)
        self.metadata = {
            "snapshot_id": self.root.name, "count": len(items), "dimension": 512,
            "model": MODEL_ID, "revision": MODEL_REVISION,
            "matrix_sha256": sha256(self.root / "embeddings.npy"),
            "manifest_sha256": sha256(self.root / "items.json"),
        }
        write_json(self.root / "metadata.json", self.metadata)
        self.catalog = Catalog(self.root)

    def test_cosine_slot_order_ties_and_warning(self):
        matches, warnings = self.catalog.recommend_by_item("query")
        self.assertEqual([match.item_id for match in matches], ["b", "shoe"])
        self.assertEqual([match.similarity for match in matches], [1.0, 0.0])
        self.assertEqual([match.position for match in matches], [1, 2])
        self.assertEqual(warnings, ["No eligible candidates for outerwear"])

    def test_query_exclusion_and_top_k(self):
        matches, warnings = self.catalog.recommend(
            self.catalog.matrix[0], "top", query_id="b", top_k=1,
        )
        self.assertEqual([match.item_id for match in matches], ["z"])
        self.assertEqual(warnings, [])
        with self.assertRaises(ValueError):
            self.catalog.recommend_by_item("query", top_k=0)

    def test_random_reuses_policy_and_exclusions(self):
        def select():
            return self.catalog.random("top", np.random.default_rng(42), query_id="b")
        matches, warnings = select()
        self.assertEqual(select(), (matches, warnings))
        self.assertIn(matches[0].item_id, {"z", "a"})
        self.assertEqual(matches[1].item_id, "shoe")
        self.assertEqual(warnings, ["No eligible candidates for outerwear"])
        with self.assertRaises(NoCandidatesError):
            self.catalog.random("dress", np.random.default_rng(42), query_id="shoe")

    def test_rejects_corrupted_artifacts(self):
        with (self.root / "items.json").open("a") as stream:
            stream.write(" ")
        with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
            Catalog(self.root)

    def test_rejects_invalid_matrix_even_with_correct_checksum(self):
        path = self.root / "embeddings.npy"
        save_matrix(path, np.zeros((5, 512), dtype=np.float32))
        self.metadata["matrix_sha256"] = sha256(path)
        write_json(self.root / "metadata.json", self.metadata)
        with self.assertRaisesRegex(ValueError, "finite and normalized"):
            Catalog(self.root)
