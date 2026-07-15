#!/usr/bin/env python3
"""Validate the unified non-mutating production lead launch readiness workflow."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "production-lead-launch-readiness.yml"
BUILDER = ROOT / "tools" / "build_production_lead_launch_readiness.py"
STAMPER = ROOT / "tools" / "stamp_production_lead_launch_readiness.py"
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
        "contents: read",
        "issues: write",
        "HAS_SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN != '' }}",
        "HAS_SUPABASE_PROJECT_ID: ${{ secrets.SUPABASE_PROJECT_ID != '' }}",
        "HAS_PARKET_HEALTHCHECK_TOKEN: ${{ secrets.PARKET_HEALTHCHECK_TOKEN != '' }}",
        "HAS_PARKET_SMOKE_CONTACT: ${{ secrets.PARKET_SMOKE_CONTACT != '' }}",
        "Verify Edge Function sources",
        "Check deploy GitHub secret readiness",
        "Check controlled smoke GitHub secret readiness",
        "Check current public production contract",
        "Read remote Supabase secret names",
        "Check remote Supabase readiness",
        "rm -f remote-secret-names.json",
        "Build unified readiness summary",
        "Stamp readiness source commit",
        "python tools/stamp_production_lead_launch_readiness.py",
        '--commit-sha "$GITHUB_SHA"',
        "Upload unified readiness artifact",
        "name: production-lead-launch-readiness",
        "Update issue 373 readiness snapshot",
        "steps.stamp.outcome == 'success'",
        "python tools/manage_production_lead_launch_readiness.py",
        "Fail when launch prerequisites are blocked",
        "steps.summary.outcome == 'failure' || steps.stamp.outcome == 'failure'",
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
    STAMPER: (
        "Source commit:",
        "Snapshot validity:",
        "exactly 40 lowercase hexadecimal characters",
        "rerun after any change to `main`",
        "--commit-sha",
        "--report",
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
        "Source commit",
        "только для указанного коммита",
        "повторить readiness после любого изменения `main`",
        "stamp_production_lead_launch_readiness.py --self-test",
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
        findings.append("workflow must grant issues: write exactly once")
    if workflow.count("SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}") != 1:
        findings.append("workflow must expose SUPABASE_ACCESS_TOKEN only once for read-only CLI access")
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

    inputs_block = block(workflow, "workflow_dispatch:", "\npermissions:")
    if "PARKET_SMOKE_CONTACT" in inputs_block or "PARKET_HEALTHCHECK_TOKEN" in inputs_block:
        findings.append("protected smoke values must never be accepted as workflow inputs")

    stage_names = (
        "Verify Edge Function sources",
        "Check deploy GitHub secret readiness",
        "Check controlled smoke GitHub secret readiness",
        "Check current public production contract",
        "Read remote Supabase secret names",
        "Check remote Supabase readiness",
        "Remove temporary remote secret list",
        "Build unified readiness summary",
        "Stamp readiness source commit",
        "Upload unified readiness artifact",
        "Update issue 373 readiness snapshot",
        "Fail when launch prerequisites are blocked",
    )
    positions = [workflow.find(name) for name in stage_names]
    if any(position < 0 for position in positions):
        findings.append("workflow is missing one or more required readiness stages")
    elif positions != sorted(positions):
        findings.append("workflow stages must preserve safe source, cleanup, summary, stamp, artifact, issue and fail order")

    raw_path_position = workflow.find("remote-secret-names.json")
    cleanup_position = workflow.find("rm -f remote-secret-names.json")
    upload_position = workflow.find("Upload unified readiness artifact")
    if min(raw_path_position, cleanup_position, upload_position) < 0 or not (
        raw_path_position < cleanup_position < upload_position
    ):
        findings.append("temporary remote secret names must be removed before artifact upload")

    stamp_block = block(workflow, "- name: Stamp readiness source commit", "- name: Upload unified readiness artifact")
    for marker in (
        "id: stamp",
        "if: always()",
        "continue-on-error: true",
        "python tools/stamp_production_lead_launch_readiness.py",
        '--commit-sha "$GITHUB_SHA"',
        "--report production-lead-launch-readiness.md",
    ):
        if marker not in stamp_block:
            findings.append(f"commit stamp step must contain: {marker}")

    issue_block = block(workflow, "- name: Update issue 373 readiness snapshot", "- name: Fail when launch prerequisites are blocked")
    for marker in (
        "if: always() && steps.stamp.outcome == 'success'",
        "continue-on-error: true",
        "GITHUB_TOKEN: ${{ github.token }}",
        "--report production-lead-launch-readiness.md",
    ):
        if marker not in issue_block:
            findings.append(f"issue 373 snapshot step must contain: {marker}")
    for forbidden in (
        "edge-github-secret-readiness.md",
        "edge-deploy-readiness.md",
        "controlled-lead-smoke-secret-readiness.md",
        "lead-endpoint-preflight.md",
    ):
        if forbidden in issue_block:
            findings.append(f"issue snapshot must publish only unified summary, not: {forbidden}")

    fail_block = workflow[workflow.find("- name: Fail when launch prerequisites are blocked") :]
    if "steps.summary.outcome == 'failure' || steps.stamp.outcome == 'failure'" not in fail_block:
        findings.append("workflow must fail when summary building or commit stamping fails")

    for path in (BUILDER, STAMPER, ISSUE_MANAGER):
        text = texts.get(path, "")
        for forbidden in (
            "PARKET_SMOKE_CONTACT =",
            "PARKET_HEALTHCHECK_TOKEN =",
            "SUPABASE_ACCESS_TOKEN =",
            "print(contact)",
            "print(token)",
        ):
            if forbidden in text:
                findings.append(f"{path.relative_to(ROOT)} contains protected-data marker: {forbidden}")

    manager = texts.get(ISSUE_MANAGER, "")
    for forbidden in (
        "edge-github-secret-readiness.md",
        "edge-deploy-readiness.md",
        "controlled-lead-smoke-secret-readiness.md",
        "lead-endpoint-preflight.md",
    ):
        if forbidden in manager:
            findings.append(f"issue manager contains forbidden component report marker: {forbidden}")

    for self_test_path, label in (
        (BUILDER, "production lead launch readiness"),
        (STAMPER, "production lead readiness commit stamp"),
        (ISSUE_MANAGER, "production lead readiness issue manager"),
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
