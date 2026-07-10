#!/usr/bin/env python3
"""Validate GitHub Actions workflow configuration."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE_QUALITY_PATH = ROOT / ".github" / "workflows" / "site-quality.yml"
PAGES_PATH = ROOT / ".github" / "workflows" / "pages.yml"
LIVE_HEALTH_PATH = ROOT / ".github" / "workflows" / "live-site-health.yml"
BROWSER_SMOKE_PATH = ROOT / ".github" / "workflows" / "browser-smoke.yml"
LIVE_ISSUE_MANAGER = ROOT / "tools" / "manage_live_health_issue.py"
PLAYWRIGHT_CONFIG = ROOT / "playwright.config.mjs"
PACKAGE_JSON = ROOT / "package.json"
DENO_CONFIG = ROOT / "deno.json"
E2E_TEST = ROOT / "tests" / "e2e" / "site-smoke.spec.mjs"
ACCESSIBILITY_TEST = ROOT / "tests" / "e2e" / "accessibility.spec.mjs"
ACCESSIBILITY_CSS = ROOT / "css" / "accessibility-polish.css"
QUALITY_RUNNER = "python tools/run_quality_checks.py"
PYTHON_VERSION = 'python-version: "3.12"'
DENO_SETUP = "uses: denoland/setup-deno@v2"
DENO_VERSION = "deno-version: lts"
DENO_CHECK = "deno check supabase/functions/parket-public-lead/index.ts"

EXPECTED_MARKERS = {
    SITE_QUALITY_PATH: [
        "uses: actions/checkout@v4",
        "uses: actions/setup-python@v5",
        PYTHON_VERSION,
        DENO_SETUP,
        DENO_VERSION,
        DENO_CHECK,
        "id: edge_typecheck",
        "continue-on-error: true",
        "uses: actions/upload-artifact@v4",
        "name: edge-function-check",
        "if: steps.edge_typecheck.outcome == 'failure'",
        f"run: {QUALITY_RUNNER}",
    ],
    PAGES_PATH: [
        "uses: actions/checkout@v4",
        "uses: actions/setup-python@v5",
        PYTHON_VERSION,
        DENO_SETUP,
        DENO_VERSION,
        DENO_CHECK,
        f"run: {QUALITY_RUNNER}",
        "uses: actions/configure-pages@v5",
        "uses: actions/upload-pages-artifact@v4",
        "uses: actions/deploy-pages@v4",
        'path: "_site"',
    ],
    LIVE_HEALTH_PATH: [
        'cron: "23 4 * * *"',
        "workflow_dispatch:",
        "actions: read",
        "issues: write",
        "uses: actions/checkout@v4",
        "uses: actions/setup-python@v5",
        PYTHON_VERSION,
        "run: python tools/check_live_site.py --report live-health-report.md",
        "continue-on-error: true",
        "uses: actions/upload-artifact@v4",
        "GITHUB_TOKEN: ${{ github.token }}",
        "run: python tools/manage_live_health_issue.py failure --report live-health-report.md",
        "run: python tools/manage_live_health_issue.py success",
        "if: steps.live_health.outcome == 'failure'",
        "if: steps.live_health.outcome == 'success'",
    ],
    BROWSER_SMOKE_PATH: [
        'cron: "41 5 * * 1"',
        "workflow_dispatch:",
        "uses: actions/checkout@v4",
        "uses: actions/setup-python@v5",
        PYTHON_VERSION,
        "uses: actions/setup-node@v4",
        'node-version: "20"',
        "run: npm install --no-audit --no-fund",
        "run: npx playwright install --with-deps chromium",
        "run: npm run test:e2e",
        "uses: actions/upload-artifact@v4",
        "name: browser-smoke-report",
    ],
}

REQUIRED_BROWSER_FILES = {
    PACKAGE_JSON: [
        '"@axe-core/playwright": "4.10.2"',
        '"@playwright/test": "1.54.2"',
        '"test:e2e": "playwright test"',
    ],
    DENO_CONFIG: ['"nodeModulesDir": "auto"'],
    PLAYWRIGHT_CONFIG: ["python tools/build_pages.py", "python -m http.server 4173", "trace: 'retain-on-failure'"],
    E2E_TEST: [
        "мобильное меню открывается",
        "успешный backend сохраняет заявку",
        "форма показывает ручной fallback",
        "страница 404 остаётся noindex",
    ],
    ACCESSIBILITY_TEST: [
        "AxeBuilder",
        "wcag2a",
        "wcag2aa",
        "wcag21a",
        "wcag21aa",
        "accessibility.spec.mjs",
    ],
    ACCESSIBILITY_CSS: [
        ".person-card .muted",
        '.form-help a[href$="/politika/"]',
        '.footer__bottom a[href$="/politika/"]',
        "text-decoration: underline",
    ],
}

FORBIDDEN_MARKERS = [
    "uses: actions/checkout@v6",
    "uses: denoland/setup-deno@v3",
    "permissions: write-all",
]


def main() -> int:
    findings: list[str] = []

    for path, expected_markers in EXPECTED_MARKERS.items():
        if not path.exists():
            findings.append(f"{path.relative_to(ROOT)} is missing")
            continue

        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)

        for marker in expected_markers:
            if marker not in text:
                findings.append(f"{rel} must contain {marker}")

        for marker in FORBIDDEN_MARKERS:
            if marker in text:
                findings.append(f"{rel} must not contain {marker}")

    for path, expected_markers in REQUIRED_BROWSER_FILES.items():
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
