#!/usr/bin/env python3
"""Validate the safe search launch readiness workflow, helpers and docs."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "search-launch-readiness.yml"
HELPER = ROOT / "tools" / "build_search_launch_readiness.py"
MANAGER = ROOT / "tools" / "manage_search_launch_readiness.py"
DOC = ROOT / "docs" / "search-launch-readiness.md"
DISCOVERY_DOC = ROOT / "docs" / "search-discovery-launch.md"
OPERATIONS_INDEX = ROOT / "docs" / "operations-index.md"

WORKFLOW_MARKERS = (
    "name: Search launch readiness",
    "workflow_dispatch:",
    "workflow_run:",
    'workflows: ["Deploy GitHub Pages"]',
    "types: [completed]",
    "contents: read",
    "issues: write",
    "github.event_name == 'workflow_dispatch'",
    "github.ref_name == github.event.repository.default_branch",
    "github.event_name == 'workflow_run'",
    "github.event.workflow_run.conclusion == 'success'",
    "github.event.workflow_run.head_branch == github.event.repository.default_branch",
    "uses: actions/checkout@v7",
    "ref: ${{ github.event_name == 'workflow_run' && github.event.workflow_run.head_sha || github.event.repository.default_branch }}",
    "uses: actions/setup-python@v6",
    'python-version: "3.12"',
    "python tools/check_live_site.py",
    "--report search-live-health.md",
    "python tools/submit_indexnow.py",
    "--verify-live-key",
    "--report search-indexnow.md",
    "python tools/build_search_launch_readiness.py",
    "SEARCH_SOURCE_COMMIT: ${{ github.event_name == 'workflow_run' && github.event.workflow_run.head_sha || github.sha }}",
    '--source-commit "$SEARCH_SOURCE_COMMIT"',
    'cat search-launch-readiness.md >> "$GITHUB_STEP_SUMMARY"',
    "uses: actions/upload-artifact@v7",
    "name: search-launch-readiness",
    "retention-days: 30",
    "name: Update roadmap readiness snapshot",
    "continue-on-error: true",
    "GITHUB_TOKEN: ${{ github.token }}",
    "python tools/manage_search_launch_readiness.py --report search-launch-readiness.md",
    "if: steps.readiness.outcome == 'failure'",
)

FORBIDDEN_WORKFLOW_MARKERS = (
    "schedule:",
    "contents: write",
    "permissions: write-all",
    "environment: production",
    "secrets.",
    "--submit",
)

HELPER_MARKERS = (
    "class ComponentResult",
    "def read_component(",
    "def evaluate_reports(",
    "TECHNICAL_READY_ANALYTICS_PENDING",
    "SEARCH_LAUNCH_READY",
    "BLOCKED",
    "def render_report(",
    "def run_self_test(",
    'return 1 if level == "BLOCKED" else 0',
)

MANAGER_MARKERS = (
    "ISSUE_NUMBER = 308",
    'COMMENT_MARKER = "<!-- parket36-search-launch-readiness -->"',
    "def validate_safe_report(",
    "def render_comment(",
    "def find_managed_comment(",
    "def publish_snapshot(",
    "def self_test(",
    "только техническую готовность",
)

DOC_MARKERS = (
    "Actions → Search launch readiness",
    "после каждого успешного `Deploy GitHub Pages`",
    "один обновляемый комментарий в issue #308",
    "TECHNICAL_READY_ANALYTICS_PENDING",
    "SEARCH_LAUNCH_READY",
    "не вызывает `--submit` для IndexNow",
    "не считает успешную техническую проверку гарантией индексации или позиций",
)

DISCOVERY_MARKERS = (
    "Техническая публикация `https://parket36.ru/` восстановлена",
    "Search launch readiness",
    "автоматически после каждого успешного Pages deploy",
    "не подтверждает фактическое добавление сайта в поисковые кабинеты",
)

FORBIDDEN_DISCOVERY_MARKERS = (
    "Поисковики не смогут стабильно находить страницы, пока `https://parket36.ru/` не открывается",
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
    for path in (WORKFLOW, HELPER, MANAGER, DOC, DISCOVERY_DOC, OPERATIONS_INDEX):
        if not path.is_file():
            findings.append(f"{path.relative_to(ROOT)} is missing")

    if findings:
        print("Search launch readiness findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    helper_text = HELPER.read_text(encoding="utf-8")
    manager_text = MANAGER.read_text(encoding="utf-8")
    doc_text = DOC.read_text(encoding="utf-8")
    discovery_text = DISCOVERY_DOC.read_text(encoding="utf-8")
    operations_text = OPERATIONS_INDEX.read_text(encoding="utf-8")

    for marker in WORKFLOW_MARKERS:
        if marker not in workflow_text:
            findings.append(f"search readiness workflow must contain {marker}")
    for marker in FORBIDDEN_WORKFLOW_MARKERS:
        if marker in workflow_text:
            findings.append(f"search readiness workflow must not contain {marker}")
    for marker in HELPER_MARKERS:
        if marker not in helper_text:
            findings.append(f"search readiness helper must contain {marker}")
    for marker in MANAGER_MARKERS:
        if marker not in manager_text:
            findings.append(f"search readiness issue manager must contain {marker}")
    for marker in DOC_MARKERS:
        if marker not in doc_text:
            findings.append(f"search readiness doc must contain {marker}")
    for marker in DISCOVERY_MARKERS:
        if marker not in discovery_text:
            findings.append(f"search discovery doc must contain {marker}")
    for marker in FORBIDDEN_DISCOVERY_MARKERS:
        if marker in discovery_text:
            findings.append(f"search discovery doc must not contain stale marker: {marker}")
    if "docs/search-launch-readiness.md" not in operations_text:
        findings.append("operations index must reference docs/search-launch-readiness.md")
    if "автоматический post-deploy" not in operations_text:
        findings.append("operations index must describe automatic post-deploy search readiness")

    checks = (
        (HELPER, ("--self-test",), "search readiness helper self-test"),
        (MANAGER, ("--self-test",), "search readiness issue-manager self-test"),
    )
    for path, args, label in checks:
        returncode, detail = run_python(path, *args)
        if returncode != 0:
            findings.append(f"{label} failed: {detail}")

    if findings:
        print("Search launch readiness findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Search launch readiness check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
