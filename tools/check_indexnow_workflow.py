#!/usr/bin/env python3
"""Validate the post-deploy IndexNow workflow and its offline helper contract."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "indexnow.yml"
HELPER = ROOT / "tools" / "submit_indexnow.py"
ISSUE_MANAGER = ROOT / "tools" / "manage_indexnow_issue.py"
CONFIG = ROOT / "data" / "indexnow.json"

WORKFLOW_MARKERS = (
    "name: Notify IndexNow after deploy",
    'workflows: ["Deploy GitHub Pages"]',
    "types: [completed]",
    "workflow_dispatch:",
    "contents: read",
    "actions: read",
    "issues: write",
    "github.event.workflow_run.conclusion == 'success'",
    "uses: actions/checkout@v7",
    "ref: ${{ github.event_name == 'workflow_run' && github.event.workflow_run.head_sha || github.sha }}",
    "uses: actions/setup-python@v6",
    'python-version: "3.12"',
    "python tools/submit_indexnow.py --self-test",
    "python tools/submit_indexnow.py --check",
    "python tools/manage_indexnow_issue.py --self-test",
    "id: indexnow",
    "continue-on-error: true",
    "--submit",
    "--attempts 6",
    "--retry-delay 10",
    "--timeout 20",
    "--report indexnow-report.md",
    "uses: actions/upload-artifact@v7",
    "name: indexnow-report",
    "retention-days: 30",
    "name: Update repeated IndexNow failure issue",
    "if: steps.indexnow.outcome == 'failure'",
    "python tools/manage_indexnow_issue.py failure --report indexnow-report.md",
    "name: Close recovered IndexNow issue",
    "if: steps.indexnow.outcome == 'success'",
    "python tools/manage_indexnow_issue.py success",
    "GITHUB_TOKEN: ${{ github.token }}",
)

HELPER_MARKERS = (
    "class IndexNowReport",
    "def verify_live_key_once",
    "def verify_live_key(",
    "def build_payload",
    "def report_markdown",
    "def write_report",
    "def run_self_test",
    "status not in {200, 202}",
    '"keyLocation": key_location(domain, config)',
)

ISSUE_MANAGER_MARKERS = (
    'ISSUE_TITLE = "[monitoring] IndexNow notification failure"',
    'WORKFLOW_FILE = "indexnow.yml"',
    "def previous_completed_conclusion",
    "def handle_failure",
    "def handle_success",
    "First isolated IndexNow failure",
    '"state_reason": "completed"',
    "def self_test",
)

FORBIDDEN_WORKFLOW_MARKERS = (
    "permissions: write-all",
    "contents: write",
    "uses: actions/checkout@v4",
    "uses: actions/upload-artifact@v4",
    "ready=false",
    "submission skipped",
)


def run_python(path: Path, *args: str) -> tuple[int, str]:
    completed = subprocess.run(
        [sys.executable, str(path), *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode, (completed.stdout + completed.stderr).strip()


def main() -> int:
    findings: list[str] = []

    for path in (WORKFLOW, HELPER, ISSUE_MANAGER, CONFIG):
        if not path.is_file():
            findings.append(f"{path.relative_to(ROOT)} is missing")

    if findings:
        print("IndexNow workflow findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    helper_text = HELPER.read_text(encoding="utf-8")
    manager_text = ISSUE_MANAGER.read_text(encoding="utf-8")

    for marker in WORKFLOW_MARKERS:
        if marker not in workflow_text:
            findings.append(f".github/workflows/indexnow.yml must contain {marker}")
    for marker in FORBIDDEN_WORKFLOW_MARKERS:
        if marker in workflow_text:
            findings.append(f".github/workflows/indexnow.yml must not contain {marker}")
    for marker in HELPER_MARKERS:
        if marker not in helper_text:
            findings.append(f"tools/submit_indexnow.py must contain {marker}")
    for marker in ISSUE_MANAGER_MARKERS:
        if marker not in manager_text:
            findings.append(f"tools/manage_indexnow_issue.py must contain {marker}")

    checks = (
        (HELPER, ("--self-test",), "IndexNow helper offline self-test"),
        (HELPER, ("--check",), "IndexNow helper static contract check"),
        (ISSUE_MANAGER, ("--self-test",), "IndexNow issue-manager self-test"),
    )
    for path, args, label in checks:
        returncode, detail = run_python(path, *args)
        if returncode != 0:
            findings.append(f"{label} failed: {detail}")

    if findings:
        print("IndexNow workflow findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("IndexNow workflow check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
