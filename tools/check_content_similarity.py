#!/usr/bin/env python3
"""Fail CI when the committed content similarity report is stale."""

from __future__ import annotations

import difflib
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

from build_content_similarity_report import write_report

ROOT = Path(__file__).resolve().parents[1]
COMMITTED_MARKDOWN = ROOT / "docs" / "content-similarity-report.md"


def main() -> int:
    if not COMMITTED_MARKDOWN.is_file():
        print("Content similarity report is missing: docs/content-similarity-report.md")
        return 1

    with TemporaryDirectory(prefix="parket-content-similarity-") as temporary:
        generated_markdown, _, findings = write_report(Path(temporary))
        if findings:
            print("Content similarity generation findings:")
            for finding in findings:
                print(f"  - {finding}")
            return 1
        expected = generated_markdown.read_text(encoding="utf-8")

    actual = COMMITTED_MARKDOWN.read_text(encoding="utf-8")
    if actual != expected:
        print("docs/content-similarity-report.md is stale")
        print(
            "Regenerate it with: "
            "python tools/build_content_similarity_report.py --output-dir reports/content-similarity"
        )
        print(
            "Then copy reports/content-similarity/content-similarity-report.md "
            "to docs/content-similarity-report.md"
        )
        print("Unified diff:")
        for line in difflib.unified_diff(
            actual.splitlines(),
            expected.splitlines(),
            fromfile="docs/content-similarity-report.md",
            tofile="generated/content-similarity-report.md",
            lineterm="",
        ):
            print(line)
        return 1

    print("Content similarity report check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
