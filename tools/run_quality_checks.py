#!/usr/bin/env python3
"""Run the full Parket36 quality gate used by CI and Pages deploy."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    ("Validate shared settings", ["tools/site_settings.py", "--check"]),
    ("Validate domain settings", ["tools/check_domain_settings.py"]),
    ("Validate workflow configuration", ["tools/check_workflows.py"]),
    ("Validate quality runner", ["tools/check_quality_runner.py"]),
    ("Validate operational docs", ["tools/check_docs.py"]),
    ("Validate campaign links", ["tools/build_campaign_links.py", "--check"]),
    ("Validate local profile kit", ["tools/build_local_profile_kit.py", "--check"]),
    ("Validate direct callback campaign", ["tools/check_direct_callback_campaign.py"]),
    ("Validate deployment manifest", ["tools/deployment_manifest.py", "--self-test"]),
    ("Validate live deployment source", ["tools/check_live_deployment.py", "--self-test"]),
    ("Validate post-deploy verification", ["tools/check_post_deploy_verification.py"]),
    ("Validate Pages issue completion", ["tools/complete_pages_switch_issue.py", "--self-test"]),
    ("Validate production lead monitoring", ["tools/check_lead_endpoint_monitoring.py"]),
    ("Validate production Edge deploy workflow", ["tools/check_edge_deploy_workflow.py"]),
    ("Validate controlled production lead smoke", ["tools/check_controlled_lead_smoke.py"]),
    ("Validate production lead launch readiness", ["tools/check_production_lead_launch_readiness.py"]),
    ("Validate production lead readiness staleness", ["tools/check_production_lead_readiness_staleness.py"]),
    ("Validate analytics privacy", ["tools/check_analytics_privacy.py"]),
    ("Validate JavaScript assets", ["tools/check_js_assets.py"]),
    ("Validate shared shell coverage", ["tools/check_shared_shell_coverage.py"]),
    ("Validate content inventory", ["tools/check_content_inventory.py"]),
    ("Validate content similarity", ["tools/check_content_similarity.py"]),
    ("Validate internal link map", ["tools/check_internal_link_map.py"]),
    ("Validate structured data", ["tools/check_structured_data.py"]),
    ("Validate breadcrumb schema", ["tools/check_breadcrumb_schema.py"]),
    ("Validate generated sitemap", ["tools/check_generated_sitemap.py"]),
    ("Validate sitemap helper", ["tools/check_sitemap_helper.py"]),
    ("Validate OG cards", ["tools/check_og_cards.py"]),
    ("Validate image attributes", ["tools/check_image_attributes.py"]),
    ("Validate live health checker", ["tools/check_live_site.py", "--self-test"]),
    ("Validate live conversion monitoring", ["tools/check_live_conversion_workflow.py"]),
    ("Validate Supabase retention", ["tools/check_supabase_retention.py"]),
    ("Validate link attributes", ["tools/check_empty_link_attributes.py"]),
    ("Run static audit", ["tools/check_site.py"]),
    ("Run extra guardrails", ["tools/check_guardrails.py"]),
    ("Validate conversion paths", ["tools/check_conversion_paths.py"]),
    ("Validate commercial pages", ["tools/check_commercial_pages.py"]),
    ("Validate callback topic context", ["tools/check_callback_topic_context.py"]),
    ("Validate homepage callback paths", ["tools/check_home_callback_links.py"]),
    ("Validate lead paths", ["tools/check_lead_paths.py"]),
    ("Validate lead reliability", ["tools/check_lead_reliability.py"]),
    ("Validate lead notification feedback", ["tools/check_lead_notification_feedback.py"]),
    ("Validate lead payload shape", ["tools/check_payload_shape.py"]),
    ("Validate IndexNow workflow", ["tools/check_indexnow_workflow.py"]),
    ("Validate IndexNow discovery", ["tools/submit_indexnow.py", "--check"]),
    ("Build public directory", ["tools/build_pages.py"]),
]


def main() -> int:
    for title, args in CHECKS:
        print(f"\n==> {title}", flush=True)
        completed = subprocess.run([sys.executable, *args], cwd=ROOT, check=False)
        if completed.returncode != 0:
            print(f"\nQuality check failed: {title}", file=sys.stderr)
            return completed.returncode

    print("\nAll quality checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
