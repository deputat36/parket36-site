#!/usr/bin/env python3
"""Validate repeated GitHub Pages deployment failure monitoring."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "pages-deploy-monitor.yml"
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
MANAGER = ROOT / "tools" / "manage_pages_deploy_issue.py"
DOC = ROOT / "docs" / "pages-deploy-monitoring.md"

WORKFLOW_MARKERS = (
    "name: Monitor Pages deploy",
    "workflow_run:",
    'workflows: ["Deploy GitHub Pages"]',
    "types: [completed]",
    "contents: read",
    "actions: read",
    "issues: write",
    "group: pages-deploy-monitor",
    "cancel-in-progress: false",
    "ref: ${{ github.event.workflow_run.head_sha }}",
    "uses: actions/checkout@v7",
    "uses: actions/setup-python@v6",
    'python-version: "3.12"',
    "python tools/manage_pages_deploy_issue.py --self-test",
    "PAGES_DEPLOY_RUN_ID: ${{ github.event.workflow_run.id }}",
    "PAGES_DEPLOY_SHA: ${{ github.event.workflow_run.head_sha }}",
    "PAGES_DEPLOY_CONCLUSION: ${{ github.event.workflow_run.conclusion }}",
    "run: python tools/manage_pages_deploy_issue.py",
)

MANAGER_MARKERS = (
    'ISSUE_TITLE = "[monitoring] GitHub Pages deploy failure"',
    'WORKFLOW_FILE = "pages.yml"',
    "FAILURE_CONCLUSIONS = frozenset",
    "NON_ALERTING_CONCLUSIONS = frozenset",
    "def previous_completed_conclusion(",
    "def should_open_issue(",
    '"PATCH"',
    '"state": "closed", "state_reason": "completed"',
    "First isolated Pages deploy failure",
    "updated in place",
    "Pages deploy issue manager self-test passed",
)

DOC_MARKERS = (
    "Мониторинг GitHub Pages deploy",
    "Первый единичный отказ не создаёт issue",
    "[monitoring] GitHub Pages deploy failure",
    "Тело существующей задачи обновляется на месте",
    "state_reason: completed",
    "tools/manage_pages_deploy_issue.py --self-test",
    "tools/check_pages_deploy_monitoring.py",
    "не повторяет deploy",
)

FORBIDDEN_WORKFLOW_MARKERS = (
    "schedule:",
    "workflow_dispatch:",
    "continue-on-error:",
    "permissions: write-all",
    "pull_request:",
)


def run_self_test() -> tuple[int, str]:
    completed = subprocess.run(
        [sys.executable, str(MANAGER), "--self-test"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode, (completed.stdout + completed.stderr).strip()


def main() -> int:
    findings: list[str] = []

    for path in (WORKFLOW, PAGES_WORKFLOW, MANAGER, DOC):
        if not path.is_file():
            findings.append(f"{path.relative_to(ROOT)} is missing")

    if findings:
        print("Pages deploy monitoring findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    pages_text = PAGES_WORKFLOW.read_text(encoding="utf-8")
    manager_text = MANAGER.read_text(encoding="utf-8")
    doc_text = DOC.read_text(encoding="utf-8")

    if "name: Deploy GitHub Pages" not in pages_text:
        findings.append("pages.yml must keep the monitored workflow name")

    for marker in WORKFLOW_MARKERS:
        if marker not in workflow_text:
            findings.append(f"pages-deploy-monitor.yml must contain {marker}")
    for marker in FORBIDDEN_WORKFLOW_MARKERS:
        if marker in workflow_text:
            findings.append(f"pages-deploy-monitor.yml must not contain {marker}")
    for marker in MANAGER_MARKERS:
        if marker not in manager_text:
            findings.append(f"manage_pages_deploy_issue.py must contain {marker}")
    for marker in DOC_MARKERS:
        if marker not in doc_text:
            findings.append(f"pages-deploy-monitoring.md must contain {marker}")

    returncode, detail = run_self_test()
    if returncode != 0:
        findings.append(f"Pages deploy issue manager self-test failed: {detail}")

    if findings:
        print("Pages deploy monitoring findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Pages deploy monitoring check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
