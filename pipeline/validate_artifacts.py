"""Validate a published snapshot without loading CLIP."""

import argparse
from pathlib import Path

from scripts.release_preflight import check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "snapshot", "images"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--allow-fixture", action="store_true")
    args = parser.parse_args()
    count = check(args.manifest, args.snapshot, args.images, allow_fixture=args.allow_fixture)
    print(f"Validated {count} catalog items")


if __name__ == "__main__":
    main()
