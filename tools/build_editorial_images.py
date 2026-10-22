#!/usr/bin/env python3
"""Rebuild responsive editorial WebP variants from declared original sources."""
from pathlib import Path
import json
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / "data/editorial-media.json").read_text())
    count = 0
    for key, asset in manifest["assets"].items():
        if not asset.get("build"):
            continue
        source = ROOT / asset["provenance"]["source"]
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            for width in asset["build"]["widths"]:
                height = round(width * asset["height"] / asset["width"])
                resized = ImageOps.fit(image, (width, height), method=Image.Resampling.LANCZOS)
                output = ROOT / f"img/editorial/{key}-{width}.webp"
                resized.save(output, "WEBP", quality=80, method=6)
                with Image.open(output) as check:
                    check.load()
                    if check.size != (width, height):
                        raise ValueError(f"Wrong editorial image dimensions: {output}")
                count += 1
    print(f"Prepared {count} responsive editorial images")


if __name__ == "__main__":
    main()
