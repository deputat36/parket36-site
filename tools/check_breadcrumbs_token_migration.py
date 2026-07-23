#!/usr/bin/env python3
"""Validate tokenized Breadcrumbs and visible BreadcrumbList source structure."""

from __future__ import annotations

import ast
from html import unescape
import json
from pathlib import Path
import re
import sys
from typing import Any

from breadcrumb_schema import BreadcrumbPageParser, breadcrumb_payload

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "design" / "components" / "parket36-components.json"
MANIFEST = ROOT / "design" / "figma" / "parket36-sync-manifest.json"
CATALOG = ROOT / "design" / "prototypes" / "components-v1.htm"
CATALOG_CSS = ROOT / "design" / "prototypes" / "components-v1-breadcrumbs.css"
PRODUCTION_CSS = ROOT / "css" / "breadcrumbs-polish.css"
BUNDLE = ROOT / "tools" / "css_bundle.py"
SCHEMA_GENERATOR = ROOT / "tools" / "breadcrumb_schema.py"
SCHEMA_CHECK = ROOT / "tools" / "check_breadcrumb_schema.py"
RUNNER = ROOT / "tools" / "run_quality_checks.py"
DOC = ROOT / "docs" / "design" / "parket36-breadcrumbs-token-migration-v1.md"
PRODUCTION_DOC = ROOT / "docs" / "design" / "parket36-production-token-layer-v1.md"
DOMAIN = "https://parket36.ru"

