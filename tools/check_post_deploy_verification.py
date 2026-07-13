#!/usr/bin/env python3
"""Validate automatic live verification after a successful GitHub Pages deploy."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
LIVE_WORKFLOW = ROOT / ".github" / "workflows" / "live-site-health.yml"
DEPLOYMENT_CHECKER = ROOT / "tools" / "check_live_deployment.py"
DEPLOYMENT_MANIFEST = ROOT / "tools" / "deployment_manifest.py"
PAGES_ISSUE_COMPLETER = ROOT / "tools" / "complete_pages_switch_issue.py"
ROOT_MANIFEST = ROOT / "deployment.json"

REQUIRED_MARKERS = {
    PAGES_WORKFLOW: {
        "run: python tools/deployment_manifest.py --write _site/deployment.json": "artifact-only manifest creation",
        'path: "_site"': "Pages artifact path",
        "uses: actions/deploy-pages@v5": "Pages deploy action",
    },
    LIVE_WORKFLOW: {
        "workflow_run:": "post-deploy trigger",
        'workflows: ["Deploy GitHub Pages"]': "Pages workflow dependency",
        "types: [completed]": "completed deploy trigger",
        "if: github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success'": "successful deploy condition",
        "group: live-site-health": "monitoring concurrency group",
        "ref: ${{ github.event_name == 'workflow_run' && github.event.workflow_run.head_sha || github.sha }}": "deployed SHA checkout",
        "EXPECTED_DEPLOY_SHA: ${{ github.event_name == 'workflow_run' && github.event.workflow_run.head_sha || '' }}": "expected deployment SHA",
        "EXPECTED_DEPLOY_RUN_ID: ${{ github.event_name == 'workflow_run' && github.event.workflow_run.id || '' }}": "expected deployment run ID",
        "DEPLOY_ATTEMPTS: ${{ github.event_name == 'workflow_run' && '6' || '1' }}": "post-deploy retry count",
        '--expected-sha "$EXPECTED_DEPLOY_SHA"': "expected SHA argument",
        '--expected-run-id "$EXPECTED_DEPLOY_RUN_ID"': "expected run ID argument",
        '--attempts "$DEPLOY_ATTEMPTS"': "retry attempts argument",
        "--retry-delay 10": "propagation retry delay",
        "- name: Complete Pages switch issue": "Pages issue completion step",
        "github.event_name == 'workflow_run' &&": "post-deploy-only issue completion",
        "steps.live_health.outcome == 'success' &&": "live-health success requirement",
        "steps.deployment_source.outcome == 'success'": "deployment source success requirement",
        "PAGES_DEPLOY_SHA: ${{ github.event.workflow_run.head_sha }}": "completed deploy SHA for issue comment",
        "PAGES_DEPLOY_RUN_ID: ${{ github.event.workflow_run.id }}": "completed deploy run ID for issue comment",
        "run: python tools/complete_pages_switch_issue.py": "Pages issue completer invocation",
    },
    DEPLOYMENT_CHECKER: {
        "def manifest_request_url(": "cache-busted URL helper",
        '"verify_commit": expected_sha or ""': "commit cache key",
        '"verify_run": expected_run_id or ""': "run cache key",
        '"attempt": str(attempt)': "per-attempt cache key",
        '"Cache-Control": "no-cache, no-store, max-age=0"': "no-cache request header",
        '"Pragma": "no-cache"': "legacy no-cache header",
        "def check_manifest_with_retry(": "retry helper",
        "request_url = manifest_request_url(": "cache-busted request use",
        "expected_sha": "expected SHA validation",
        "expected_run_id": "expected run ID validation",
        "stale or unexpected deployment": "stale deployment failure",
        "time.sleep(retry_delay)": "propagation wait",
        "MAX_ATTEMPTS = 6": "bounded retry count",
        'parser.add_argument("--expected-sha")': "expected SHA CLI",
        'parser.add_argument("--expected-run-id")': "expected run ID CLI",
        'parser.add_argument("--attempts", type=int, default=1)': "attempts CLI",
        "daily/manual manifest URL must remain canonical": "canonical URL self-test",
        "cache-busted manifest URL missing marker": "cache-busting self-test",
        "matching expected SHA and run ID must pass": "exact deployment self-test",
        "stale deployment SHA must fail": "stale SHA self-test",
    },
    DEPLOYMENT_MANIFEST: {
        '"publisher": "github-actions"': "GitHub Actions publisher",
        '"artifact": "_site"': "artifact identity",
        'os.environ.get("GITHUB_SHA", "local")': "commit provenance",
        'os.environ.get("GITHUB_RUN_ID", "local")': "workflow provenance",
    },
    PAGES_ISSUE_COMPLETER: {
        "ISSUE_NUMBER = 5": "fixed Pages switch issue",
        'EXPECTED_TITLE = "Переключить parket36.ru на GitHub Pages"': "issue title guard",
        'if event_name != "workflow_run"': "workflow_run safety guard",
        '"state": "closed", "state_reason": "completed"': "completed issue closure",
        "SHA и run ID live-сборки совпали": "exact deployment completion evidence",
        "Pages switch issue completer self-test passed": "self-test",
    },
}


def main() -> int:
    findings: list[str] = []

    if ROOT_MANIFEST.exists():
        findings.append("deployment.json must not exist in repository root")

    for path, markers in REQUIRED_MARKERS.items():
        if not path.is_file():
            findings.append(f"missing required file: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker, label in markers.items():
            if marker not in text:
                findings.append(f"{path.relative_to(ROOT)}: missing {label}: {marker}")

    if findings:
        print("Post-deploy verification findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Post-deploy verification check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
