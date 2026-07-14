#!/usr/bin/env python3
"""Validate the manual controlled production lead smoke and its protected verifier."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "controlled-lead-smoke.yml"
SCRIPT = ROOT / "tools" / "run_controlled_lead_smoke.py"
DOC = ROOT / "docs" / "controlled-production-lead-smoke.md"
CONFIG = ROOT / "supabase" / "config.toml"
VERIFIER = ROOT / "supabase" / "functions" / "parket-lead-verify" / "index.ts"
REQUEST_ID = ROOT / "supabase" / "functions" / "parket-lead-verify" / "request-id.ts"
REQUEST_ID_TEST = ROOT / "supabase" / "functions" / "parket-lead-verify" / "request-id_test.ts"
DEPLOY_WORKFLOW = ROOT / ".github" / "workflows" / "deploy-lead-function.yml"
SITE_QUALITY = ROOT / ".github" / "workflows" / "site-quality.yml"
PAGES = ROOT / ".github" / "workflows" / "pages.yml"

REQUIRED_MARKERS = {
    WORKFLOW: (
        "name: Controlled production lead smoke",
        "workflow_dispatch:",
        "SEND_CONTROLLED_LEAD",
        "expected_notification:",
        "sent",
        "disabled",
        "any",
        "issues: write",
        "environment: production",
        "PARKET_SMOKE_CONTACT: ${{ secrets.PARKET_SMOKE_CONTACT }}",
        "PARKET_HEALTHCHECK_TOKEN: ${{ secrets.PARKET_HEALTHCHECK_TOKEN }}",
        'if [ "$GITHUB_REF" != "refs/heads/main" ]',
        "uses: actions/checkout@v7",
        "persist-credentials: false",
        "uses: actions/setup-python@v6",
        'python-version: "3.12"',
        "python tools/run_controlled_lead_smoke.py",
        "--expected-notification",
        "name: controlled-lead-smoke",
        "gh issue comment 373",
        "Do not close this issue until Ivan confirms actual receipt",
        "steps.controlled_smoke.outcome == 'failure'",
    ),
    SCRIPT: (
        "PARKET_SMOKE_CONTACT",
        "PARKET_HEALTHCHECK_TOKEN",
        "Контролируемая проверка production",
        "Не обрабатывать как клиентскую заявку",
        "controlled_smoke",
        "parket-lead-verify",
        "parket_leads",
        "parket_public_lead_audit",
        "The report never contains the contact value or health token.",
        "Human confirmation that Ivan actually received",
        "--expected-notification",
        "--self-test",
    ),
    DOC: (
        "Controlled production lead smoke",
        "PARKET_SMOKE_CONTACT",
        "PARKET_HEALTHCHECK_TOKEN",
        "SEND_CONTROLLED_LEAD",
        "реальную техническую заявку",
        "parket-lead-verify",
        "parket_leads",
        "parket_public_lead_audit",
        "не возвращает персональные данные",
        "подтвердить фактическое получение",
        "не закрывает его",
    ),
    CONFIG: (
        "[functions.parket-public-lead]",
        "[functions.parket-lead-verify]",
        "verify_jwt = false",
    ),
    VERIFIER: (
        'const HEALTHCHECK_HEADER = "x-parket-health-token"',
        "ALLOWED_ORIGINS",
        '"https://parket36.ru"',
        '"https://www.parket36.ru"',
        "safeEqual",
        "authorized(req)",
        "validateRequestId",
        "parket_leads",
        "parket_public_lead_audit",
        '.eq("accepted", accepted)',
        "request_id",
    ),
    REQUEST_ID: (
        "REQUEST_ID_MIN_LENGTH = 8",
        "REQUEST_ID_MAX_LENGTH = 120",
        "REQUEST_ID_PATTERN",
        "validateRequestId",
    ),
    REQUEST_ID_TEST: (
        "accepts controlled smoke IDs",
        "rejects missing and malformed IDs",
        "rejects oversized IDs",
    ),
    DEPLOY_WORKFLOW: (
        "Test controlled lead verifier request ID",
        "Type-check controlled lead verifier",
        "Deploy controlled lead verifier",
        "supabase functions deploy parket-lead-verify",
        "--no-verify-jwt",
    ),
    SITE_QUALITY: (
        "Test controlled lead verifier request ID",
        "deno test supabase/functions/parket-lead-verify/request-id_test.ts",
        "deno check supabase/functions/parket-lead-verify/index.ts",
    ),
    PAGES: (
        "Test controlled lead verifier request ID",
        "deno test supabase/functions/parket-lead-verify/request-id_test.ts",
        "deno check supabase/functions/parket-lead-verify/index.ts",
    ),
}

FORBIDDEN_WORKFLOW_MARKERS = (
    "  push:",
    "  pull_request:",
    "  schedule:",
    "permissions: write-all",
    "set -x",
    'echo "$PARKET_SMOKE_CONTACT"',
    'echo "$PARKET_HEALTHCHECK_TOKEN"',
    "state: closed",
    "gh issue close 373",
)

FORBIDDEN_SCRIPT_MARKERS = (
    "print(contact)",
    "print(health_token)",
    '"contact": contact,\n        "health_token"',
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
    return (completed.stdout + completed.stderr).strip() or "unknown self-test error"


def main() -> int:
    findings: list[str] = []
    texts: dict[Path, str] = {}

    for path, markers in REQUIRED_MARKERS.items():
        if not path.is_file():
            findings.append(f"missing required file: {path.relative_to(ROOT)}")
            texts[path] = ""
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        texts[path] = text
        for marker in markers:
            if marker not in text:
                findings.append(f"{path.relative_to(ROOT)}: missing marker: {marker}")

    workflow = texts.get(WORKFLOW, "")
    for marker in FORBIDDEN_WORKFLOW_MARKERS:
        if marker in workflow:
            findings.append(f"controlled smoke workflow contains forbidden marker: {marker}")
    if workflow.count("secrets.PARKET_SMOKE_CONTACT") != 1:
        findings.append("controlled smoke workflow must reference PARKET_SMOKE_CONTACT exactly once")
    if workflow.count("secrets.PARKET_HEALTHCHECK_TOKEN") != 1:
        findings.append("controlled smoke workflow must reference PARKET_HEALTHCHECK_TOKEN exactly once")
    if "PARKET_SMOKE_CONTACT" in workflow.split("inputs:", 1)[-1].split("permissions:", 1)[0]:
        findings.append("PARKET_SMOKE_CONTACT must never be accepted as a workflow input")

    config = texts.get(CONFIG, "")
    if config.count("verify_jwt = false") != 2:
        findings.append("supabase/config.toml must explicitly disable JWT for exactly two protected functions")

    script = texts.get(SCRIPT, "")
    for marker in FORBIDDEN_SCRIPT_MARKERS:
        if marker in script:
            findings.append(f"controlled smoke script can expose protected data: {marker}")

    verifier = texts.get(VERIFIER, "")
    auth_position = verifier.find("if (!authorized(req))")
    client_position = verifier.find("const supabase = createClient")
    query_position = verifier.find("const [lead, audit] = await Promise.all")
    if auth_position < 0 or client_position < 0 or query_position < 0:
        findings.append("verifier authorization and query flow markers are incomplete")
    elif not (auth_position < client_position < query_position):
        findings.append("verifier must authorize before creating the database client and querying rows")

    if SCRIPT.is_file():
        error = run_self_test(SCRIPT)
        if error:
            findings.append("controlled lead smoke self-test failed: " + error)

    if findings:
        print("Controlled lead smoke findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Controlled production lead smoke passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
