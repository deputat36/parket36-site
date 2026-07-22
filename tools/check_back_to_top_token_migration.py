#!/usr/bin/env python3
"""Validate the tokenized production Back to Top component."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "design" / "components" / "parket36-components.json"
MANIFEST = ROOT / "design" / "figma" / "parket36-sync-manifest.json"
CATALOG = ROOT / "design" / "prototypes" / "components-v1.htm"
CATALOG_CSS = ROOT / "design" / "prototypes" / "components-v1-back-to-top.css"
PRODUCTION_CSS = ROOT / "css" / "back-to-top-polish.css"
JS = ROOT / "js" / "main.js"
BUNDLE = ROOT / "tools" / "css_bundle.py"
DOC = ROOT / "docs" / "design" / "parket36-back-to-top-token-migration-v1.md"
PRODUCTION_DOC = ROOT / "docs" / "design" / "parket36-production-token-layer-v1.md"

EXPECTED_STATES = ["hidden", "visible", "hover", "focus", "pressed"]
EXPECTED_DIMENSIONS = {
    "size": 48,
    "desktopRight": 18,
    "desktopBottom": 22,
    "mobileBottom": 82,
    "visibilityThreshold": 650,
    "radiusToken": "radius.full",
}
EXPECTED_ACCESSIBILITY = {
    "nativeButtonRequired": True,
    "accessibleNameRequired": True,
    "focusVisible": True,
    "reducedMotionAware": True,
    "minimumTouchTarget": 44,
}
REQUIRED_CSS = (
    "/* Tokenized Back to Top:",
    ".back-to-top {",
    "width: 48px",
    "height: 48px",
    "min-width: var(--p36-size-touch-min)",
    "min-height: var(--p36-size-touch-min)",
    "border-radius: var(--p36-radius-full)",
    "background: var(--p36-color-semantic-action-primary)",
    "color: var(--p36-color-semantic-text-inverse)",
    "box-shadow: var(--p36-shadow-floating)",
    "opacity: 0",
    "pointer-events: none",
    ".back-to-top.is-visible",
    "opacity: 1",
    "pointer-events: auto",
    ".back-to-top.is-visible:hover",
    "background: var(--p36-color-semantic-action-primary-hover)",
    ".back-to-top:focus-visible",
    "outline: 3px solid var(--p36-color-primitive-brass-200)",
    ".back-to-top.is-visible:active",
    "box-shadow: var(--p36-shadow-card)",
    "@media (max-width: 640px)",
    "bottom: 82px",
    "@media (prefers-reduced-motion: reduce)",
    "transition: none",
)
REQUIRED_JS = (
    "const backToTop = document.createElement('button');",
    "backToTop.type = 'button';",
    "backToTop.className = 'back-to-top';",
    "backToTop.textContent = '↑';",
    "backToTop.setAttribute('aria-label', 'Вернуться к началу страницы');",
    "document.body.appendChild(backToTop);",
    "backToTop.classList.toggle('is-visible', window.scrollY > 650);",
    "backToTop.addEventListener('click', () => {",
    "window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });",
)
FORBIDDEN_CSS_PATTERNS = (
    re.compile(r"#[0-9a-fA-F]{3,8}\b"),
    re.compile(r"\brgba?\("),
    re.compile(r"\bhsla?\("),
    re.compile(r"var\(--wood\)"),
    re.compile(r"var\(--gold\)"),
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_css_modules(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if "CSS_MODULES" in names:
            value = ast.literal_eval(node.value)
            if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
                return value
    raise ValueError("CSS_MODULES assignment is missing or invalid")


def main() -> int:
    findings: list[str] = []
    required_files = (
        CONTRACT,
        MANIFEST,
        CATALOG,
        CATALOG_CSS,
        PRODUCTION_CSS,
        JS,
        BUNDLE,
        DOC,
        PRODUCTION_DOC,
    )
    for path in required_files:
        if not path.is_file():
            findings.append(f"missing Back to Top asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        contract = read_json(CONTRACT)
        manifest = read_json(MANIFEST)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Back to Top JSON is invalid: {exc}")
        return 1

    component = contract.get("components", {}).get("backToTop", {})
    if component.get("figmaName") != "Back to Top":
        findings.append("backToTop.figmaName must remain 'Back to Top'")
    if component.get("anatomy") != ["Container", "Icon"]:
        findings.append("Back to Top anatomy must remain Container + Icon")
    properties = component.get("properties", {})
    if properties.get("state") != EXPECTED_STATES:
        findings.append("Back to Top states differ from the approved order")
    if properties.get("icon") != "arrow-up":
        findings.append("Back to Top icon contract must remain arrow-up")
    if component.get("dimensions") != EXPECTED_DIMENSIONS:
        findings.append("Back to Top dimensions differ from the approved contract")
    if component.get("accessibility") != EXPECTED_ACCESSIBILITY:
        findings.append("Back to Top accessibility contract differs from the approved contract")

    manifest_state = manifest.get("components", {}).get("Back to Top", {})
    if manifest_state != {"nodeId": None, "status": "pending"}:
        findings.append("Figma Back to Top must remain pending with null nodeId")

    css = PRODUCTION_CSS.read_text(encoding="utf-8")
    for marker in REQUIRED_CSS:
        if marker not in css:
            findings.append(f"Back to Top CSS is missing marker: {marker}")
    for pattern in FORBIDDEN_CSS_PATTERNS:
        if pattern.search(css):
            findings.append(f"Back to Top CSS contains forbidden raw/legacy color: {pattern.pattern}")
    if css.count(".back-to-top {") != 2:
        findings.append("Back to Top production CSS must define base and mobile blocks only")

    js = JS.read_text(encoding="utf-8")
    for marker in REQUIRED_JS:
        if marker not in js:
            findings.append(f"Back to Top JavaScript contract is missing marker: {marker}")
    if "window.scrollY > 650" not in js:
        findings.append("Back to Top visibility threshold must remain 650 px")
    if "prefersReducedMotion() ? 'auto' : 'smooth'" not in js:
        findings.append("Back to Top must remain reduced-motion aware")

    try:
        modules = load_css_modules(BUNDLE)
    except (SyntaxError, ValueError) as exc:
        findings.append(str(exc))
        modules = ()
    if modules:
        if modules.count("back-to-top-polish.css") != 1:
            findings.append("back-to-top-polish.css must appear exactly once in CSS_MODULES")
        try:
            choice_index = modules.index("choice-chip-polish.css")
            back_index = modules.index("back-to-top-polish.css")
            logo_index = modules.index("logo-brand.css")
        except ValueError:
            findings.append("Back to Top bundle neighbours are missing")
        else:
            if not choice_index < back_index < logo_index:
                findings.append("Back to Top bundle order must remain after Choice Chip and before Logo")

    catalog = CATALOG.read_text(encoding="utf-8")
    catalog_css = CATALOG_CSS.read_text(encoding="utf-8")
    for marker in (
        'href="./components-v1-back-to-top.css"',
        'id="back-to-top"',
        "Back to Top",
        "hidden · visible · hover · focus · pressed",
        'aria-label="Вернуться к началу страницы"',
        "back-to-top-specimen is-hidden",
        "back-to-top-specimen is-hover",
        "back-to-top-specimen is-focus",
        "back-to-top-specimen is-pressed",
    ):
        if marker not in catalog:
            findings.append(f"Back to Top catalog is missing marker: {marker}")
    for marker in (
        ".back-to-top-specimen",
        "width: 48px",
        "height: 48px",
        "var(--p36-radius-full)",
        "var(--p36-shadow-floating)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        if marker not in catalog_css:
            findings.append(f"Back to Top catalog CSS is missing marker: {marker}")
    for pattern in FORBIDDEN_CSS_PATTERNS:
        if pattern.search(catalog_css):
            findings.append(f"Back to Top catalog CSS contains forbidden raw/legacy color: {pattern.pattern}")

    doc = DOC.read_text(encoding="utf-8")
    production_doc = PRODUCTION_DOC.read_text(encoding="utf-8")
    for marker in (
        "48×48 px",
        "650 px",
        "Вернуться к началу страницы",
        "mobile до 640 px",
        "prefers-reduced-motion: reduce",
        "back-to-top-polish.css",
        "JavaScript не изменяется",
    ):
        if marker.lower() not in doc.lower():
            findings.append(f"Back to Top documentation is missing marker: {marker}")
    for marker in (
        "css/back-to-top-polish.css",
        "Back to Top",
        "порогом 650 px",
    ):
        if marker.lower() not in production_doc.lower():
            findings.append(f"production token documentation is missing Back to Top marker: {marker}")

    if findings:
        print("Back to Top token migration findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Back to Top token migration passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
