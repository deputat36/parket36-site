#!/usr/bin/env python3
"""Fail CI when the committed shared-shell coverage report is stale."""

from __future__ import annotations

import difflib
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

from build_shared_shell_coverage import self_test, write_report

ROOT = Path(__file__).resolve().parents[1]
COMMITTED_CSV = ROOT / "docs" / "shared-shell-coverage.csv"
COMMITTED_MARKDOWN = ROOT / "docs" / "shared-shell-coverage.md"


def print_diff(actual: str, expected: str, actual_name: str, expected_name: str) -> None:
    for line in difflib.unified_diff(
        actual.splitlines(),
        expected.splitlines(),
        fromfile=actual_name,
        tofile=expected_name,
        lineterm="",
    ):
        print(line)


def main() -> int:
    findings = self_test()
    if findings:
        print("Shared shell coverage self-test findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    missing = [
        path.relative_to(ROOT).as_posix()
        for path in (COMMITTED_CSV, COMMITTED_MARKDOWN)
        if not path.is_file()
    ]
    if missing:
        print("Shared shell coverage report is missing:")
        for relative in missing:
            print(f"  - {relative}")
        return 1

    with TemporaryDirectory(prefix="parket-shared-shell-coverage-") as temporary:
        generated_csv, generated_markdown, generation_findings = write_report(Path(temporary))
        if generation_findings:
            print("Shared shell coverage generation findings:")
            for finding in generation_findings:
                print(f"  - {finding}")
            return 1
        expected_csv = generated_csv.read_text(encoding="utf-8")
        expected_markdown = generated_markdown.read_text(encoding="utf-8")

    actual_csv = COMMITTED_CSV.read_text(encoding="utf-8")
    actual_markdown = COMMITTED_MARKDOWN.read_text(encoding="utf-8")
    stale = False

    if actual_markdown != expected_markdown:
        stale = True
        print("docs/shared-shell-coverage.md is stale")
        print_diff(
            actual_markdown,
            expected_markdown,
            "docs/shared-shell-coverage.md",
            "generated/shared-shell-coverage.md",
        )

    if actual_csv != expected_csv:
        stale = True
        print("docs/shared-shell-coverage.csv is stale")
        print_diff(
            actual_csv,
            expected_csv,
            "docs/shared-shell-coverage.csv",
            "generated/shared-shell-coverage.csv",
        )

    if stale:
        print(
            "Regenerate with: python tools/build_shared_shell_coverage.py "
            "--output-dir reports/shared-shell-coverage"
        )
        print("Then copy both generated files to docs/.")
        return 1

    print("Shared shell coverage check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
