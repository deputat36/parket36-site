#!/usr/bin/env python3
"""Validate the shared quality gate composition."""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "tools" / "run_quality_checks.py"

EXPECTED_CHECKS = [
    ["tools/site_settings.py", "--check"],
    ["tools/check_domain_settings.py"],
    ["tools/check_workflows.py"],
    ["tools/check_quality_runner.py"],
    ["tools/check_docs.py"],
    ["tools/build_campaign_links.py", "--check"],
    ["tools/build_local_profile_kit.py", "--check"],
    ["tools/check_direct_callback_campaign.py"],
    ["tools/deployment_manifest.py", "--self-test"],
    ["tools/check_live_deployment.py", "--self-test"],
    ["tools/check_post_deploy_verification.py"],
    ["tools/complete_pages_switch_issue.py", "--self-test"],
    ["tools/check_lead_endpoint_monitoring.py"],
    ["tools/check_edge_deploy_workflow.py"],
    ["tools/check_controlled_lead_smoke.py"],
    ["tools/check_production_lead_launch_readiness.py"],
    ["tools/check_production_lead_readiness_staleness.py"],
    ["tools/check_analytics_privacy.py"],
    ["tools/check_js_assets.py"],
    ["tools/check_shared_shell_coverage.py"],
    ["tools/check_content_inventory.py"],
    ["tools/check_content_similarity.py"],
    ["tools/check_internal_link_map.py"],
    ["tools/check_structured_data.py"],
    ["tools/check_breadcrumb_schema.py"],
    ["tools/check_generated_sitemap.py"],
    ["tools/check_sitemap_helper.py"],
    ["tools/check_og_cards.py"],
    ["tools/check_image_attributes.py"],
    ["tools/check_live_site.py", "--self-test"],
    ["tools/check_live_conversion_workflow.py"],
    ["tools/check_supabase_retention.py"],
    ["tools/check_empty_link_attributes.py"],
    ["tools/check_site.py"],
    ["tools/check_guardrails.py"],
    ["tools/check_conversion_paths.py"],
    ["tools/check_commercial_pages.py"],
    ["tools/check_callback_topic_context.py"],
    ["tools/check_home_callback_links.py"],
    ["tools/check_lead_paths.py"],
    ["tools/check_lead_reliability.py"],
    ["tools/check_lead_notification_feedback.py"],
    ["tools/check_payload_shape.py"],
    ["tools/check_indexnow_workflow.py"],
    ["tools/submit_indexnow.py", "--check"],
    ["tools/build_pages.py"],
]


def extract_checks() -> list[list[str]]:
    tree = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if "CHECKS" not in names:
                continue

            checks: list[list[str]] = []
            for item in ast.literal_eval(node.value):
                if not isinstance(item, tuple) or len(item) != 2:
                    raise ValueError("CHECKS entries must be (title, args) tuples")
                title, args = item
                if not isinstance(title, str) or not isinstance(args, list):
                    raise ValueError("CHECKS entries must use a string title and list args")
                if not all(isinstance(arg, str) for arg in args):
                    raise ValueError("CHECKS args must contain only strings")
                checks.append(args)
            return checks

    raise ValueError("CHECKS assignment is missing")


def main() -> int:
    findings: list[str] = []

    try:
        checks = extract_checks()
    except (SyntaxError, ValueError) as exc:
        print(f"Quality runner parse error: {exc}")
        return 1

    if checks != EXPECTED_CHECKS:
        findings.append("tools/run_quality_checks.py must keep the approved quality gate order")
        findings.append(f"expected: {EXPECTED_CHECKS}")
        findings.append(f"actual:   {checks}")

    seen: set[str] = set()
    for args in checks:
        script = args[0]
        if script in seen:
            findings.append(f"duplicate quality check: {script}")
        seen.add(script)

        script_path = ROOT / script
        if not script_path.exists():
            findings.append(f"quality check script is missing: {script}")

    if findings:
        print("Quality runner findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Quality runner check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
