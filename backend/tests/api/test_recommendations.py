from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import numpy as np
from PIL import Image

from backend.app.main import MAX_BYTES, create_app
from backend.app.recommendations.engine import Catalog
from scripts.create_fixture import build


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict("os.environ", {"DATABASE_URL": ""}))
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.catalog = Catalog(build(self.root))
        self.client = TestClient(create_app(
            self.catalog, lambda: lambda images: np.ones((len(images), 512)), self.root,
        ))
        self.addCleanup(self.client.close)

    def upload(self, payload=None, category="top", client=None):
        if payload is None:
            output = BytesIO()
            with Image.new("RGB", (64, 64)) as image:
                image.save(output, format="PNG")
            payload = output.getvalue()
        return (client or self.client).post("/api/v1/recommendations",
            data={"category": category}, files={"image": ("query.png", payload, "image/png")})

    def test_upload_and_images(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        matches = response.json()["recommendations"]
        self.assertEqual([item["category"] for item in matches], ["bottom", "outerwear", "footwear"])
        self.assertEqual(self.client.get(matches[0]["image_url"]).status_code, 200)

    def test_bad_uploads(self):
        for response, status, code in (
            (self.upload(b"broken"), 422, "invalid_image"),
            (self.upload(b"0" * (MAX_BYTES + 1)), 413, "file_too_large"),
            (self.upload(category="unknown"), 422, "invalid_category"),
        ):
            self.assertEqual(response.status_code, status)
            self.assertEqual(response.json()["error"]["code"], code)

    def test_no_candidates(self):
        self.catalog.category_rows["bottom"] = np.array([], dtype=np.intp)
        self.catalog.category_rows["outerwear"] = np.array([], dtype=np.intp)
        self.catalog.category_rows["footwear"] = np.array([], dtype=np.intp)
        self.assertEqual(self.upload().json()["error"]["code"], "no_candidates")

    def test_item_lookup_and_unavailable_model(self):
        self.assertEqual(self.client.get("/api/v1/items/missing").status_code, 404)
        response = self.client.post("/api/v1/recommendations/by-item", json={"item_id": "1", "top_k": 2})
        self.assertEqual(len(response.json()["recommendations"]), 2)

        def broken():
            raise OSError("fixture")
        with TestClient(create_app(self.catalog, broken, self.root)) as client:
            self.assertEqual(self.upload(client=client).json()["error"]["code"], "model_unavailable")
