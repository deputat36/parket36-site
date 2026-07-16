#!/usr/bin/env python3
"""Validate operational documentation for CI and deploy workflows."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"
SITE_QUALITY_PATH = ROOT / ".github" / "workflows" / "site-quality.yml"
PAGES_PATH = ROOT / ".github" / "workflows" / "pages.yml"
LIVE_HEALTH_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "live-site-health.yml"
LIVE_HEALTH_DOC_PATH = ROOT / "docs" / "live-site-monitoring.md"
LIVE_VERIFICATION_LEDGER_PATH = ROOT / "tools" / "record_live_verification.py"
INDEXNOW_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "indexnow.yml"
INDEXNOW_DOC_PATH = ROOT / "docs" / "indexnow-automation.md"
INDEXNOW_ISSUE_MANAGER_PATH = ROOT / "tools" / "manage_indexnow_issue.py"
QUALITY_RUNNER = "python tools/run_quality_checks.py"
OLD_LOCAL_CHECK_BLOCK = "python tools/site_settings.py --check\npython tools/check_site.py"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> int:
    findings: list[str] = []

    required_files = (
        README_PATH,
        SITE_QUALITY_PATH,
        PAGES_PATH,
        LIVE_HEALTH_WORKFLOW_PATH,
        LIVE_HEALTH_DOC_PATH,
        LIVE_VERIFICATION_LEDGER_PATH,
        INDEXNOW_WORKFLOW_PATH,
        INDEXNOW_DOC_PATH,
        INDEXNOW_ISSUE_MANAGER_PATH,
    )
    missing = [path.relative_to(ROOT).as_posix() for path in required_files if not path.is_file()]
    if missing:
        print("Documentation findings:")
        for path in missing:
            print(f"  - required file is missing: {path}")
        return 1

    readme = read(README_PATH)
    site_quality = read(SITE_QUALITY_PATH)
    pages = read(PAGES_PATH)
    live_health_workflow = read(LIVE_HEALTH_WORKFLOW_PATH)
    live_health_doc = read(LIVE_HEALTH_DOC_PATH)
    live_verification_ledger = read(LIVE_VERIFICATION_LEDGER_PATH)
    indexnow_workflow = read(INDEXNOW_WORKFLOW_PATH)
    indexnow_doc = read(INDEXNOW_DOC_PATH)

    required_readme_markers = [
        QUALITY_RUNNER,
        "tools/run_quality_checks.py",
        "check_domain_settings.py",
        "check_workflows.py",
        "check_quality_runner.py",
        "check_shared_shell_coverage.py",
        "shared-shell-coverage",
        "check_content_inventory.py",
        "content-inventory",
        "check_live_site.py",
        "check_empty_link_attributes.py",
        "check_conversion_paths.py",
        "check_lead_paths.py",
        "check_lead_reliability.py",
    ]
    for marker in required_readme_markers:
        if marker not in readme:
            findings.append(f"README.md must mention {marker}")

    if OLD_LOCAL_CHECK_BLOCK in readme:
        findings.append("README.md still documents the old local multi-command quality check")

    for path, text in ((SITE_QUALITY_PATH, site_quality), (PAGES_PATH, pages)):
        if QUALITY_RUNNER not in text:
            findings.append(f"{path.relative_to(ROOT)} must run {QUALITY_RUNNER}")

    required_live_health_doc_markers = (
        "tools/record_live_verification.py",
        "Последняя подтверждённая публикация parket36.ru",
        "parket36-live-verification",
        "issue #308",
        "Плановый и ручной monitoring запись не обновляют",
        "30-дневном artifact",
        "python tools/record_live_verification.py --self-test",
    )
    for marker in required_live_health_doc_markers:
        if marker not in live_health_doc:
            findings.append(f"docs/live-site-monitoring.md must mention {marker}")

    required_live_health_workflow_markers = (
        "- name: Record latest verified deploy",
        "github.event_name == 'workflow_run' &&",
        "steps.live_health.outcome == 'success' &&",
        "steps.live_conversion.outcome == 'success' &&",
        "steps.live_public_copy.outcome == 'success' &&",
        "steps.deployment_source.outcome == 'success'",
        "PAGES_DEPLOY_SHA: ${{ github.event.workflow_run.head_sha }}",
        "PAGES_DEPLOY_RUN_ID: ${{ github.event.workflow_run.id }}",
        "run: python tools/record_live_verification.py",
    )
    for marker in required_live_health_workflow_markers:
        if marker not in live_health_workflow:
            findings.append(f"Live health workflow must contain {marker}")

    required_ledger_markers = (
        "ISSUE_NUMBER = 308",
        'COMMENT_MARKER = "<!-- parket36-live-verification -->"',
        'if event_name != "workflow_run"',
        "multiple live verification ledger comments found",
        'api_request("PATCH", f"{base}/issues/comments/{comment_id}"',
        "Live verification ledger self-test passed",
    )
    for marker in required_ledger_markers:
        if marker not in live_verification_ledger:
            findings.append(f"tools/record_live_verification.py must contain {marker}")

    required_indexnow_doc_markers = (
        "Notify IndexNow after deploy",
        "workflow_dispatch",
        "tools/submit_indexnow.py --self-test",
        "tools/submit_indexnow.py --check",
        "tools/manage_indexnow_issue.py --self-test",
        "tools/check_indexnow_workflow.py",
        "[monitoring] IndexNow notification failure",
        "indexnow-report",
        "Ответ `200` или `202`",
        "не гарантирует",
    )
    for marker in required_indexnow_doc_markers:
        if marker not in indexnow_doc:
            findings.append(f"docs/indexnow-automation.md must mention {marker}")

    required_indexnow_workflow_markers = (
        'workflows: ["Deploy GitHub Pages"]',
        "--report indexnow-report.md",
        "actions: read",
        "issues: write",
        "python tools/manage_indexnow_issue.py failure --report indexnow-report.md",
        "python tools/manage_indexnow_issue.py success",
    )
    for marker in required_indexnow_workflow_markers:
        if marker not in indexnow_workflow:
            findings.append(f"IndexNow workflow must contain {marker}")

    if findings:
        print("Documentation findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Documentation check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
