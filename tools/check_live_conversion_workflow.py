#!/usr/bin/env python3
"""Validate live call and IndexNow monitoring integration."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "live-site-health.yml"
HELPER = ROOT / "tools" / "check_live_conversion.py"

WORKFLOW_MARKERS = (
    "id: live_conversion",
    "python tools/check_live_conversion.py",
    "--report live-health-report.md",
    'LIVE_CONVERSION_ATTEMPTS: ${{ github.event_name == \'workflow_run\' && \'6\' || \'1\' }}',
    '--attempts "$LIVE_CONVERSION_ATTEMPTS"',
    "--retry-delay 10",
    "--timeout 20",
    "steps.live_conversion.outcome == 'failure'",
    "steps.live_conversion.outcome == 'success'",
    "name: live-health-report",
)

HELPER_MARKERS = (
    "Homepage call route",
    "IndexNow key HTTP",
    "IndexNow key content",
    'href="tel:{phone_e164}"',
    "Позвонить Ивану",
    "Оценка по фото",
    "def run_with_retries",
    "def append_report",
    "def self_test",
)

FORBIDDEN_MARKERS = (
    "permissions: write-all",
    "uses: actions/checkout@v4",
    "uses: actions/upload-artifact@v4",
)


def main() -> int:
    findings: list[str] = []

    for path in (WORKFLOW, HELPER):
        if not path.is_file():
            findings.append(f"{path.relative_to(ROOT)} is missing")

    if findings:
        print("Live conversion workflow findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    helper_text = HELPER.read_text(encoding="utf-8")

    for marker in WORKFLOW_MARKERS:
        if marker not in workflow_text:
            findings.append(f".github/workflows/live-site-health.yml must contain {marker}")
    for marker in HELPER_MARKERS:
        if marker not in helper_text:
            findings.append(f"tools/check_live_conversion.py must contain {marker}")
    for marker in FORBIDDEN_MARKERS:
        if marker in workflow_text:
            findings.append(f".github/workflows/live-site-health.yml must not contain {marker}")

    completed = subprocess.run(
        [sys.executable, str(HELPER), "--self-test"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stdout + completed.stderr).strip()
        findings.append("live conversion helper self-test failed: " + detail)

    if findings:
        print("Live conversion workflow findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Live conversion workflow check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
