import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from pipeline.prepare_dataset import prepare, write_json


class DatasetPreparationTest(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "images").mkdir()
        for item_id in ("1", "2", "3", "4", "6", "7"):
            with Image.new("RGB", (64, 64)) as image:
                image.save(self.root / "images" / f"{item_id}.jpg")
        (self.root / "images/6.jpg").write_bytes(b"broken")
        metadata = {str(i): {"semantic_category": "tops"} for i in range(1, 7)}
        metadata["2"]["semantic_category"] = "unmapped"
        write_json(self.root / "polyvore_item_metadata.json", metadata)
        self.split("train", ("A", [1, 2]), ("B", [1, 2]), ("C", [1, 5, 6, 7]))
        self.split("valid", ("D", [3, 4]))
        self.split("test")

    def split(self, name, *outfits):
        write_json(self.root / "disjoint" / f"{name}.json", [
            {"set_id": outfit, "items": [{"item_id": str(i)} for i in ids]}
            for outfit, ids in outfits
        ])

    def test_complete_outfits_and_deduplication(self):
        manifest = prepare(self.root, "synthetic-test")
        self.assertEqual(manifest, prepare(self.root, "synthetic-test"))
        self.assertEqual(manifest["selected_counts"], {"train": 2, "valid": 1})
        self.assertEqual(manifest["exclusion_counts"], {
            "corrupt_image": 1, "missing_image": 1, "missing_metadata": 1,
        })
        self.assertEqual([item["id"] for item in manifest["items"]], ["1", "2", "3", "4"])
        self.assertEqual(manifest["items"][1]["category"], "unknown")

    def test_enforces_sample_limit(self):
        manifest = prepare(self.root, "synthetic-test", limits={"train": 1})
        self.assertEqual(len(manifest["outfits"]), 1)
        self.assertEqual(manifest["seed"], 42)

    def test_rejects_split_leakage(self):
        self.split("test", ("E", [1, 4]))
        with self.assertRaisesRegex(ValueError, "crosses official disjoint splits"):
            prepare(self.root, "synthetic-test")

    def test_manifest_output(self):
        target = self.root / "processed" / "manifest.json"
        manifest = prepare(self.root, "synthetic-test")
        write_json(target, manifest)
        self.assertEqual(json.loads(target.read_text()), manifest)
        self.assertEqual(list(target.parent.iterdir()), [target])
