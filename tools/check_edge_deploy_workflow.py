#!/usr/bin/env python3
"""Validate the fail-closed manual production Edge Function deployment workflow."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-lead-function.yml"
SUPABASE_CONFIG = ROOT / "supabase" / "config.toml"
READINESS = ROOT / "tools" / "check_edge_deploy_readiness.py"
GITHUB_SECRETS = ROOT / "tools" / "check_edge_github_secrets.py"
DOC = ROOT / "docs" / "production-edge-deploy.md"

REQUIRED_MARKERS = {
    WORKFLOW: (
        "name: Deploy production lead function",
        "workflow_dispatch:",
        "operation:",
        'description: "Validate readiness only or deploy after validation"',
        "default: validate-only",
        "- validate-only",
        "- deploy",
        'description: "For deploy only: type DEPLOY_PARKET_PUBLIC_LEAD"',
        "required: false",
        'default: ""',
        "DEPLOY_PARKET_PUBLIC_LEAD",
        "notification_policy:",
        "require-configured",
        "allow-disabled",
        "issues: write",
        "validate production readiness",
        "deploy and verify production functions",
        "needs: validate",
        "if: inputs.operation == 'deploy'",
        "environment: production",
        "SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}",
        "SUPABASE_PROJECT_ID: ${{ secrets.SUPABASE_PROJECT_ID }}",
        "PARKET_HEALTHCHECK_TOKEN: ${{ secrets.PARKET_HEALTHCHECK_TOKEN }}",
        "HAS_SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN != '' }}",
        "HAS_SUPABASE_PROJECT_ID: ${{ secrets.SUPABASE_PROJECT_ID != '' }}",
        "HAS_PARKET_HEALTHCHECK_TOKEN: ${{ secrets.PARKET_HEALTHCHECK_TOKEN != '' }}",
        "OPERATION: ${{ inputs.operation }}",
        'if [ "$GITHUB_REF" != "refs/heads/main" ]',
        'if [ "$OPERATION" = "deploy" ]',
        "Validate operation and confirmation",
        "Revalidate deploy confirmation",
        "Check GitHub secret readiness",
        "Recheck GitHub secret readiness after approval",
        "python tools/check_edge_github_secrets.py",
        "--has-supabase-access-token",
        "--has-supabase-project-id",
        "--has-healthcheck-token",
        "edge-github-secret-readiness",
        "edge-deploy-final-github-secrets",
        "uses: actions/checkout@v7",
        "persist-credentials: false",
        "uses: actions/setup-python@v6",
        'python-version: "3.12"',
        "uses: denoland/setup-deno@v2",
        "deno-version: lts",
        "supabase/setup-cli@3c2f5e2ae34c34e428e8e206e2c4d21fa2d20fbf",
        "version: latest",
        "Test controlled lead verifier request ID",
        "Type-check controlled lead verifier",
        "supabase secrets list --project-ref",
        "--output json > remote-secret-names.json",
        "python tools/check_edge_deploy_readiness.py",
        "--notification-policy",
        "rm -f remote-secret-names.json",
        "name: edge-deploy-readiness",
        "Finish validate-only readiness",
        "inputs.operation == 'validate-only'",
        "No Edge Function was deployed because operation was validate-only.",
        "Revalidate deployment readiness after approval",
        "edge-deploy-final-readiness",
        "Deploy controlled lead verifier",
        "supabase functions deploy parket-lead-verify",
        "Deploy parket-public-lead",
        "supabase functions deploy parket-public-lead",
        "--use-api",
        "--no-verify-jwt",
        "python tools/check_public_lead_preflight.py",
        "python tools/check_production_lead_endpoint.py",
        "--require-token",
        "name: edge-deploy-post-checks",
        "failure --kind preflight",
        "success --kind preflight",
        "failure --kind protected",
        "success --kind protected",
        "gh issue comment 373",
        "Both Edge Functions deployed",
    ),
    SUPABASE_CONFIG: (
        'project_id = "parket36-site"',
        "[functions.parket-public-lead]",
        "[functions.parket-lead-verify]",
        "verify_jwt = false",
    ),
    READINESS: (
        "PARKET_IP_HASH_SALT",
        "PARKET_HEALTHCHECK_TOKEN",
        "PARKET_TELEGRAM_BOT_TOKEN",
        "PARKET_TELEGRAM_CHAT_ID",
        "PARKET_RESEND_API_KEY",
        "PARKET_EMAIL_FROM",
        "PARKET_EMAIL_TO",
        "SUPABASE_PROJECT_ID mismatch",
        "parket-public-lead",
        "parket-lead-verify",
        "function_config_has_public_mode",
        "verify_jwt = false",
        "allow-disabled",
        "This report contains secret names only",
        "--self-test",
    ),
    GITHUB_SECRETS: (
        "SUPABASE_ACCESS_TOKEN",
        "SUPABASE_PROJECT_ID",
        "PARKET_HEALTHCHECK_TOKEN",
        "configured/missing booleans only",
        "never reads, prints, hashes or stores secret values",
        "--has-supabase-access-token",
        "--has-supabase-project-id",
        "--has-healthcheck-token",
        "--self-test",
    ),
    DOC: (
        "Deploy production lead function",
        "validate-only",
        "режим по умолчанию",
        "ничего не развёртывает",
        "operation",
        "readiness-job",
        "deploy-job",
        "required reviewer",
        "edge-github-secret-readiness",
        "edge-deploy-final-github-secrets",
        "configured/missing",
        "parket-public-lead",
        "parket-lead-verify",
        "SUPABASE_ACCESS_TOKEN",
        "SUPABASE_PROJECT_ID",
        "PARKET_HEALTHCHECK_TOKEN",
        "PARKET_IP_HASH_SALT",
        "environment `production`",
        "DEPLOY_PARKET_PUBLIC_LEAD",
        "require-configured",
        "allow-disabled",
        "supabase secrets list",
        "--use-api",
        "--no-verify-jwt",
        "edge-deploy-readiness",
        "edge-deploy-final-readiness",
        "edge-deploy-post-checks",
        "контролируемая реальная заявка",
    ),
}

FORBIDDEN_WORKFLOW_MARKERS = (
    "  push:",
    "  pull_request:",
    "  schedule:",
    "default: deploy",
    "permissions: write-all",
    "set -x",
    'echo "$SUPABASE_ACCESS_TOKEN"',
    'echo "$PARKET_HEALTHCHECK_TOKEN"',
    "path: remote-secret-names.json",
    "--prune",
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
            findings.append(f"deploy workflow contains forbidden marker: {marker}")

    exact_secret_lines = (
        "SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}",
        "SUPABASE_PROJECT_ID: ${{ secrets.SUPABASE_PROJECT_ID }}",
        "PARKET_HEALTHCHECK_TOKEN: ${{ secrets.PARKET_HEALTHCHECK_TOKEN }}",
        "HAS_SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN != '' }}",
        "HAS_SUPABASE_PROJECT_ID: ${{ secrets.SUPABASE_PROJECT_ID != '' }}",
        "HAS_PARKET_HEALTHCHECK_TOKEN: ${{ secrets.PARKET_HEALTHCHECK_TOKEN != '' }}",
    )
    for line in exact_secret_lines:
        if workflow.count(line) != 2:
            findings.append(f"readiness and deploy jobs must each contain exact secret marker: {line}")

    inputs_block_start = workflow.find("workflow_dispatch:")
    inputs_block_end = workflow.find("\npermissions:")
    inputs_block = workflow[inputs_block_start:inputs_block_end]
    operation_position = inputs_block.find("operation:")
    confirm_position = inputs_block.find("confirm:")
    notification_position = inputs_block.find("notification_policy:")
    if min(operation_position, confirm_position, notification_position) < 0:
        findings.append("workflow inputs must include operation, confirm and notification_policy")
    elif not (operation_position < confirm_position < notification_position):
        findings.append("workflow inputs must keep operation before confirm and notification_policy")

    confirm_block = inputs_block[confirm_position:notification_position] if confirm_position >= 0 else ""
    if "required: false" not in confirm_block:
        findings.append("deploy confirmation must be optional for validate-only runs")

    validate_start = workflow.find("\n  validate:\n")
    deploy_start = workflow.find("\n  deploy:\n")
    if validate_start < 0 or deploy_start < 0 or validate_start > deploy_start:
        findings.append("workflow must keep readiness job before deploy job")
        validate_block = ""
        deploy_block = ""
    else:
        validate_block = workflow[validate_start:deploy_start]
        deploy_block = workflow[deploy_start:]

    if "environment: production" in validate_block:
        findings.append("validate-only readiness job must not require the production environment")
    if "supabase functions deploy" in validate_block:
        findings.append("validate-only readiness job must not contain deployment commands")
    if "Finish validate-only readiness" not in validate_block:
        findings.append("validate job must include an explicit validate-only completion step")
    if "edge-github-secret-readiness" not in validate_block:
        findings.append("validate job must upload GitHub secret readiness before Supabase checks")

    github_check_position = validate_block.find("Check GitHub secret readiness")
    github_upload_position = validate_block.find("Upload GitHub secret readiness report")
    github_stop_position = validate_block.find("Stop when GitHub secret readiness failed")
    cli_position = validate_block.find("Set up Supabase CLI")
    if min(github_check_position, github_upload_position, github_stop_position, cli_position) < 0:
        findings.append("validate job is missing GitHub secret readiness stages")
    elif not (github_check_position < github_upload_position < github_stop_position < cli_position):
        findings.append("GitHub secret report must be uploaded and enforced before Supabase CLI")

    if "if: inputs.operation == 'deploy'" not in deploy_block:
        findings.append("deploy job must be guarded by operation == deploy")
    if "needs: validate" not in deploy_block:
        findings.append("deploy job must depend on successful readiness validation")
    if "environment: production" not in deploy_block:
        findings.append("deploy job must use the protected production environment")
    if "Revalidate deploy confirmation" not in deploy_block:
        findings.append("deploy job must revalidate confirmation after environment approval")
    if "Recheck GitHub secret readiness after approval" not in deploy_block:
        findings.append("deploy job must recheck GitHub secret presence after environment approval")
    if "Revalidate deployment readiness after approval" not in deploy_block:
        findings.append("deploy job must repeat remote readiness checks after approval")

    final_github_check = deploy_block.find("Recheck GitHub secret readiness after approval")
    final_github_upload = deploy_block.find("Upload final GitHub secret readiness report")
    final_github_stop = deploy_block.find("Stop before deploy when final GitHub secret readiness failed")
    final_cli = deploy_block.find("Set up Supabase CLI")
    if min(final_github_check, final_github_upload, final_github_stop, final_cli) < 0:
        findings.append("deploy job is missing final GitHub secret readiness stages")
    elif not (final_github_check < final_github_upload < final_github_stop < final_cli):
        findings.append("final GitHub secret report must be uploaded and enforced before Supabase CLI")

    readiness_position = workflow.find("Validate deployment readiness")
    validate_only_position = workflow.find("Finish validate-only readiness")
    final_readiness_position = workflow.find("Revalidate deployment readiness after approval")
    verifier_position = workflow.find("Deploy controlled lead verifier")
    public_position = workflow.find("Deploy parket-public-lead")
    preflight_position = workflow.find("Run public endpoint preflight")
    protected_position = workflow.find("Run protected production healthcheck")
    if min(readiness_position, validate_only_position, final_readiness_position, verifier_position, public_position, preflight_position, protected_position) < 0:
        findings.append("deploy workflow is missing one or more required readiness or deployment stages")
    elif not (
        readiness_position
        < validate_only_position
        < final_readiness_position
        < verifier_position
        < public_position
        < preflight_position
    ):
        findings.append("workflow order must be readiness, validate-only finish, final readiness, verifier, public lead, preflight")
    if protected_position < public_position:
        findings.append("protected healthcheck must run after both deployments")

    config = texts.get(SUPABASE_CONFIG, "")
    if config.count("verify_jwt = false") != 2:
        findings.append("supabase/config.toml must set verify_jwt = false exactly for both functions")

    for path, label in (
        (READINESS, "edge deploy readiness"),
        (GITHUB_SECRETS, "GitHub secret readiness"),
    ):
        if path.is_file():
            error = run_self_test(path)
            if error:
                findings.append(f"{label} self-test failed: {error}")

    if findings:
        print("Edge deploy workflow findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Edge deploy workflow passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
