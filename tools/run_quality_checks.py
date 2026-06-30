#!/usr/bin/env python3
"""Run the full Parket36 quality gate used by CI and Pages deploy."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    ("Validate shared settings", ["tools/site_settings.py", "--check"]),
    ("Validate domain settings", ["tools/check_domain_settings.py"]),
    ("Validate workflow configuration", ["tools/check_workflows.py"]),
    ("Validate quality runner", ["tools/check_quality_runner.py"]),
    ("Validate operational docs", ["tools/check_docs.py"]),
    ("Validate sitemap helper", ["tools/check_sitemap_helper.py"]),
    ("Run static audit", ["tools/check_site.py"]),
    ("Run extra guardrails", ["tools/check_guardrails.py"]),
    ("Validate conversion paths", ["tools/check_conversion_paths.py"]),
    ("Validate lead paths", ["tools/check_lead_paths.py"]),
    ("Build public directory", ["tools/build_pages.py"]),
]


def main() -> int:
    for title, args in CHECKS:
        print(f"\n==> {title}", flush=True)
        completed = subprocess.run([sys.executable, *args], cwd=ROOT, check=False)
        if completed.returncode != 0:
            print(f"\nQuality check failed: {title}", file=sys.stderr)
            return completed.returncode

    print("\nAll quality checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
