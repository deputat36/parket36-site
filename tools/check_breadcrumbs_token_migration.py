#!/usr/bin/env python3
"""Validate the tokenized production Breadcrumbs component and visible breadcrumb structure."""

from __future__ import annotations

import ast
from html.parser import HTMLParser
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

EXPECTED_STATES = ["default", "hover", "focus"]
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
REQUIRED_CSS = (
    "/* Tokenized Breadcrumbs:",
    ".breadcrumbs {",
    "display: flex",
    "flex-wrap: wrap",
    "min-height: 40px",
    "gap: var(--p36-spacing-sm)",
    "padding: var(--p36-spacing-sm) var(--p36-spacing-md)",
    "border-radius: var(--p36-radius-full)",
    "background: var(--p36-color-semantic-surface-default)",
    "box-shadow: var(--p36-shadow-card)",
    ".breadcrumbs a:hover",
    "background: var(--p36-color-semantic-surface-subtle)",
    ".breadcrumbs a:focus-visible",
    "outline: 3px solid var(--p36-color-primitive-brass-200)",
    ".breadcrumbs > span:last-child",
    "@media (max-width: 640px)",
    "width: 100%",
    "border-radius: var(--p36-radius-md)",
    "@media (prefers-reduced-motion: reduce)",
    "transition: none",
)
FORBIDDEN_CSS_PATTERNS = (
    re.compile(r"#[0-9a-fA-F]{3,8}\b"),
    re.compile(r"\brgba?\("),
    re.compile(r"\bhsla?\("),
    re.compile(r"var\(--wood\)"),
    re.compile(r"var\(--gold\)"),
)
SKIP_PARTS = {"_site", "design", "node_modules", "vendor", ".git"}


class BreadcrumbStructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.container_count = 0
        self._depth = 0
        self._active_tag = ""
        self._active_href = ""
        self._chunks: list[str] = []
        self.elements: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key.lower(): (value or "") for key, value in attrs_list}
        lowered = tag.lower()
        if lowered == "div" and "breadcrumbs" in attrs.get("class", "").split():
            self.container_count += 1
            self._depth = 1
            return
        if self._depth and lowered == "div":
            self._depth += 1
        if self._depth and lowered in {"a", "span"}:
            self._active_tag = lowered
            self._active_href = attrs.get("href", "").strip() if lowered == "a" else ""
            self._chunks = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if self._depth and lowered == self._active_tag:
            text = " ".join("".join(self._chunks).split())
            self.elements.append((self._active_tag, text, self._active_href))
            self._active_tag = ""
            self._active_href = ""
            self._chunks = []
        if self._depth and lowered == "div":
            self._depth -= 1

    def handle_data(self, data: str) -> None:
        if self._depth and self._active_tag:
            self._chunks.append(data)


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


def public_html_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*.html"):
        relative = path.relative_to(ROOT)
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        files.append(path)
    return sorted(files)


def validate_visible_breadcrumbs(path: Path, text: str, findings: list[str]) -> None:
    relative = path.relative_to(ROOT).as_posix()
    structure = BreadcrumbStructureParser()
    structure.feed(text)
    if structure.container_count != 1:
        findings.append(f"{relative}: expected exactly one breadcrumbs container")
        return

    elements = structure.elements
    if len(elements) < 3 or len(elements) % 2 == 0:
        findings.append(f"{relative}: breadcrumb elements must alternate item/separator/item")
        return

    first_tag, first_text, first_href = elements[0]
    if (first_tag, first_text, first_href) != ("a", "Главная", "/"):
        findings.append(f"{relative}: first breadcrumb must be link Главная -> /")

    for index, (tag, label, href) in enumerate(elements):
        if not label:
            findings.append(f"{relative}: breadcrumb element {index + 1} has empty text")
        if index % 2 == 1:
            if tag != "span" or label != "›" or href:
                findings.append(f"{relative}: separator {index + 1} must be span ›")
            continue
        is_last = index == len(elements) - 1
        if is_last:
            if tag != "span" or href or label == "›":
                findings.append(f"{relative}: current breadcrumb must be final non-link span")
        elif tag != "a" or not href:
            findings.append(f"{relative}: parent breadcrumb {index + 1} must be a non-empty link")

    schema_parser = BreadcrumbPageParser()
    schema_parser.feed(text)
    visible_items = [element for index, element in enumerate(elements) if index % 2 == 0]
    if len(schema_parser.items) != len(visible_items):
        findings.append(f"{relative}: schema parser item count differs from visible breadcrumb items")
    try:
        payload = breadcrumb_payload(schema_parser, DOMAIN)
    except ValueError as exc:
        findings.append(f"{relative}: {exc}")
        return
    if "noindex" not in schema_parser.robots.lower():
        if payload is None:
            findings.append(f"{relative}: indexable breadcrumb page must generate BreadcrumbList")
        else:
            items = payload.get("itemListElement")
            if not isinstance(items, list) or len(items) != len(visible_items):
                findings.append(f"{relative}: BreadcrumbList size differs from visible items")


