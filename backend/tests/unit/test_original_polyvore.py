from PIL import Image

from pipeline.prepare_dataset import write_json
from pipeline.prepare_original_polyvore import prepare


def test_original_split_join_preserves_partial_groups(tmp_path):
    image_root = tmp_path / "images"
    metadata = tmp_path / "metadata"
    for index, category in ((1, "top"), (2, "pants")):
        folder = image_root / "Re-PolyVore" / category
        folder.mkdir(parents=True)
        with Image.new("RGB", (64, 64)) as image:
            image.save(folder / f"123_{index}.jpg")
    write_json(metadata / "test_no_dup.json", [
        {"set_id": "123", "items": [{"index": i} for i in (1, 2, 3)]}
    ])
    manifest, audit = prepare(metadata, image_root, limits={"test": 1})
    assert manifest["outfits"] == [
        {"id": "123", "split": "test", "source_item_count": 3, "item_ids": ["123_1", "123_2"]}
    ]
    assert [item["category"] for item in manifest["items"]] == ["top", "bottom"]
    assert audit["splits"]["test"]["filename_matches"] == 2
    assert audit["item_exceptions"] == [{"split": "test", "item_id": "123_3", "reason": "missing"}]
