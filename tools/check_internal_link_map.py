#!/usr/bin/env python3
"""Fail CI when the committed internal-link map is stale."""

from __future__ import annotations

import difflib
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

from build_internal_link_map import write_report

ROOT = Path(__file__).resolve().parents[1]
COMMITTED_MARKDOWN = ROOT / "docs" / "internal-link-map.md"


def main() -> int:
    if not COMMITTED_MARKDOWN.is_file():
        print("Internal link map is missing: docs/internal-link-map.md")
        return 1

    with TemporaryDirectory(prefix="parket-internal-links-") as temporary:
        _, _, generated_markdown, findings = write_report(Path(temporary))
        if findings:
            print("Internal link map generation findings:")
            for finding in findings:
                print(f"  - {finding}")
            return 1
        expected = generated_markdown.read_text(encoding="utf-8")

    actual = COMMITTED_MARKDOWN.read_text(encoding="utf-8")
    if actual != expected:
        print("docs/internal-link-map.md is stale")
        print(
            "Regenerate it with: "
            "python tools/build_internal_link_map.py --output-dir reports/internal-links"
        )
        print(
            "Then copy reports/internal-links/internal-link-map.md "
            "to docs/internal-link-map.md"
        )
        print("Unified diff:")
        for line in difflib.unified_diff(
            actual.splitlines(),
            expected.splitlines(),
            fromfile="docs/internal-link-map.md",
            tofile="generated/internal-link-map.md",
            lineterm="",
        ):
            print(line)
        return 1

    print("Internal link map check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
