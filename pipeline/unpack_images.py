"""Stream embedded images from local Parquet into the ingestion directory."""

import argparse
from collections import Counter
from io import BytesIO
import json
from pathlib import Path
import re
from tempfile import NamedTemporaryFile

from PIL import Image, ImageOps
import pyarrow.parquet as parquet


def unpack(files, output, id_column, image_column):
    output.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    for source in files:
        archive = parquet.ParquetFile(source)
        missing = {id_column, image_column} - set(archive.schema_arrow.names)
        if missing:
            raise ValueError(f"{source}: missing columns {sorted(missing)}; available: "
                             f"{archive.schema_arrow.names}")
        for batch in archive.iter_batches(batch_size=64, columns=[id_column, image_column]):
            for row in batch.to_pylist():
                item_id = str(row[id_column])
                if not re.fullmatch(r"[0-9]+", item_id):
                    raise ValueError(f"{source}: invalid item ID {item_id!r}")
                target = output / f"{item_id}.jpg"
                if target.exists():
                    counts["existing"] += 1
                    continue
                payload = row[image_column]
                if isinstance(payload, dict):
                    payload = payload.get("bytes")
                if not isinstance(payload, bytes) or not payload:
                    counts["missing_bytes"] += 1
                    continue
                try:
                    with Image.open(BytesIO(payload)) as image:
                        rgb = ImageOps.exif_transpose(image).convert("RGB")
                except (OSError, ValueError, Image.DecompressionBombError):
                    counts["invalid_image"] += 1
                    continue
                with rgb, NamedTemporaryFile(dir=output, delete=False) as stream:
                    temporary = Path(stream.name)
                    try:
                        rgb.save(stream, "JPEG", quality=95)
                        stream.flush()
                        temporary.replace(target)
                    finally:
                        temporary.unlink(missing_ok=True)
                counts["written"] += 1
    return dict(counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/raw/polyvore_outfits/images"))
    parser.add_argument("--id-column", default="item_id")
    parser.add_argument("--image-column", default="image")
    parser.add_argument("--inspect", action="store_true", help="Print schemas without extracting")
    args = parser.parse_args()
    if args.inspect:
        for source in args.files:
            print(source, parquet.ParquetFile(source).schema_arrow, sep="\n")
        return
    print(json.dumps(unpack(args.files, args.output, args.id_column, args.image_column), sort_keys=True))


if __name__ == "__main__":
    main()
