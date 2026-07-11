#!/usr/bin/env python3
"""Fail CI when sitemap.xml differs from the canonical/date-driven generator."""

from __future__ import annotations

import difflib
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

from build_sitemap import write_sitemap

ROOT = Path(__file__).resolve().parents[1]
COMMITTED_SITEMAP = ROOT / "sitemap.xml"


def main() -> int:
    if not COMMITTED_SITEMAP.is_file():
        print("sitemap.xml is missing")
        return 1

    with TemporaryDirectory(prefix="parket-sitemap-") as temporary:
        generated = Path(temporary) / "sitemap.xml"
        _, findings = write_sitemap(COMMITTED_SITEMAP, generated)
        if findings:
            print("Sitemap generation findings:")
            for finding in findings:
                print(f"  - {finding}")
            return 1
        expected = generated.read_text(encoding="utf-8")

    actual = COMMITTED_SITEMAP.read_text(encoding="utf-8")
    if actual != expected:
        print("sitemap.xml is stale")
        print(
            "Regenerate it with: "
            "python tools/build_sitemap.py --source sitemap.xml --output reports/generated-sitemap.xml"
        )
        print("Then replace sitemap.xml with reports/generated-sitemap.xml")
        print("Unified diff:")
        for line in difflib.unified_diff(
            actual.splitlines(),
            expected.splitlines(),
            fromfile="sitemap.xml",
            tofile="generated/sitemap.xml",
            lineterm="",
        ):
            print(line)
        return 1

    print("Generated sitemap check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