def main() -> int:
    findings: list[str] = []
    required_files = (
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
    for path in required_files:
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
        findings.append("breadcrumbs.figmaName must remain 'Breadcrumbs'")
    if component.get("anatomy") != ["Container", "Link", "Separator", "Current"]:
        findings.append("Breadcrumbs anatomy differs from the approved contract")
    properties = component.get("properties", {})
    if properties.get("state") != EXPECTED_STATES:
        findings.append("Breadcrumbs states differ from the approved order")
    if properties.get("separator") != "chevron-right":
        findings.append("Breadcrumbs separator contract must remain chevron-right")
    if properties.get("wraps") != "boolean":
        findings.append("Breadcrumbs must expose wrapping as a boolean property")
    if component.get("dimensions") != EXPECTED_DIMENSIONS:
        findings.append("Breadcrumbs dimensions differ from the approved contract")
    if component.get("accessibility") != EXPECTED_ACCESSIBILITY:
        findings.append("Breadcrumbs accessibility contract differs from the approved contract")

    manifest_state = manifest.get("components", {}).get("Breadcrumbs", {})
    if manifest_state != {"nodeId": None, "status": "pending"}:
        findings.append("Figma Breadcrumbs must remain pending with null nodeId")

    css = PRODUCTION_CSS.read_text(encoding="utf-8")
    for marker in REQUIRED_CSS:
        if marker not in css:
            findings.append(f"Breadcrumbs CSS is missing marker: {marker}")
    for pattern in FORBIDDEN_CSS_PATTERNS:
        if pattern.search(css):
            findings.append(f"Breadcrumbs CSS contains forbidden raw/legacy color: {pattern.pattern}")
    if css.count(".breadcrumbs {") != 2:
        findings.append("Breadcrumbs CSS must contain base and mobile container blocks")

    try:
        modules = load_css_modules(BUNDLE)
    except (SyntaxError, ValueError) as exc:
        findings.append(str(exc))
        modules = ()
    if modules:
        if modules.count("breadcrumbs-polish.css") != 1:
            findings.append("breadcrumbs-polish.css must appear exactly once in CSS_MODULES")
        expected_tail = (
            "choice-chip-polish.css",
            "back-to-top-polish.css",
            "breadcrumbs-polish.css",
            "logo-brand.css",
        )
        if tuple(modules[-4:]) != expected_tail:
            findings.append("Breadcrumbs bundle order differs from the approved tail")

    catalog = CATALOG.read_text(encoding="utf-8")
    catalog_css = CATALOG_CSS.read_text(encoding="utf-8")
    for marker in (
        'href="./components-v1-breadcrumbs.css"',
        'id="breadcrumbs"',
        "Breadcrumbs",
        "default · hover · focus",
        "breadcrumbs-specimen is-hover",
        "breadcrumbs-specimen is-focus",
        "breadcrumbs-specimen__separator">›<",
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
        "@media (prefers-reduced-motion: reduce)",
    ):
        if marker not in catalog_css:
            findings.append(f"Breadcrumbs catalog CSS is missing marker: {marker}")
    for pattern in FORBIDDEN_CSS_PATTERNS:
        if pattern.search(catalog_css):
            findings.append(f"Breadcrumbs catalog CSS contains forbidden raw/legacy color: {pattern.pattern}")

    breadcrumb_pages = 0
    for html_file in public_html_files():
        text = html_file.read_text(encoding="utf-8")
        if 'class="breadcrumbs"' not in text:
            continue
        breadcrumb_pages += 1
        validate_visible_breadcrumbs(html_file, text, findings)
    if breadcrumb_pages < 20:
        findings.append(f"expected at least 20 public breadcrumb pages, found {breadcrumb_pages}")

    generator_text = SCHEMA_GENERATOR.read_text(encoding="utf-8")
    for marker in (
        'GENERATED_MARKER = "data-generated-breadcrumbs"',
        'SEPARATORS = {"›", ">", "→", "/", "»"}',
        'if lowered == "div" and "breadcrumbs" in attrs.get("class", "").split():',
        '"@type": "BreadcrumbList"',
        "inject_breadcrumb_schemas",
    ):
        if marker not in generator_text:
            findings.append(f"BreadcrumbList generator is missing marker: {marker}")

    schema_check_text = SCHEMA_CHECK.read_text(encoding="utf-8")
    for marker in (
        "Breadcrumb schema self-test passed",
        "Циклёвка паркета",
        "expected one indexable breadcrumb schema",
    ):
        if marker not in schema_check_text:
            findings.append(f"Breadcrumb schema self-test is missing marker: {marker}")

    runner_text = RUNNER.read_text(encoding="utf-8")
    for marker in (
        'tools/check_breadcrumbs_token_migration.py',
        'tools/check_breadcrumb_schema.py',
    ):
        if marker not in runner_text:
            findings.append(f"quality runner is missing Breadcrumbs check: {marker}")

    doc = DOC.read_text(encoding="utf-8")
    production_doc = PRODUCTION_DOC.read_text(encoding="utf-8")
    for marker in (
        "40 px",
        "разделитель `›`",
        "текущий пункт без ссылки",
        "flex-wrap: wrap",
        "BreadcrumbList",
        "breadcrumbs-polish.css",
        "HTML-анатомия публичных страниц",
    ):
        if marker.lower() not in doc.lower():
            findings.append(f"Breadcrumbs documentation is missing marker: {marker}")
    for marker in (
        "css/breadcrumbs-polish.css",
        "BreadcrumbList JSON-LD",
        "Breadcrumbs",
    ):
        if marker.lower() not in production_doc.lower():
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
