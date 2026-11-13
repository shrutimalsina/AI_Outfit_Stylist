from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np
from PIL import Image

from backend.app.ml.encoder import normalize
from pipeline.extract_embeddings import extract
from pipeline.prepare_dataset import read_json, sha256, write_json


class EmbeddingTest(unittest.TestCase):
    def test_normalization(self):
        matrix = np.ones((2, 512))
        result = normalize(matrix)
        self.assertEqual(result.dtype, np.float32)
        np.testing.assert_allclose(np.linalg.norm(result, axis=1), [1, 1])
        for invalid in (np.zeros((1, 512)), np.ones((1, 511)), matrix * np.nan):
            with self.assertRaises(ValueError):
                normalize(invalid)

    def test_resumes_and_publishes_in_manifest_order(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            image_path = root / "item.jpg"
            with Image.new("RGB", (64, 64)) as image:
                image.save(image_path)
            manifest = root / "manifest.json"
            write_json(manifest, {"items": [
                {"id": item_id, "category": category, "image": image_path.name,
                 "image_sha256": sha256(image_path)}
                for item_id, category in [("2", "top"), ("1", "bottom"), ("3", "unknown")]
            ]})
            output = root / "output"
            calls = []

            def interrupted(images):
                calls.append(len(images))
                if len(calls) == 2:
                    raise RuntimeError("interrupted")
                return np.eye(1, 512)

            with self.assertRaisesRegex(RuntimeError, "interrupted"):
                extract(manifest, root, output, lambda: interrupted, batch_size=1)
            self.assertFalse(any(path.name[0] != "." for path in output.iterdir()))

            def resume(images):
                self.assertEqual(len(images), 1)
                return np.roll(np.eye(1, 512), 1, axis=1)

            snapshot = extract(manifest, root, output, lambda: resume)
            self.assertEqual([item["id"] for item in read_json(snapshot / "items.json")], ["2", "1"])
            np.testing.assert_array_equal(np.load(snapshot / "embeddings.npy"), np.eye(2, 512))
            self.assertEqual(read_json(snapshot / "metadata.json")["matrix_sha256"],
                             sha256(snapshot / "embeddings.npy"))
            self.assertEqual(extract(manifest, root, output, lambda: self.fail("loaded model")),
                             snapshot)