BLOCK_RE = re.compile(r'<div\s+class="breadcrumbs">(.*?)</div>', re.DOTALL)
ITEM_RE = re.compile(r'<(a|span)(?:\s+href="([^"]*)")?>(.*?)</\1>', re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
RAW_COLOR_PATTERNS = (
    re.compile(r"#[0-9a-fA-F]{3,8}\b"),
    re.compile(r"\brgba?\("),
    re.compile(r"\bhsla?\("),
    re.compile(r"var\(--wood\)"),
    re.compile(r"var\(--gold\)"),
)
SKIP_PARTS = {"_site", "design", "node_modules", "vendor", ".git"}

EXPECTED_DIMENSIONS = {
    "minimumHeight": 40,
    "horizontalPadding": 12,
    "gap": 8,
    "radiusToken": "radius.full",
    "mobileRadiusToken": "radius.md",
}
EXPECTED_ACCESSIBILITY = {
    "firstItemHome": True,
    "currentItemNotLinked": True,
    "focusVisible": True,
    "wrapsWithoutClipping": True,
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_modules(path: Path) -> tuple[str, ...]:
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


def clean_text(value: str) -> str:
    return " ".join(unescape(TAG_RE.sub("", value)).split())


def parse_visible_items(block: str) -> list[tuple[str, str, str]]:
    return [(tag, href or "", clean_text(label)) for tag, href, label in ITEM_RE.findall(block)]


def public_html_files() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*.html"):
        relative = path.relative_to(ROOT)
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        result.append(path)
    return sorted(result)


def validate_page(path: Path, text: str, findings: list[str]) -> None:
    relative = path.relative_to(ROOT).as_posix()
    blocks = BLOCK_RE.findall(text)
    if len(blocks) != 1:
        findings.append(f"{relative}: expected exactly one breadcrumbs block")
        return

    items = parse_visible_items(blocks[0])
    if len(items) < 3 or len(items) % 2 == 0:
        findings.append(f"{relative}: breadcrumb nodes must alternate item/separator/item")
        return

    if items[0] != ("a", "/", "Главная"):
        findings.append(f"{relative}: first breadcrumb must be Главная -> /")

    visible_labels: list[str] = []
    for index, (tag, href, label) in enumerate(items):
        if not label:
            findings.append(f"{relative}: breadcrumb node {index + 1} has empty text")
        if index % 2 == 1:
            if (tag, href, label) != ("span", "", "›"):
                findings.append(f"{relative}: separator {index + 1} must be span ›")
            continue

        visible_labels.append(label)
        is_last = index == len(items) - 1
        if is_last:
            if tag != "span" or href or label == "›":
                findings.append(f"{relative}: current breadcrumb must be final non-link span")
        elif tag != "a" or not href:
            findings.append(f"{relative}: parent breadcrumb {index + 1} must be a link")

    parser = BreadcrumbPageParser()
    parser.feed(text)
    if [name for name, _ in parser.items] != visible_labels:
        findings.append(f"{relative}: schema parser labels differ from visible breadcrumbs")
        return

    try:
        payload = breadcrumb_payload(parser, DOMAIN)
    except ValueError as exc:
        findings.append(f"{relative}: {exc}")
        return

    if "noindex" not in parser.robots.lower():
        elements = payload.get("itemListElement") if isinstance(payload, dict) else None
        if not isinstance(elements, list) or len(elements) != len(visible_labels):
            findings.append(f"{relative}: generated BreadcrumbList size differs from visible items")


def main() -> int:
    findings: list[str] = []
    required = (
        CONTRACT,
        MANIFEST,
        CATALOG,
        CATALOG_CSS,
        PRODUCTION_CSS,
        BUNDLE,
        SCHEMA_GENERATOR,
        SCHEMA_CHECK,
        RUNNER,
        DOC,
        PRODUCTION_DOC,
    )
    for path in required:
        if not path.is_file():
            findings.append(f"missing Breadcrumbs asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        contract = read_json(CONTRACT)
        manifest = read_json(MANIFEST)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Breadcrumbs JSON is invalid: {exc}")
        return 1

    component = contract.get("components", {}).get("breadcrumbs", {})
    if component.get("figmaName") != "Breadcrumbs":
        findings.append("breadcrumbs.figmaName must remain Breadcrumbs")
    if component.get("anatomy") != ["Container", "Link", "Separator", "Current"]:
        findings.append("Breadcrumbs anatomy differs from approved contract")
    properties = component.get("properties", {})
    if properties.get("state") != ["default", "hover", "focus"]:
        findings.append("Breadcrumbs states differ from approved order")
    if properties.get("separator") != "chevron-right" or properties.get("wraps") != "boolean":
        findings.append("Breadcrumbs separator/wrap properties differ from approved contract")
    if component.get("dimensions") != EXPECTED_DIMENSIONS:
        findings.append("Breadcrumbs dimensions differ from approved contract")
    if component.get("accessibility") != EXPECTED_ACCESSIBILITY:
        findings.append("Breadcrumbs accessibility differs from approved contract")

    if manifest.get("components", {}).get("Breadcrumbs") != {"nodeId": None, "status": "pending"}:
        findings.append("Figma Breadcrumbs must remain pending with null nodeId")

    css = PRODUCTION_CSS.read_text(encoding="utf-8")
    for marker in (
        "/* Tokenized Breadcrumbs:",
        ".breadcrumbs {",
        "flex-wrap: wrap",
        "min-height: 40px",
        "gap: var(--p36-spacing-sm)",
        "padding: var(--p36-spacing-sm) var(--p36-spacing-md)",
        "border-radius: var(--p36-radius-full)",
        "box-shadow: var(--p36-shadow-card)",
        ".breadcrumbs a:hover",
        ".breadcrumbs a:focus-visible",
        "outline: 3px solid var(--p36-color-primitive-brass-200)",
        ".breadcrumbs > span:last-child",
        "@media (max-width: 640px)",
        "border-radius: var(--p36-radius-md)",
        "@media (prefers-reduced-motion: reduce)",
        "transition: none",
    ):
        if marker not in css:
            findings.append(f"Breadcrumbs CSS is missing marker: {marker}")
    for pattern in RAW_COLOR_PATTERNS:
        if pattern.search(css):
            findings.append(f"Breadcrumbs CSS contains forbidden raw/legacy color: {pattern.pattern}")
    if css.count(".breadcrumbs {") != 2:
        findings.append("Breadcrumbs CSS must contain base and mobile container blocks")

    try:
        modules = load_modules(BUNDLE)
    except (SyntaxError, ValueError) as exc:
        findings.append(str(exc))
        modules = ()
    expected_tail = (
        "back-to-top-polish.css",
        "breadcrumbs-polish.css",
        "proof-card-polish.css",
        "logo-brand.css",
    )
    if modules and tuple(modules[-4:]) != expected_tail:
        findings.append("Breadcrumbs bundle order differs from approved tail")

    catalog = CATALOG.read_text(encoding="utf-8")
    catalog_css = CATALOG_CSS.read_text(encoding="utf-8")
    for marker in (
        'href="./components-v1-breadcrumbs.css"',
        'id="breadcrumbs"',
        "default · hover · focus",
        "breadcrumbs-specimen is-hover",
        "breadcrumbs-specimen is-focus",
        "breadcrumbs-specimen__separator",
        "breadcrumbs-specimen__current",
    ):
        if marker not in catalog:
            findings.append(f"Breadcrumbs catalog is missing marker: {marker}")
    for marker in (
        ".breadcrumbs-specimen",
        "min-height: 40px",
        "flex-wrap: wrap",
        "var(--p36-radius-full)",
        "var(--p36-radius-md)",
        "var(--p36-shadow-card)",
    ):
        if marker not in catalog_css:
            findings.append(f"Breadcrumbs catalog CSS is missing marker: {marker}")
    for pattern in RAW_COLOR_PATTERNS:
        if pattern.search(catalog_css):
            findings.append(f"Breadcrumbs catalog CSS contains forbidden raw/legacy color: {pattern.pattern}")

    breadcrumb_pages = 0
    for html_file in public_html_files():
        text = html_file.read_text(encoding="utf-8")
        if 'class="breadcrumbs"' not in text:
            continue
        breadcrumb_pages += 1
        validate_page(html_file, text, findings)
    if breadcrumb_pages < 20:
        findings.append(f"expected at least 20 public breadcrumb pages, found {breadcrumb_pages}")

    generator_text = SCHEMA_GENERATOR.read_text(encoding="utf-8")
    for marker in (
        'GENERATED_MARKER = "data-generated-breadcrumbs"',
        'SEPARATORS = {"›", ">", "→", "/", "»"}',
        '"@type": "BreadcrumbList"',
        "inject_breadcrumb_schemas",
    ):
        if marker not in generator_text:
            findings.append(f"BreadcrumbList generator is missing marker: {marker}")

    runner_text = RUNNER.read_text(encoding="utf-8")
    for marker in ("tools/check_breadcrumbs_token_migration.py", "tools/check_breadcrumb_schema.py"):
        if marker not in runner_text:
            findings.append(f"quality runner is missing Breadcrumbs check: {marker}")

    doc_lower = DOC.read_text(encoding="utf-8").lower()
    production_doc_lower = PRODUCTION_DOC.read_text(encoding="utf-8").lower()
    for marker in (
        "40 px",
        "разделитель `›`",
        "текущий пункт без ссылки",
        "flex-wrap: wrap",
        "breadcrumblist",
        "breadcrumbs-polish.css",
    ):
        if marker.lower() not in doc_lower:
            findings.append(f"Breadcrumbs documentation is missing marker: {marker}")
    for marker in ("css/breadcrumbs-polish.css", "breadcrumblist json-ld", "breadcrumbs"):
        if marker.lower() not in production_doc_lower:
            findings.append(f"production token documentation is missing Breadcrumbs marker: {marker}")

    if findings:
        print("Breadcrumbs token migration findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print(f"Breadcrumbs token migration passed across {breadcrumb_pages} public pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
