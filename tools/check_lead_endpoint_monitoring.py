#!/usr/bin/env python3
"""Validate production lead endpoint monitoring, shared settings and secret handling."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "lead-endpoint-health.yml"
CHECKER = ROOT / "tools" / "check_production_lead_endpoint.py"
ISSUE_MANAGER = ROOT / "tools" / "manage_lead_endpoint_issue.py"
DOC = ROOT / "docs" / "production-lead-monitoring.md"
CONFIG = ROOT / "data" / "site.json"
SITE_SETTINGS = ROOT / "tools" / "site_settings.py"
MAIN_JS = ROOT / "js" / "main.js"
ENDPOINT_DOCS = (
    ROOT / "docs" / "supabase-parket-leads.md",
    ROOT / "docs" / "lead-endpoint-test-mode.md",
)
ENDPOINT_RE = re.compile(
    r"https://[a-z0-9-]+\.supabase\.co/functions/v1/parket-public-lead"
)
MAIN_CONST_RE = re.compile(
    r"const\s+PARKET_LEAD_ENDPOINT\s*=\s*['\"](?P<url>https://[^'\"]+)['\"]\s*;"
)

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
        "endpoint_from_site",
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
        "data/site.json",
        "site_settings.py --write",
        "PARKET_HEALTHCHECK_TOKEN",
        "test_mode",
        "не создаёт заявку",
        "production-lead-endpoint-health",
        "healthcheck_not_configured",
        "healthcheck_forbidden",
    ),
    CONFIG: ('"lead_endpoint":',),
    SITE_SETTINGS: (
        '"lead_endpoint"',
        "LEAD_ENDPOINT_CONST_RE",
        "update_endpoint_text",
        "site_settings.py --write",
    ),
    MAIN_JS: ("const PARKET_LEAD_ENDPOINT =",),
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


def configured_endpoint(findings: list[str]) -> str:
    try:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(f"cannot read data/site.json: {exc}")
        return ""

    endpoint = str(payload.get("lead_endpoint") or "").strip()
    if not ENDPOINT_RE.fullmatch(endpoint):
        findings.append(
            "data/site.json lead_endpoint must be an HTTPS Supabase URL ending in "
            "/functions/v1/parket-public-lead"
        )
        return ""
    return endpoint


def validate_endpoint_sync(expected: str, findings: list[str]) -> None:
    if not expected:
        return

    try:
        main_text = MAIN_JS.read_text(encoding="utf-8")
    except OSError as exc:
        findings.append(f"cannot read js/main.js: {exc}")
        return

    main_matches = list(MAIN_CONST_RE.finditer(main_text))
    if len(main_matches) != 1:
        findings.append("js/main.js must contain exactly one PARKET_LEAD_ENDPOINT constant")
    elif main_matches[0].group("url") != expected:
        findings.append("js/main.js PARKET_LEAD_ENDPOINT differs from data/site.json")

    for path in ENDPOINT_DOCS:
        if not path.is_file():
            findings.append(f"missing endpoint documentation: {path.relative_to(ROOT)}")
            continue
        values = ENDPOINT_RE.findall(path.read_text(encoding="utf-8", errors="ignore"))
        if not values:
            findings.append(f"{path.relative_to(ROOT)} is missing the production endpoint URL")
            continue
        unexpected = sorted({value for value in values if value != expected})
        if unexpected:
            findings.append(
                f"{path.relative_to(ROOT)} contains endpoint values different from data/site.json: "
                + ", ".join(unexpected)
            )


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

    validate_endpoint_sync(configured_endpoint(findings), findings)

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
