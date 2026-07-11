#!/usr/bin/env python3
"""Self-test public image attribute normalization."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys

from image_attributes import normalize_image_attributes

VALID_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" '
    'viewBox="0 0 1200 800"><rect width="1200" height="800"/></svg>'
)


def valid_case(root: Path) -> list[str]:
    image_dir = root / "img"
    image_dir.mkdir(parents=True)
    (image_dir / "work-test.svg").write_text(VALID_SVG, encoding="utf-8")
    html = root / "index.html"
    html.write_text(
        '<!doctype html><html><body><img data-placeholder-image '
        'src="/img/work-test.svg" alt="Тест" width="960" height="720"></body></html>',
        encoding="utf-8",
    )
    errors: list[str] = []
    count = normalize_image_attributes(root, errors)
    text = html.read_text(encoding="utf-8")
    findings = list(errors)
    if count != 1:
        findings.append(f"expected one processed image, got {count}")
    for marker in (
        'width="1200"',
        'height="800"',
        'decoding="async"',
        'loading="lazy"',
        'alt="Тест"',
    ):
        if marker not in text:
            findings.append(f"normalized HTML is missing {marker}")
    if 'width="960"' in text or 'height="720"' in text:
        findings.append("incorrect source dimensions were not replaced")
    return findings


def invalid_case(root: Path) -> list[str]:
    image_dir = root / "img"
    image_dir.mkdir(parents=True)
    (image_dir / "test.svg").write_text(VALID_SVG, encoding="utf-8")
    (root / "index.html").write_text(
        '<!doctype html><html><body><img src="/img/test.svg"></body></html>',
        encoding="utf-8",
    )
    errors: list[str] = []
    normalize_image_attributes(root, errors)
    if not any("missing alt" in error for error in errors):
        return ["missing alt was not rejected"]
    return []


def main() -> int:
    findings: list[str] = []
    with TemporaryDirectory() as temp:
        findings.extend(valid_case(Path(temp)))
    with TemporaryDirectory() as temp:
        findings.extend(invalid_case(Path(temp)))

    if findings:
        print("Image attribute self-test findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Image attribute self-test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
