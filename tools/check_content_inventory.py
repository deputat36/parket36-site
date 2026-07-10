#!/usr/bin/env python3
"""Fail CI when the committed content inventory is stale."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import sys

from build_content_inventory import write_inventory

ROOT = Path(__file__).resolve().parents[1]
COMMITTED_MARKDOWN = ROOT / "docs" / "content-inventory.md"


def main() -> int:
    if not COMMITTED_MARKDOWN.is_file():
        print("Content inventory is missing: docs/content-inventory.md")
        return 1

    with TemporaryDirectory(prefix="parket-content-inventory-") as temporary:
        _, generated_markdown, findings = write_inventory(Path(temporary))
        if findings:
            print("Content inventory generation findings:")
            for finding in findings:
                print(f"  - {finding}")
            return 1

        expected = generated_markdown.read_text(encoding="utf-8")

    actual = COMMITTED_MARKDOWN.read_text(encoding="utf-8")
    if actual != expected:
        print("docs/content-inventory.md is stale")
        print(
            "Regenerate it with: "
            "python tools/build_content_inventory.py --output-dir reports/content-inventory"
        )
        print("Then copy reports/content-inventory/content-inventory.md to docs/content-inventory.md")
        return 1

    print("Content inventory check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
