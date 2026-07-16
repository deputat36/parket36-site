#!/usr/bin/env python3
"""Validate the verified deploy drift watchdog and its operational contract."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "verified-deploy-drift.yml"
CHECKER = ROOT / "tools" / "check_verified_deploy_drift.py"
MANAGER = ROOT / "tools" / "manage_verified_deploy_drift_issue.py"
DOC = ROOT / "docs" / "verified-deploy-drift.md"

WORKFLOW_MARKERS = (
    "name: Verified deploy drift",
    'cron: "53 5 * * *"',
    "workflow_dispatch:",
    "workflow_run:",
    'workflows: ["Live site health"]',
    "types: [completed]",
    "contents: read",
    "actions: read",
    "issues: write",
    "group: verified-deploy-drift",
    "cancel-in-progress: false",
    "github.event.workflow_run.conclusion == 'success'",
    "ref: ${{ github.event_name == 'workflow_run' && github.event.workflow_run.head_sha || github.event.repository.default_branch }}",
    "uses: actions/checkout@v7",
    "uses: actions/setup-python@v6",
    'python-version: "3.12"',
    "python tools/check_verified_deploy_drift.py --self-test",
    "python tools/manage_verified_deploy_drift_issue.py --self-test",
    "CHECK_TARGET_SHA: ${{ github.event_name == 'workflow_run' && github.event.workflow_run.head_sha || '' }}",
    'TARGET_SHA="${CHECK_TARGET_SHA:-$(git rev-parse HEAD)}"',
    "--current-sha \"$TARGET_SHA\"",
    "--report verified-deploy-drift-report.md",
    "uses: actions/upload-artifact@v7",
    "name: verified-deploy-drift-report",
    "retention-days: 30",
    "python tools/manage_verified_deploy_drift_issue.py",
    "failure",
    "python tools/manage_verified_deploy_drift_issue.py success",
    "if: steps.drift.outcome == 'failure'",
    "if: steps.drift.outcome == 'success'",
    "run: exit 1",
)

CHECKER_MARKERS = (
    'ISSUE_NUMBER = 308',
    'EXPECTED_TITLE = "Автономная дорожная карта улучшения Паркет36"',
    'COMMENT_MARKER = "<!-- parket36-live-verification -->"',
    "def extract_ledger_sha(",
    "def evaluate_drift(",
    "multiple live verification ledger comments found",
    "current main commit does not match",
    "Verified deploy drift self-test passed",
)

MANAGER_MARKERS = (
    'ISSUE_TITLE = "[monitoring] verified deploy drift"',
    'WORKFLOW_FILE = "verified-deploy-drift.yml"',
    "def previous_completed_conclusion(",
    "First isolated verified deploy drift",
    "updated in place",
    '"state": "closed", "state_reason": "completed"',
    "Verified deploy drift issue manager self-test passed",
)

DOC_MARKERS = (
    "Watchdog подтверждённого deploy",
    "Live site health",
    "текущий `main`",
    "Последняя подтверждённая публикация parket36.ru",
    "Первый единичный drift не создаёт issue",
    "[monitoring] verified deploy drift",
    "verified-deploy-drift-report",
    "tools/check_verified_deploy_drift.py --self-test",
    "tools/manage_verified_deploy_drift_issue.py --self-test",
    "не развёртывает сайт",
)

FORBIDDEN_WORKFLOW_MARKERS = (
    "push:",
    "pull_request:",
    "permissions: write-all",
    "pages: write",
    "id-token: write",
    "SUPABASE_",
    "PARKET_HEALTHCHECK_TOKEN",
)


def run_self_test(path: Path) -> tuple[int, str]:
    completed = subprocess.run(
        [sys.executable, str(path), "--self-test"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode, (completed.stdout + completed.stderr).strip()


def main() -> int:
    findings: list[str] = []

    for path in (WORKFLOW, CHECKER, MANAGER, DOC):
        if not path.is_file():
            findings.append(f"{path.relative_to(ROOT)} is missing")

    if findings:
        print("Verified deploy drift workflow findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    checker_text = CHECKER.read_text(encoding="utf-8")
    manager_text = MANAGER.read_text(encoding="utf-8")
    doc_text = DOC.read_text(encoding="utf-8")

    for marker in WORKFLOW_MARKERS:
        if marker not in workflow_text:
            findings.append(f"verified-deploy-drift.yml must contain {marker}")
    for marker in FORBIDDEN_WORKFLOW_MARKERS:
        if marker in workflow_text:
            findings.append(f"verified-deploy-drift.yml must not contain {marker}")
    if workflow_text.count("continue-on-error: true") != 3:
        findings.append("verified-deploy-drift.yml must use continue-on-error exactly for check and issue operations")

    for marker in CHECKER_MARKERS:
        if marker not in checker_text:
            findings.append(f"check_verified_deploy_drift.py must contain {marker}")
    for marker in MANAGER_MARKERS:
        if marker not in manager_text:
            findings.append(f"manage_verified_deploy_drift_issue.py must contain {marker}")
    for marker in DOC_MARKERS:
        if marker not in doc_text:
            findings.append(f"verified-deploy-drift.md must contain {marker}")

    for path, label in ((CHECKER, "drift checker"), (MANAGER, "drift issue manager")):
        returncode, detail = run_self_test(path)
        if returncode != 0:
            findings.append(f"{label} self-test failed: {detail}")

    if findings:
        print("Verified deploy drift workflow findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Verified deploy drift workflow check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
