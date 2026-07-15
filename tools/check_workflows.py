#!/usr/bin/env python3
"""Validate GitHub Actions workflow and browser-quality configuration."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE_QUALITY_PATH = ROOT / ".github" / "workflows" / "site-quality.yml"
PAGES_PATH = ROOT / ".github" / "workflows" / "pages.yml"
LIVE_HEALTH_PATH = ROOT / ".github" / "workflows" / "live-site-health.yml"
BROWSER_SMOKE_PATH = ROOT / ".github" / "workflows" / "browser-smoke.yml"
LIGHTHOUSE_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "lighthouse.yml"
LIVE_ISSUE_MANAGER = ROOT / "tools" / "manage_live_health_issue.py"
PLAYWRIGHT_CONFIG = ROOT / "playwright.config.mjs"
LIGHTHOUSE_CONFIG = ROOT / "lighthouserc.cjs"
PACKAGE_JSON = ROOT / "package.json"
DENO_CONFIG = ROOT / "deno.json"
REQUIREMENTS_QUALITY = ROOT / "requirements-quality.txt"
E2E_TEST = ROOT / "tests" / "e2e" / "site-smoke.spec.mjs"
ACCESSIBILITY_TEST = ROOT / "tests" / "e2e" / "accessibility.spec.mjs"
NO_JS_ACCESSIBILITY_TEST = ROOT / "tests" / "e2e" / "no-js-accessibility.spec.mjs"
SHARED_SHELL_TEST = ROOT / "tests" / "e2e" / "shared-shell.spec.mjs"
OG_CARD_TEST = ROOT / "tests" / "e2e" / "og-cards.spec.mjs"
ACCESSIBILITY_CSS = ROOT / "css" / "accessibility-polish.css"
HTML_ACCESSIBILITY = ROOT / "tools" / "html_accessibility.py"
SHARED_SHELL_TOOL = ROOT / "tools" / "shared_shell.py"
SHARED_SHELL_COVERAGE_TOOL = ROOT / "tools" / "build_shared_shell_coverage.py"
SHARED_SHELL_COVERAGE_CHECK = ROOT / "tools" / "check_shared_shell_coverage.py"
CONTENT_INVENTORY_TOOL = ROOT / "tools" / "build_content_inventory.py"
CONTENT_SIMILARITY_TOOL = ROOT / "tools" / "build_content_similarity_report.py"
INTERNAL_LINK_MAP_TOOL = ROOT / "tools" / "build_internal_link_map.py"
SITEMAP_TOOL = ROOT / "tools" / "build_sitemap.py"
OG_CARD_TOOL = ROOT / "tools" / "og_cards.py"

CHECKOUT = "uses: actions/checkout@v7"
SETUP_PYTHON = "uses: actions/setup-python@v6"
SETUP_NODE = "uses: actions/setup-node@v6"
UPLOAD_ARTIFACT = "uses: actions/upload-artifact@v7"
CONFIGURE_PAGES = "uses: actions/configure-pages@v6"
UPLOAD_PAGES = "uses: actions/upload-pages-artifact@v5"
DEPLOY_PAGES = "uses: actions/deploy-pages@v5"
PYTHON_VERSION = 'python-version: "3.12"'
DENO_SETUP = "uses: denoland/setup-deno@v2"
DENO_VERSION = "deno-version: lts"
DENO_CHECK = "deno check supabase/functions/parket-public-lead/index.ts"
QUALITY_DEPS = "python -m pip install --disable-pip-version-check -r requirements-quality.txt"
QUALITY_RUNNER = "python tools/run_quality_checks.py"

EXPECTED_MARKERS = {
    SITE_QUALITY_PATH: [
        CHECKOUT,
        SETUP_PYTHON,
        PYTHON_VERSION,
        QUALITY_DEPS,
        DENO_SETUP,
        DENO_VERSION,
        DENO_CHECK,
        "id: edge_typecheck",
        "continue-on-error: true",
        UPLOAD_ARTIFACT,
        "name: edge-function-check",
        "if: steps.edge_typecheck.outcome == 'failure'",
        "id: quality_gate",
        "name: quality-gate-log",
        "if: steps.quality_gate.outcome == 'failure'",
        "quality-gate.log",
        "run: python tools/build_content_inventory.py --output-dir reports/content-inventory",
        "name: content-inventory",
        "path: reports/content-inventory",
        "run: python tools/build_content_similarity_report.py --output-dir reports/content-similarity",
        "name: content-similarity-report",
        "path: reports/content-similarity",
        "run: python tools/build_internal_link_map.py --output-dir reports/internal-links",
        "name: internal-link-map",
        "path: reports/internal-links",
        "run: python tools/build_shared_shell_coverage.py --output-dir reports/shared-shell-coverage",
        "name: shared-shell-coverage",
        "path: reports/shared-shell-coverage",
        "run: python tools/build_sitemap.py --source sitemap.xml --output reports/generated-sitemap.xml",
        "name: generated-sitemap",
        "path: reports/generated-sitemap.xml",
    ],
    PAGES_PATH: [
        CHECKOUT,
        SETUP_PYTHON,
        PYTHON_VERSION,
        QUALITY_DEPS,
        DENO_SETUP,
        DENO_VERSION,
        DENO_CHECK,
        f"run: {QUALITY_RUNNER}",
        CONFIGURE_PAGES,
        UPLOAD_PAGES,
        DEPLOY_PAGES,
        'path: "_site"',
    ],
    LIVE_HEALTH_PATH: [
        'cron: "23 4 * * *"',
        "workflow_dispatch:",
        "actions: read",
        "issues: write",
        CHECKOUT,
        SETUP_PYTHON,
        PYTHON_VERSION,
        "run: python tools/check_live_site.py --report live-health-report.md",
        "continue-on-error: true",
        UPLOAD_ARTIFACT,
        "GITHUB_TOKEN: ${{ github.token }}",
        "run: python tools/manage_live_health_issue.py failure --report live-health-report.md",
        "run: python tools/manage_live_health_issue.py success",
        "if: steps.live_health.outcome == 'failure'",
        "if: steps.live_health.outcome == 'success'",
    ],
    BROWSER_SMOKE_PATH: [
        'cron: "41 5 * * 1"',
        "workflow_dispatch:",
        CHECKOUT,
        SETUP_PYTHON,
        PYTHON_VERSION,
        QUALITY_DEPS,
        SETUP_NODE,
        'node-version: "20"',
        "package-manager-cache: false",
        "run: npm install --no-audit --no-fund",
        "run: npx playwright install --with-deps chromium",
        "run: npm run test:e2e",
        UPLOAD_ARTIFACT,
        "name: browser-smoke-report",
    ],
    LIGHTHOUSE_WORKFLOW_PATH: [
        'cron: "7 6 * * 1"',
        "workflow_dispatch:",
        CHECKOUT,
        SETUP_PYTHON,
        PYTHON_VERSION,
        QUALITY_DEPS,
        SETUP_NODE,
        'node-version: "20"',
        "package-manager-cache: false",
        "run: npm install --no-audit --no-fund",
        "run: python tools/build_pages.py",
        "run: npm run test:lighthouse",
        UPLOAD_ARTIFACT,
        "name: lighthouse-report",
    ],
}

REQUIRED_QUALITY_FILES = {
    PACKAGE_JSON: [
        '"@axe-core/playwright": "4.10.2"',
        '"@lhci/cli": "0.15.1"',
        '"@playwright/test": "1.54.2"',
        '"test:e2e": "playwright test"',
        '"test:lighthouse": "lhci autorun --config=./lighthouserc.cjs"',
    ],
    DENO_CONFIG: ['"nodeModulesDir": "auto"'],
    REQUIREMENTS_QUALITY: ["Pillow==12.2.0"],
    PLAYWRIGHT_CONFIG: [
        "python tools/build_pages.py",
        "python -m http.server 4173",
        "trace: 'retain-on-failure'",
    ],
    LIGHTHOUSE_CONFIG: [
        "staticDistDir: './_site'",
        "http://localhost/zayavka/",
        "'categories:performance'",
        "'categories:accessibility'",
        "'categories:best-practices'",
        "'categories:seo'",
        "target: 'filesystem'",
    ],
    E2E_TEST: [
        "мобильное меню открывается",
        "успешный backend сохраняет заявку",
        "форма показывает ручной fallback",
        "страница 404 остаётся noindex",
    ],
    ACCESSIBILITY_TEST: ["AxeBuilder", "wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
    NO_JS_ACCESSIBILITY_TEST: [
        "javaScriptEnabled: false",
        "a.skip-link",
        "main#main-content",
        "aria-controls",
        "data-css-bundle",
    ],
    SHARED_SHELL_TEST: [
        "javaScriptEnabled: false",
        "header.topbar",
        "section.final-cta",
        "footer.footer",
        "div.mobile-cta",
        "expect(request).toEqual(home)",
    ],
    OG_CARD_TEST: [
        "og:image",
        "image/png",
        "summary_large_image",
        "137, 80, 78, 71, 13, 10, 26, 10",
    ],
    ACCESSIBILITY_CSS: [
        ".person-card .muted",
        '.form-help a[href$="/politika/"]',
        '.footer__bottom a[href$="/politika/"]',
        "text-decoration: underline",
    ],
    HTML_ACCESSIBILITY: ["SKIP_LINK", "main-content", "site-navigation", "inject_accessibility_html"],
    SHARED_SHELL_TOOL: ["PILOT_PAGES", "data/shared-shell/header.html", "shared-shell:final-cta", "apply_shared_shell"],
    SHARED_SHELL_COVERAGE_TOOL: [
        "CoverageRecord",
        "build_page_profiles",
        "shared-shell-coverage.csv",
        "shared-shell-coverage.md",
        "self_test",
    ],
    SHARED_SHELL_COVERAGE_CHECK: [
        "docs/shared-shell-coverage.csv",
        "docs/shared-shell-coverage.md",
        "write_report",
        "self_test",
    ],
    CONTENT_INVENTORY_TOOL: [
        "PageRecord",
        "THIN_WORD_LIMIT",
        "inbound_links",
        "title_duplicate_count",
        "content-inventory.csv",
        "content-inventory.md",
    ],
    CONTENT_SIMILARITY_TOOL: [
        "MainContentParser",
        "SIMILARITY_THRESHOLD",
        "canonical_groups",
        "content-similarity-report.md",
        "content-similarity-pairs.csv",
    ],
    INTERNAL_LINK_MAP_TOOL: [
        "LinkMapParser",
        "contextual_inbound",
        "shared_only_inbound",
        "internal-link-nodes.csv",
        "internal-link-edges.csv",
        "internal-link-map.md",
    ],
    SITEMAP_TOOL: [
        "SitemapPageParser",
        "dateModified",
        "datePublished",
        "default_policy",
        "generated-sitemap.xml",
    ],
    OG_CARD_TOOL: [
        "WIDTH = 1200",
        "HEIGHT = 630",
        "summary_large_image",
        "validate_og_cards",
    ],
}

FORBIDDEN_MARKERS = [
    "uses: actions/checkout@v4",
    "uses: actions/checkout@v6",
    "uses: actions/setup-python@v5",
    "uses: actions/setup-node@v4",
    "uses: actions/upload-artifact@v4",
    "uses: actions/configure-pages@v5",
    "uses: actions/upload-pages-artifact@v4",
    "uses: actions/deploy-pages@v4",
    "uses: denoland/setup-deno@v3",
    "permissions: write-all",
    "package-manager-cache: true",
]


def main() -> int:
    findings: list[str] = []

    for path, expected_markers in EXPECTED_MARKERS.items():
        if not path.exists():
            findings.append(f"{path.relative_to(ROOT)} is missing")
            continue
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        for marker in expected_markers:
            if marker not in text:
                findings.append(f"{relative} must contain {marker}")
        for marker in FORBIDDEN_MARKERS:
            if marker in text:
                findings.append(f"{relative} must not contain {marker}")

    for path, expected_markers in REQUIRED_QUALITY_FILES.items():
        if not path.exists():
            findings.append(f"{path.relative_to(ROOT)} is missing")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in expected_markers:
            if marker not in text:
                findings.append(f"{path.relative_to(ROOT)} must contain {marker}")

    if not LIVE_ISSUE_MANAGER.exists():
        findings.append("tools/manage_live_health_issue.py is missing")
    else:
        completed = subprocess.run(
            [sys.executable, str(LIVE_ISSUE_MANAGER), "--self-test"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            detail = (completed.stdout + completed.stderr).strip()
            findings.append("live-health issue manager self-test failed: " + detail)

    if findings:
        print("Workflow findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Workflow check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
