#!/usr/bin/env python3
"""Validate the unified non-mutating production lead launch readiness workflow."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "production-lead-launch-readiness.yml"
BUILDER = ROOT / "tools" / "build_production_lead_launch_readiness.py"
ISSUE_MANAGER = ROOT / "tools" / "manage_production_lead_launch_readiness.py"
DOC = ROOT / "docs" / "production-lead-launch-readiness.md"
RUNNER = ROOT / "tools" / "run_quality_checks.py"
QUALITY_CHECKER = ROOT / "tools" / "check_quality_runner.py"

REQUIRED_MARKERS = {
    WORKFLOW: (
        "name: Production lead launch readiness",
        "workflow_dispatch:",
        "notification_policy:",
        "require-configured",
        "allow-disabled",
        "permissions:",
        "contents: read",
        "issues: write",
        "build unified production lead readiness",
        "HAS_SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN != '' }}",
        "HAS_SUPABASE_PROJECT_ID: ${{ secrets.SUPABASE_PROJECT_ID != '' }}",
        "HAS_PARKET_HEALTHCHECK_TOKEN: ${{ secrets.PARKET_HEALTHCHECK_TOKEN != '' }}",
        "HAS_PARKET_SMOKE_CONTACT: ${{ secrets.PARKET_SMOKE_CONTACT != '' }}",
        "Verify Edge Function sources",
        "Check deploy GitHub secret readiness",
        "python tools/check_edge_github_secrets.py",
        "Check controlled smoke GitHub secret readiness",
        "python tools/check_controlled_smoke_github_secrets.py",
        "Check current public production contract",
        "python tools/check_public_lead_preflight.py",
        "Set up Supabase CLI",
        "steps.deploy_github.outcome == 'success'",
        "supabase secrets list --project-ref",
        "--output json > remote-secret-names.json",
        "Check remote Supabase readiness",
        "steps.remote_names.outcome == 'success'",
        "python tools/check_edge_deploy_readiness.py",
        "rm -f remote-secret-names.json",
        "Build unified readiness summary",
        "python tools/build_production_lead_launch_readiness.py",
        "steps.source_checks.outcome",
        "steps.deploy_github.outcome",
        "steps.remote_readiness.outcome",
        "steps.smoke_github.outcome",
        "steps.preflight.outcome",
        "Upload unified readiness artifact",
        "name: production-lead-launch-readiness",
        "production-lead-launch-readiness.md",
        "edge-github-secret-readiness.md",
        "edge-deploy-readiness.md",
        "controlled-lead-smoke-secret-readiness.md",
        "lead-endpoint-preflight.md",
        "Update issue 373 readiness snapshot",
        "GITHUB_TOKEN: ${{ github.token }}",
        "python tools/manage_production_lead_launch_readiness.py",
        "Fail when launch prerequisites are blocked",
        "steps.summary.outcome == 'failure'",
    ),
    BUILDER: (
        "Production lead launch readiness",
        "BLOCKED",
        "DEPLOY_READY",
        "LAUNCH_READY",
        "PRODUCTION_CONTRACT_CURRENT",
        "source_verification",
        "github_deploy_secrets",
        "remote_supabase_readiness",
        "github_controlled_smoke_secrets",
        "current_production_contract",
        "HTTP OPTIONS only",
        "never contains secret values",
        "does not deploy an Edge Function",
        "--source-status",
        "--deploy-github-status",
        "--remote-readiness-status",
        "--smoke-github-status",
        "--preflight-status",
        "--self-test",
    ),
    ISSUE_MANAGER: (
        "ISSUE_NUMBER = 373",
        "parket36-production-lead-launch-readiness",
        "Production lead launch readiness",
        "Readiness level:",
        "This summary never contains secret values",
        "component reports остаются",
        "find_managed_comment",
        "PATCH",
        "--report",
        "--self-test",
    ),
    DOC: (
        "Production lead launch readiness",
        "BLOCKED",
        "DEPLOY_READY",
        "LAUNCH_READY",
        "PRODUCTION_CONTRACT_CURRENT",
        "PARKET_SMOKE_CONTACT",
        "PARKET_HEALTHCHECK_TOKEN",
        "HTTP `OPTIONS`",
        "не развёртывает Edge Functions",
        "не создаёт заявку",
        "remote-secret-names.json",
        "issue #373",
        "один служебный комментарий",
        "component reports",
        "manage_production_lead_launch_readiness.py --self-test",
        "issue #375",
    ),
    RUNNER: (
        '"Validate production lead launch readiness", ["tools/check_production_lead_launch_readiness.py"]',
    ),
    QUALITY_CHECKER: (
        '["tools/check_production_lead_launch_readiness.py"]',
    ),
}

FORBIDDEN_WORKFLOW_MARKERS = (
    "  push:",
    "  pull_request:",
    "  schedule:",
    "environment: production",
    "permissions: write-all",
    "supabase functions deploy",
    "tools/run_controlled_lead_smoke.py",
    "tools/check_production_lead_endpoint.py",
    "PARKET_HEALTHCHECK_TOKEN: ${{ secrets.PARKET_HEALTHCHECK_TOKEN }}",
    "PARKET_SMOKE_CONTACT: ${{ secrets.PARKET_SMOKE_CONTACT }}",
    "path: remote-secret-names.json",
    "set -x",
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
            findings.append(f"launch readiness workflow contains forbidden marker: {marker}")

    if workflow.count("issues: write") != 1:
        findings.append("workflow must grant issues: write exactly once for the managed issue 373 snapshot")
    if workflow.count("SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}") != 1:
        findings.append("workflow must expose SUPABASE_ACCESS_TOKEN only once for read-only Supabase CLI access")
    if workflow.count("SUPABASE_PROJECT_ID: ${{ secrets.SUPABASE_PROJECT_ID }}") != 1:
        findings.append("workflow must expose SUPABASE_PROJECT_ID only once")

    for marker in (
        "HAS_SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN != '' }}",
        "HAS_SUPABASE_PROJECT_ID: ${{ secrets.SUPABASE_PROJECT_ID != '' }}",
        "HAS_PARKET_HEALTHCHECK_TOKEN: ${{ secrets.PARKET_HEALTHCHECK_TOKEN != '' }}",
        "HAS_PARKET_SMOKE_CONTACT: ${{ secrets.PARKET_SMOKE_CONTACT != '' }}",
    ):
        if workflow.count(marker) != 1:
            findings.append(f"workflow must contain exact boolean secret marker once: {marker}")

    input_start = workflow.find("workflow_dispatch:")
    input_end = workflow.find("\npermissions:")
    inputs_block = workflow[input_start:input_end]
    if "PARKET_SMOKE_CONTACT" in inputs_block or "PARKET_HEALTHCHECK_TOKEN" in inputs_block:
        findings.append("protected smoke values must never be accepted as workflow inputs")

    positions = {
        "source": workflow.find("Verify Edge Function sources"),
        "deploy_github": workflow.find("Check deploy GitHub secret readiness"),
        "smoke_github": workflow.find("Check controlled smoke GitHub secret readiness"),
        "preflight": workflow.find("Check current public production contract"),
        "remote_names": workflow.find("Read remote Supabase secret names"),
        "remote_readiness": workflow.find("Check remote Supabase readiness"),
        "remove_raw": workflow.find("Remove temporary remote secret list"),
        "summary": workflow.find("Build unified readiness summary"),
        "upload": workflow.find("Upload unified readiness artifact"),
        "issue_snapshot": workflow.find("Update issue 373 readiness snapshot"),
        "fail": workflow.find("Fail when launch prerequisites are blocked"),
    }
    if any(position < 0 for position in positions.values()):
        findings.append("workflow is missing one or more required launch readiness stages")
    elif not (
        positions["source"]
        < positions["deploy_github"]
        < positions["smoke_github"]
        < positions["preflight"]
        < positions["remote_names"]
        < positions["remote_readiness"]
        < positions["remove_raw"]
        < positions["summary"]
        < positions["upload"]
        < positions["issue_snapshot"]
        < positions["fail"]
    ):
        findings.append(
            "workflow stages must preserve safe source, secret, remote, cleanup, summary, upload, issue snapshot and fail order"
        )

    if "if: always()" not in workflow[positions.get("remove_raw", 0):positions.get("fail", len(workflow))]:
        findings.append("raw cleanup, summary, artifact and issue snapshot must remain available after earlier failures")

    setup_cli = workflow.find("Set up Supabase CLI")
    remote_names = workflow.find("Read remote Supabase secret names")
    if setup_cli < 0 or remote_names < 0 or setup_cli > remote_names:
        findings.append("Supabase CLI must be installed before reading remote secret names")

    raw_path_position = workflow.find("remote-secret-names.json")
    cleanup_position = workflow.find("rm -f remote-secret-names.json")
    upload_position = workflow.find("Upload unified readiness artifact")
    if min(raw_path_position, cleanup_position, upload_position) < 0 or not (
        raw_path_position < cleanup_position < upload_position
    ):
        findings.append("temporary remote secret names must be removed before artifact upload")

    issue_block_start = positions.get("issue_snapshot", -1)
    issue_block_end = positions.get("fail", -1)
    issue_block = workflow[issue_block_start:issue_block_end] if min(issue_block_start, issue_block_end) >= 0 else ""
    for marker in ("if: always()", "continue-on-error: true", "GITHUB_TOKEN: ${{ github.token }}"):
        if marker not in issue_block:
            findings.append(f"issue 373 snapshot step must contain: {marker}")
    for forbidden in (
        "edge-github-secret-readiness.md",
        "edge-deploy-readiness.md",
        "controlled-lead-smoke-secret-readiness.md",
        "lead-endpoint-preflight.md",
    ):
        if forbidden in issue_block:
            findings.append(f"issue snapshot must publish only unified summary, not component report: {forbidden}")

    builder = texts.get(BUILDER, "")
    for forbidden in (
        "PARKET_SMOKE_CONTACT =",
        "PARKET_HEALTHCHECK_TOKEN =",
        "SUPABASE_ACCESS_TOKEN =",
        "print(contact)",
        "print(token)",
    ):
        if forbidden in builder:
            findings.append(f"summary builder contains protected-data marker: {forbidden}")

    manager = texts.get(ISSUE_MANAGER, "")
    for forbidden in (
        "edge-github-secret-readiness.md",
        "edge-deploy-readiness.md",
        "controlled-lead-smoke-secret-readiness.md",
        "lead-endpoint-preflight.md",
        "PARKET_SMOKE_CONTACT =",
        "PARKET_HEALTHCHECK_TOKEN =",
        "SUPABASE_ACCESS_TOKEN =",
        "print(contact)",
        "print(token)",
    ):
        if forbidden in manager:
            findings.append(f"issue manager contains forbidden component or protected-data marker: {forbidden}")

    for self_test_path, label in (
        (BUILDER, "production lead launch readiness"),
        (ISSUE_MANAGER, "production lead launch readiness issue manager"),
    ):
        if self_test_path.is_file():
            error = run_self_test(self_test_path)
            if error:
                findings.append(f"{label} self-test failed: {error}")

    if findings:
        print("Production lead launch readiness findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Production lead launch readiness workflow passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
