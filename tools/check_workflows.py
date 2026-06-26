#!/usr/bin/env python3
"""Validate GitHub Actions workflow configuration."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE_QUALITY_PATH = ROOT / ".github" / "workflows" / "site-quality.yml"
PAGES_PATH = ROOT / ".github" / "workflows" / "pages.yml"
QUALITY_RUNNER = "python tools/run_quality_checks.py"
PYTHON_VERSION = 'python-version: "3.12"'

EXPECTED_MARKERS = {
    SITE_QUALITY_PATH: [
        "uses: actions/checkout@v4",
        "uses: actions/setup-python@v5",
        PYTHON_VERSION,
        f"run: {QUALITY_RUNNER}",
    ],
    PAGES_PATH: [
        "uses: actions/checkout@v4",
        "uses: actions/setup-python@v5",
        PYTHON_VERSION,
        f"run: {QUALITY_RUNNER}",
        "uses: actions/configure-pages@v5",
        "uses: actions/upload-pages-artifact@v4",
        "uses: actions/deploy-pages@v4",
        'path: "_site"',
    ],
}

FORBIDDEN_MARKERS = [
    "uses: actions/checkout@v6",
]


def main() -> int:
    findings: list[str] = []

    for path, expected_markers in EXPECTED_MARKERS.items():
        if not path.exists():
            findings.append(f"{path.relative_to(ROOT)} is missing")
            continue

        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)

        for marker in expected_markers:
            if marker not in text:
                findings.append(f"{rel} must contain {marker}")

        for marker in FORBIDDEN_MARKERS:
            if marker in text:
                findings.append(f"{rel} must not contain {marker}")

    if findings:
        print("Workflow findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Workflow check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
