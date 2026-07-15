#!/usr/bin/env python3
"""Validate automatic staleness handling for the production lead readiness snapshot."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANUAL_WORKFLOW = ROOT / ".github" / "workflows" / "production-lead-launch-readiness.yml"
STALE_WORKFLOW = ROOT / ".github" / "workflows" / "production-lead-readiness-stale.yml"
VERIFIER = ROOT / "tools" / "verify_production_lead_readiness_current_main.py"
STALE_MARKER = ROOT / "tools" / "mark_production_lead_readiness_stale.py"
DOC = ROOT / "docs" / "production-lead-readiness-staleness.md"
RUNNER = ROOT / "tools" / "run_quality_checks.py"
QUALITY_CHECKER = ROOT / "tools" / "check_quality_runner.py"

REQUIRED_MARKERS = {
    STALE_WORKFLOW: (
        "name: Mark production lead readiness stale",
        "push:",
        "branches:",
        "- main",
        "contents: read",
        "issues: write",
        "production-lead-readiness-stale",
        "cancel-in-progress: true",
        "mark managed production readiness snapshot stale",
        "actions/checkout@v7",
        "persist-credentials: false",
        "actions/setup-python@v6",
        'python-version: "3.12"',
        "Mark issue 373 readiness snapshot stale",
        "GITHUB_TOKEN: ${{ github.token }}",
        "python tools/mark_production_lead_readiness_stale.py",
        '--current-commit "$GITHUB_SHA"',
    ),
    VERIFIER: (
        "Source commit:",
        "/git/ref/heads/main",
        "exactly one valid Source commit",
        "does not match current main",
        "GITHUB_REPOSITORY",
        "GITHUB_TOKEN",
        "--report",
        "--self-test",
    ),
    STALE_MARKER: (
        "ISSUE_NUMBER = 373",
        "parket36-production-lead-launch-readiness",
        "parket36-production-lead-launch-readiness-stale:start",
        "parket36-production-lead-launch-readiness-stale:end",
        "Source commit:",
        "Текущий `main`",
        "не должен использоваться для deploy",
        "find_managed_comment",
        "PATCH",
        "--current-commit",
        "--self-test",
    ),
    DOC: (
        "Автоматическое устаревание production readiness",
        "production-lead-readiness-stale.yml",
        "только при `push` в `main`",
        "STALE",
        "идемпотентен",
        "verify_production_lead_readiness_current_main.py",
        "refs/heads/main",
        "artifact уже сохранён",
        "issue #373 не обновляется старым результатом",
        "controlled real lead",
        "mark_production_lead_readiness_stale.py --self-test",
        "check_production_lead_readiness_staleness.py",
    ),
    RUNNER: (
        '"Validate production lead readiness staleness", ["tools/check_production_lead_readiness_staleness.py"]',
    ),
    QUALITY_CHECKER: (
        '["tools/check_production_lead_readiness_staleness.py"]',
    ),
}

FORBIDDEN_STALE_WORKFLOW_MARKERS = (
    "workflow_dispatch:",
    "pull_request:",
    "schedule:",
    "environment: production",
    "permissions: write-all",
    "SUPABASE_ACCESS_TOKEN",
    "PARKET_HEALTHCHECK_TOKEN",
    "PARKET_SMOKE_CONTACT",
    "supabase functions deploy",
    "tools/run_controlled_lead_smoke.py",
    "tools/check_production_lead_endpoint.py",
    "set -x",
)

PROTECTED_MARKERS = (
    "SUPABASE_ACCESS_TOKEN =",
    "PARKET_HEALTHCHECK_TOKEN =",
    "PARKET_SMOKE_CONTACT =",
    "print(contact)",
    "print(token)",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def run_self_test(path: Path) -> str | None:
    completed = subprocess.run(
        [sys.executable, str(path), "--self-test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return None
    return (completed.stdout + completed.stderr).strip() or "unknown self-test error"


def block(text: str, start: str, end: str) -> str:
    start_position = text.find(start)
    end_position = text.find(end, start_position + 1)
    if start_position < 0 or end_position < 0:
        return ""
    return text[start_position:end_position]


def main() -> int:
    findings: list[str] = []
    texts: dict[Path, str] = {}

    for path, markers in REQUIRED_MARKERS.items():
        if not path.is_file():
            findings.append(f"missing required file: {path.relative_to(ROOT)}")
            texts[path] = ""
            continue
        text = read(path)
        texts[path] = text
        for marker in markers:
            if marker not in text:
                findings.append(f"{path.relative_to(ROOT)}: missing marker: {marker}")

    stale_workflow = texts.get(STALE_WORKFLOW, "")
    for marker in FORBIDDEN_STALE_WORKFLOW_MARKERS:
        if marker in stale_workflow:
            findings.append(f"stale workflow contains forbidden marker: {marker}")
    if stale_workflow.count("issues: write") != 1:
        findings.append("stale workflow must grant issues: write exactly once")
    if stale_workflow.count("contents: read") != 1:
        findings.append("stale workflow must grant contents: read exactly once")
    if stale_workflow.count("push:") != 1:
        findings.append("stale workflow must have exactly one push trigger")

    for marker in (
        "GITHUB_TOKEN: ${{ github.token }}",
        "python tools/mark_production_lead_readiness_stale.py",
        '--current-commit "$GITHUB_SHA"',
    ):
        if marker not in stale_workflow:
            findings.append(f"stale workflow publish step must contain: {marker}")

    manual_workflow = read(MANUAL_WORKFLOW) if MANUAL_WORKFLOW.is_file() else ""
    issue_block = block(
        manual_workflow,
        "- name: Update issue 373 readiness snapshot",
        "- name: Fail when launch prerequisites are blocked",
    )
    for marker in (
        "id: issue_snapshot",
        "if: always() && steps.stamp.outcome == 'success'",
        "continue-on-error: true",
        "set -euo pipefail",
        "python tools/verify_production_lead_readiness_current_main.py",
        "python tools/manage_production_lead_launch_readiness.py",
        "--report production-lead-launch-readiness.md",
    ):
        if marker not in issue_block:
            findings.append(f"atomic issue snapshot step must contain: {marker}")

    verifier_position = issue_block.find("python tools/verify_production_lead_readiness_current_main.py")
    manager_position = issue_block.find("python tools/manage_production_lead_launch_readiness.py")
    if min(verifier_position, manager_position) < 0 or verifier_position > manager_position:
        findings.append("current-main verifier must run before issue manager")

    fail_block = manual_workflow[manual_workflow.find("- name: Fail when launch prerequisites are blocked") :]
    if "steps.issue_snapshot.outcome == 'failure'" not in fail_block:
        findings.append("manual readiness workflow must fail when atomic issue snapshot step fails")

    for path in (VERIFIER, STALE_MARKER):
        text = texts.get(path, "")
        for marker in PROTECTED_MARKERS:
            if marker in text:
                findings.append(f"{path.relative_to(ROOT)} contains protected-data marker: {marker}")

    for path, label in (
        (VERIFIER, "production lead readiness current-main verifier"),
        (STALE_MARKER, "production lead readiness stale marker"),
    ):
        if path.is_file():
            error = run_self_test(path)
            if error:
                findings.append(f"{label} self-test failed: {error}")

    if findings:
        print("Production lead readiness staleness findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("Production lead readiness staleness guardrail passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
