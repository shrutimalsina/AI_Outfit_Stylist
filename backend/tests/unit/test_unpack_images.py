from io import BytesIO

from PIL import Image
import pyarrow as pa
import pyarrow.parquet as parquet
import pytest

from pipeline.unpack_images import unpack


def test_unpack_embedded_images_and_resume(tmp_path):
    buffer = BytesIO()
    with Image.new("RGBA", (64, 64)) as image:
        image.save(buffer, "PNG")
    source = tmp_path / "fixture.parquet"
    parquet.write_table(pa.table({
        "id": [1, 1, 2, 3],
        "photo": [{"bytes": payload} for payload in [buffer.getvalue(), buffer.getvalue(), b"broken", None]],
    }), source)
    output = tmp_path / "images"
    assert unpack([source], output, "id", "photo") == {
        "written": 1, "existing": 1, "invalid_image": 1, "missing_bytes": 1,
    }
    with Image.open(output / "1.jpg") as image:
        assert (image.format, image.mode, image.size) == ("JPEG", "RGB", (64, 64))
    assert unpack([source], output, "id", "photo")["existing"] == 2
    with pytest.raises(ValueError, match="missing columns"):
        unpack([source], output, "wrong", "photo")
