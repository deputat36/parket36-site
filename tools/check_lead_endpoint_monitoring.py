#!/usr/bin/env python3
"""Validate production lead endpoint monitoring files and secret handling."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "lead-endpoint-health.yml"
CHECKER = ROOT / "tools" / "check_production_lead_endpoint.py"
ISSUE_MANAGER = ROOT / "tools" / "manage_lead_endpoint_issue.py"
DOC = ROOT / "docs" / "production-lead-monitoring.md"

REQUIRED_MARKERS = {
    WORKFLOW: (
        'cron: "47 4 * * *"',
        "workflow_dispatch:",
        "issues: write",
        "PARKET_HEALTHCHECK_TOKEN: ${{ secrets.PARKET_HEALTHCHECK_TOKEN }}",
        "id: health_config",
        "configured=true",
        "configured=false",
        "python tools/check_production_lead_endpoint.py --report lead-endpoint-health.md --require-token",
        "python tools/check_production_lead_endpoint.py --report lead-endpoint-health.md",
        "name: production-lead-endpoint-health",
        "python tools/manage_lead_endpoint_issue.py failure --report lead-endpoint-health.md",
        "python tools/manage_lead_endpoint_issue.py success",
        "steps.health_config.outputs.configured == 'true'",
    ),
    CHECKER: (
        "PARKET_LEAD_ENDPOINT",
        '"test_mode": True',
        '"x-parket-health-token": token',
        '"Origin": "https://parket36.ru"',
        '"parket_leads"',
        '"parket_public_lead_audit"',
        '"telegram_notification"',
        '"email_notification"',
        "PARKET_HEALTHCHECK_TOKEN is not available",
        "The health token is never written to this report.",
        "--require-token",
        "--self-test",
    ),
    ISSUE_MANAGER: (
        "[monitoring] production lead endpoint failure",
        "find_open_issue",
        "Closing automatically",
        '"state": "closed"',
        "--self-test",
    ),
    DOC: (
        "Production lead endpoint health",
        "PARKET_HEALTHCHECK_TOKEN",
        "test_mode",
        "не создаёт заявку",
        "production-lead-endpoint-health",
        "healthcheck_not_configured",
        "healthcheck_forbidden",
    ),
}

FORBIDDEN_WORKFLOW_MARKERS = (
    "set -x",
    'echo "$PARKET_HEALTHCHECK_TOKEN"',
    "printenv PARKET_HEALTHCHECK_TOKEN",
    "--health-token",
)


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
    return (completed.stdout + completed.stderr).strip() or "unknown self-test failure"


def main() -> int:
    findings: list[str] = []

    for path, markers in REQUIRED_MARKERS.items():
        if not path.is_file():
            findings.append(f"missing required file: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in markers:
            if marker not in text:
                findings.append(f"{path.relative_to(ROOT)}: missing marker: {marker}")

    if WORKFLOW.is_file():
        workflow_text = WORKFLOW.read_text(encoding="utf-8", errors="ignore")
        for marker in FORBIDDEN_WORKFLOW_MARKERS:
            if marker in workflow_text:
                findings.append(f"workflow must not expose the health token: {marker}")
        if workflow_text.count("secrets.PARKET_HEALTHCHECK_TOKEN") != 2:
            findings.append("workflow must reference PARKET_HEALTHCHECK_TOKEN exactly twice through secrets")

    for path in (CHECKER, ISSUE_MANAGER):
        if path.is_file():
            failure = run_self_test(path)
            if failure:
                findings.append(f"{path.relative_to(ROOT)} self-test failed: {failure}")

    if findings:
        print("Production lead monitoring findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Production lead endpoint monitoring passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
