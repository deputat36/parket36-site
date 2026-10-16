#!/usr/bin/env python3
"""Rebuild web derivatives from the six recovered original illustrative images."""

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "oak-parquet": "recovered-01.png",
    "worn-parquet": "recovered-02.png",
    "finish-application": "recovered-03.png",
    "parquet-laying": "recovered-04.png",
    "local-repair": "recovered-05.png",
    "floor-sanding": "recovered-06.png",
}


def main() -> None:
    output = ROOT / "img" / "editorial"
    output.mkdir(parents=True, exist_ok=True)
    for name, source in SOURCES.items():
        with Image.open(ROOT / "design" / "source-images" / source) as image:
            for width in (480, 960, 1440):
                height = round(image.height * width / image.width)
                derivative = image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
                derivative.save(output / f"{name}-{width}.webp", "WEBP", quality=79, method=6)
    print("Prepared 18 responsive WebP derivatives; original image content is unchanged")


if __name__ == "__main__":
    main()
