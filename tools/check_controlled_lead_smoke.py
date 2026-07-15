#!/usr/bin/env python3
"""Validate the manual controlled production lead smoke and its protected verifier."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "controlled-lead-smoke.yml"
SCRIPT = ROOT / "tools" / "run_controlled_lead_smoke.py"
SECRET_CHECKER = ROOT / "tools" / "check_controlled_smoke_github_secrets.py"
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
        "operation:",
        "default: validate-only",
        "- validate-only",
        "- send",
        "For send only: type SEND_CONTROLLED_LEAD",
        "expected_notification:",
        "sent",
        "disabled",
        "any",
        "issues: write",
        "validate:",
        "HAS_PARKET_SMOKE_CONTACT: ${{ secrets.PARKET_SMOKE_CONTACT != '' }}",
        "HAS_PARKET_HEALTHCHECK_TOKEN: ${{ secrets.PARKET_HEALTHCHECK_TOKEN != '' }}",
        "python tools/check_controlled_smoke_github_secrets.py",
        "name: controlled-lead-smoke-secret-readiness",
        "No production lead was created because operation was validate-only.",
        "smoke:",
        "if: inputs.operation == 'send'",
        "needs: validate",
        "environment: production",
        "PARKET_SMOKE_CONTACT: ${{ secrets.PARKET_SMOKE_CONTACT }}",
        "PARKET_HEALTHCHECK_TOKEN: ${{ secrets.PARKET_HEALTHCHECK_TOKEN }}",
        'if [ "$GITHUB_REF" != "refs/heads/main" ]',
        "uses: actions/checkout@v7",
        "persist-credentials: false",
        "uses: actions/setup-python@v6",
        'python-version: "3.12"',
        "name: controlled-lead-smoke-final-secret-readiness",
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
    SECRET_CHECKER: (
        "GitHub secret readiness for controlled production lead smoke",
        '("PARKET_SMOKE_CONTACT", "has_smoke_contact")',
        '("PARKET_HEALTHCHECK_TOKEN", "has_healthcheck_token")',
        "configured/missing booleans only",
        "never reads, prints, hashes, measures or stores secret values",
        "--has-smoke-contact",
        "--has-healthcheck-token",
        "--self-test",
    ),
    DOC: (
        "Controlled production lead smoke",
        "validate-only",
        "operation=send",
        "controlled-lead-smoke-secret-readiness",
        "controlled-lead-smoke-final-secret-readiness",
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
    "default: send",
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

    if workflow.count("PARKET_SMOKE_CONTACT: ${{ secrets.PARKET_SMOKE_CONTACT }}") != 1:
        findings.append("controlled smoke workflow must expose PARKET_SMOKE_CONTACT to the send job exactly once")
    if workflow.count("PARKET_HEALTHCHECK_TOKEN: ${{ secrets.PARKET_HEALTHCHECK_TOKEN }}") != 1:
        findings.append("controlled smoke workflow must expose PARKET_HEALTHCHECK_TOKEN to the send job exactly once")
    if workflow.count("HAS_PARKET_SMOKE_CONTACT: ${{ secrets.PARKET_SMOKE_CONTACT != '' }}") != 2:
        findings.append("controlled smoke workflow must check the smoke contact before and after approval")
    if workflow.count("HAS_PARKET_HEALTHCHECK_TOKEN: ${{ secrets.PARKET_HEALTHCHECK_TOKEN != '' }}") != 2:
        findings.append("controlled smoke workflow must check the health token before and after approval")
    if "PARKET_SMOKE_CONTACT" in workflow.split("inputs:", 1)[-1].split("permissions:", 1)[0]:
        findings.append("PARKET_SMOKE_CONTACT must never be accepted as a workflow input")

    if "\n  validate:" not in workflow or "\n  smoke:" not in workflow:
        findings.append("controlled smoke workflow must separate validate and smoke jobs")
        validate_job = ""
        smoke_job = ""
    else:
        validate_job = workflow.split("\n  validate:", 1)[1].split("\n  smoke:", 1)[0]
        smoke_job = workflow.split("\n  smoke:", 1)[1]

    if "environment: production" in validate_job:
        findings.append("validate-only job must not require the production environment")
    if "tools/run_controlled_lead_smoke.py" in validate_job:
        findings.append("validate-only job must never create a production lead")
    validate_upload = validate_job.find("name: controlled-lead-smoke-secret-readiness")
    validate_stop = validate_job.find("Stop when controlled smoke secret readiness failed")
    if validate_upload < 0 or validate_stop < 0 or validate_upload > validate_stop:
        findings.append("validate-only job must upload secret readiness before failing")

    if "if: inputs.operation == 'send'" not in smoke_job or "needs: validate" not in smoke_job:
        findings.append("send job must run only after successful validation")
    final_upload = smoke_job.find("name: controlled-lead-smoke-final-secret-readiness")
    final_stop = smoke_job.find("Stop before controlled lead when final secret readiness failed")
    send_command = smoke_job.find("python tools/run_controlled_lead_smoke.py")
    if min(final_upload, final_stop, send_command) < 0 or not (final_upload < final_stop < send_command):
        findings.append("send job must upload and enforce final secret readiness before creating a lead")

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

    for self_test_path, label in (
        (SCRIPT, "controlled lead smoke"),
        (SECRET_CHECKER, "controlled smoke GitHub secret readiness"),
    ):
        if self_test_path.is_file():
            error = run_self_test(self_test_path)
            if error:
                findings.append(f"{label} self-test failed: {error}")

    if findings:
        print("Controlled lead smoke findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Controlled production lead smoke passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
