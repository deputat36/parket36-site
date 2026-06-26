#!/usr/bin/env python3
"""Validate operational documentation for CI and deploy workflows."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"
SITE_QUALITY_PATH = ROOT / ".github" / "workflows" / "site-quality.yml"
PAGES_PATH = ROOT / ".github" / "workflows" / "pages.yml"
QUALITY_RUNNER = "python tools/run_quality_checks.py"
OLD_LOCAL_CHECK_BLOCK = "python tools/site_settings.py --check\npython tools/check_site.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    findings: list[str] = []

    readme = read(README_PATH)
    site_quality = read(SITE_QUALITY_PATH)
    pages = read(PAGES_PATH)

    required_readme_markers = [
        QUALITY_RUNNER,
        "tools/run_quality_checks.py",
        "check_domain_settings.py",
        "check_conversion_paths.py",
        "check_lead_paths.py",
    ]
    for marker in required_readme_markers:
        if marker not in readme:
            findings.append(f"README.md must mention {marker}")

    if OLD_LOCAL_CHECK_BLOCK in readme:
        findings.append("README.md still documents the old local multi-command quality check")

    for path, text in ((SITE_QUALITY_PATH, site_quality), (PAGES_PATH, pages)):
        if QUALITY_RUNNER not in text:
            findings.append(f"{path.relative_to(ROOT)} must run {QUALITY_RUNNER}")

    if findings:
        print("Documentation findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Documentation check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
