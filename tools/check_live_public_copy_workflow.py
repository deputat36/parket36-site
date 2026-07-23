#!/usr/bin/env python3
"""Validate live public-copy monitoring and its offline contracts."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "live-site-health.yml"
LIVE_HELPER = ROOT / "tools" / "check_live_public_copy.py"
SOURCE_CHECKER = ROOT / "tools" / "check_homepage_public_copy.py"

WORKFLOW_MARKERS = (
    "id: live_public_copy",
    "python tools/check_live_public_copy.py",
    "--report live-health-report.md",
    "LIVE_PUBLIC_COPY_ATTEMPTS:",
    '--attempts "$LIVE_PUBLIC_COPY_ATTEMPTS"',
    "--retry-delay 10",
    "--timeout 20",
    "steps.live_public_copy.outcome == 'failure'",
    "steps.live_public_copy.outcome == 'success'",
    "name: live-health-report",
)

HELPER_MARKERS = (
    "Live homepage public copy",
    "Homepage client-ready copy",
    "Request page honest lead copy",
    "Фото вместо иллюстрации",
    "Как подготовить фотографии пола для предварительной оценки",
    "REQUEST_FORBIDDEN = (",
    "REQUEST_REQUIRED = (",
    "заявка уйдёт Ивану",
    "Форма попробует сохранить заявку в защищённой системе",
    'path="/zayavka/"',
    "def request_url",
    "evaluate_request",
    "verify_public_copy",
    "cache_bust_attempt",
    '"Cache-Control": "no-cache, no-store, max-age=0"',
    "def run_with_retries",
    "def append_report",
    "def self_test",
)

SOURCE_MARKERS = (
    "FORBIDDEN = (",
    "REQUIRED = (",
    "Homepage source copy is client-ready",
    "после съёмки по ТЗ",
)


def run_check(command: list[str], label: str, findings: list[str]) -> None:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stdout + completed.stderr).strip()
        findings.append(f"{label} failed: {detail}")


def main() -> int:
    findings: list[str] = []

    for path in (WORKFLOW, LIVE_HELPER, SOURCE_CHECKER):
        if not path.is_file():
            findings.append(f"{path.relative_to(ROOT)} is missing")

    if findings:
        print("Live public-copy workflow findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    helper_text = LIVE_HELPER.read_text(encoding="utf-8")
    source_text = SOURCE_CHECKER.read_text(encoding="utf-8")

    for marker in WORKFLOW_MARKERS:
        if marker not in workflow_text:
            findings.append(f".github/workflows/live-site-health.yml must contain {marker}")
    for marker in HELPER_MARKERS:
        if marker not in helper_text:
            findings.append(f"tools/check_live_public_copy.py must contain {marker}")
    for marker in SOURCE_MARKERS:
        if marker not in source_text:
            findings.append(f"tools/check_homepage_public_copy.py must contain {marker}")

    run_check([sys.executable, str(LIVE_HELPER), "--self-test"], "live helper self-test", findings)
    run_check([sys.executable, str(SOURCE_CHECKER)], "homepage source checker", findings)

    if findings:
        print("Live public-copy workflow findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Live public-copy workflow check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
