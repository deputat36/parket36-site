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
DOC = ROOT / "docs" / "production-edge-deploy.md"

REQUIRED_MARKERS = {
    WORKFLOW: (
        "name: Deploy production lead function",
        "workflow_dispatch:",
        "DEPLOY_PARKET_PUBLIC_LEAD",
        "notification_policy:",
        "require-configured",
        "allow-disabled",
        "issues: write",
        "environment: production",
        "SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}",
        "SUPABASE_PROJECT_ID: ${{ secrets.SUPABASE_PROJECT_ID }}",
        "PARKET_HEALTHCHECK_TOKEN: ${{ secrets.PARKET_HEALTHCHECK_TOKEN }}",
        'if [ "$GITHUB_REF" != "refs/heads/main" ]',
        "uses: actions/checkout@v7",
        "persist-credentials: false",
        "uses: actions/setup-python@v6",
        'python-version: "3.12"',
        "uses: denoland/setup-deno@v2",
        "deno-version: lts",
        "supabase/setup-cli@3c2f5e2ae34c34e428e8e206e2c4d21fa2d20fbf",
        "version: latest",
        "supabase secrets list --project-ref",
        "--output json > remote-secret-names.json",
        "python tools/check_edge_deploy_readiness.py",
        "--notification-policy",
        "rm -f remote-secret-names.json",
        "name: edge-deploy-readiness",
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
    ),
    SUPABASE_CONFIG: (
        'project_id = "parket36-site"',
        "[functions.parket-public-lead]",
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
        "verify_jwt = false",
        "allow-disabled",
        "This report contains secret names only",
        "--self-test",
    ),
    DOC: (
        "Deploy production lead function",
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
        "edge-deploy-post-checks",
        "контролируемая реальная заявка",
    ),
}

FORBIDDEN_WORKFLOW_MARKERS = (
    "  push:",
    "  pull_request:",
    "  schedule:",
    "permissions: write-all",
    "set -x",
    'echo "$SUPABASE_ACCESS_TOKEN"',
    'echo "$PARKET_HEALTHCHECK_TOKEN"',
    "path: remote-secret-names.json",
    "--prune",
)


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

    if workflow.count("secrets.SUPABASE_ACCESS_TOKEN") != 1:
        findings.append("deploy workflow must reference SUPABASE_ACCESS_TOKEN exactly once through secrets")
    if workflow.count("secrets.SUPABASE_PROJECT_ID") != 1:
        findings.append("deploy workflow must reference SUPABASE_PROJECT_ID exactly once through secrets")
    if workflow.count("secrets.PARKET_HEALTHCHECK_TOKEN") != 1:
        findings.append("deploy workflow must reference PARKET_HEALTHCHECK_TOKEN exactly once through secrets")

    readiness_position = workflow.find("Validate deployment readiness")
    deploy_position = workflow.find("Deploy parket-public-lead")
    preflight_position = workflow.find("Run public endpoint preflight")
    protected_position = workflow.find("Run protected production healthcheck")
    if readiness_position < 0 or deploy_position < 0 or readiness_position > deploy_position:
        findings.append("readiness validation must run before deploy")
    if deploy_position < 0 or preflight_position < deploy_position or protected_position < deploy_position:
        findings.append("public and protected checks must run after deploy")

    if READINESS.is_file():
        completed = subprocess.run(
            [sys.executable, str(READINESS), "--self-test"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stdout + completed.stderr).strip() or "unknown self-test error"
            findings.append("edge deploy readiness self-test failed: " + detail)

    if findings:
        print("Edge deploy workflow findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Edge deploy workflow passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
