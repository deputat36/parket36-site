#!/usr/bin/env python3
"""Validate the tokenized, ordered and non-interactive Process Step component."""

from __future__ import annotations

import ast
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "design" / "components" / "parket36-components.json"
MANIFEST = ROOT / "design" / "figma" / "parket36-sync-manifest.json"
CATALOG = ROOT / "design" / "prototypes" / "components-v1.htm"
CATALOG_CSS = ROOT / "design" / "prototypes" / "components-v1-process-step.css"
PRODUCTION_CSS = ROOT / "css" / "process-step-polish.css"
BUNDLE = ROOT / "tools" / "css_bundle.py"
RUNNER = ROOT / "tools" / "run_quality_checks.py"
DOC = ROOT / "docs" / "design" / "parket36-process-step-token-migration-v1.md"
PRODUCTION_DOC = ROOT / "docs" / "design" / "parket36-production-token-layer-v1.md"

EXPECTED_PAGE_COUNT = 86
EXPECTED_DIMENSIONS = {
    "minimumHeight": 164,
    "paddingTop": 64,
    "horizontalPadding": 24,
    "bottomPadding": 24,
    "gridGap": 16,
    "numberSize": 36,
    "radiusToken": "radius.lg",
}
EXPECTED_ACCESSIBILITY = {
    "nativeOrderedListRequired": True,
    "semanticListItemRequired": True,
    "nonInteractive": True,
    "linksForbidden": True,
    "buttonRoleForbidden": True,
    "tabindexForbidden": True,
    "hoverTransformForbidden": True,
    "titleRequired": True,
    "descriptionRequired": True,
}
SKIP_PARTS = {".git", "_site", "design", "node_modules", "vendor"}
SCRIPT_RE = re.compile(
    r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
FORBIDDEN_CSS_PATTERNS = (
    re.compile(r"#[0-9a-fA-F]{3,8}\b"),
    re.compile(r"\brgba?\("),
    re.compile(r"\bhsla?\("),
    re.compile(r"translate[XY]?\("),
    re.compile(r"cursor\s*:\s*pointer"),
    re.compile(r"var\(--wood\)"),
    re.compile(r"var\(--gold\)"),
)
REQUIRED_CSS = (
    "/* Tokenized Process Step:",
    ".steps {",
    "grid-template-columns: repeat(3, minmax(0, 1fr))",
    "gap: var(--p36-spacing-lg)",
    "counter-reset: step",
    ".steps li {",
    "min-height: 164px",
    "padding: var(--p36-spacing-4xl) var(--p36-spacing-xl) var(--p36-spacing-xl)",
    "border: 1px solid var(--p36-color-semantic-border-default)",
    "border-radius: var(--p36-radius-lg)",
    "background: var(--p36-color-semantic-surface-default)",
    "box-shadow: var(--p36-shadow-card)",
    "cursor: default",
    "transform: none",
    ".steps li::before",
    "counter-increment: step",
    "content: counter(step)",
    "width: 36px",
    "height: 36px",
    "background: var(--p36-color-semantic-action-primary)",
    "color: var(--p36-color-semantic-text-inverse)",
    ".steps strong",
    "font-size: var(--p36-font-size-lead)",
    ".steps span",
    "color: var(--p36-color-semantic-text-secondary)",
    ".steps li:hover",
    "@media (max-width: 640px)",
    "grid-template-columns: 1fr",
    "@media (prefers-reduced-motion: reduce)",
)


class StepsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lists: list[dict[str, Any]] = []
        self.current_list: dict[str, Any] | None = None
        self.list_depth = 0
        self.current_item: dict[str, Any] | None = None
        self.item_depth = 0
        self.capture: str | None = None
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_list}
        classes = set(attrs.get("class", "").split())

        if tag == "ol" and "steps" in classes and self.current_list is None:
            self.current_list = {
                "tag": tag,
                "items": [],
                "tabindex": "tabindex" in attrs,
                "role": attrs.get("role", ""),
            }
            self.list_depth = 1
            return

        if self.current_list is None:
            return

        self.list_depth += 1
        if tag == "li" and self.current_item is None:
            self.current_item = {
                "tag": tag,
                "strong": [],
                "span": [],
                "interactive": [],
                "tabindex": "tabindex" in attrs,
                "role": attrs.get("role", ""),
            }
            self.item_depth = 1
            return

        if self.current_item is None:
            return

        self.item_depth += 1
        if tag in {"a", "button", "input", "select", "textarea"}:
            self.current_item["interactive"].append(tag)
        if "tabindex" in attrs:
            self.current_item["tabindex"] = True
        if attrs.get("role", "") in {"button", "link"}:
            self.current_item["role"] = attrs["role"]
        if tag in {"strong", "span"}:
            self.capture = tag
            self.chunks = []

    def handle_data(self, data: str) -> None:
        if self.current_item is not None and self.capture:
            self.chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.current_list is None:
            return

        if self.current_item is not None:
            if self.capture == tag:
                text = " ".join("".join(self.chunks).split())
                self.current_item[tag].append(text)
                self.capture = None
                self.chunks = []
            self.item_depth -= 1
            if self.item_depth == 0:
                self.current_list["items"].append(self.current_item)
                self.current_item = None

        self.list_depth -= 1
        if self.list_depth == 0:
            self.lists.append(self.current_list)
            self.current_list = None


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
    result: list[Path] = []
    for path in ROOT.rglob("*.html"):
        relative = path.relative_to(ROOT)
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        result.append(path)
    return sorted(result)


def howto_step_counts(value: Any) -> list[int]:
    counts: list[int] = []
    if isinstance(value, dict):
        item_type = value.get("@type")
        is_howto = item_type == "HowTo" or (
            isinstance(item_type, list) and "HowTo" in item_type
        )
        if is_howto:
            steps = value.get("step", [])
            if isinstance(steps, list):
                count = sum(
                    1
                    for step in steps
                    if isinstance(step, dict)
                    and (
                        step.get("@type") == "HowToStep"
                        or (
                            isinstance(step.get("@type"), list)
                            and "HowToStep" in step.get("@type", [])
                        )
                    )
                )
                counts.append(count)
        for child in value.values():
            counts.extend(howto_step_counts(child))
    elif isinstance(value, list):
        for child in value:
            counts.extend(howto_step_counts(child))
    return counts


def validate_page(path: Path, text: str, findings: list[str]) -> tuple[int, int]:
    parser = StepsParser()
    parser.feed(text)
    relative = path.relative_to(ROOT).as_posix()
    if len(parser.lists) != 1:
        findings.append(f"{relative}: expected exactly one ol.steps, found {len(parser.lists)}")
        return len(parser.lists), 0

    process = parser.lists[0]
    if process["tag"] != "ol":
        findings.append(f"{relative}: Process Step container must remain an ol")
    if process["tabindex"]:
        findings.append(f"{relative}: ol.steps must not define tabindex")
    if process["role"] in {"button", "link"}:
        findings.append(f"{relative}: ol.steps must not use action role")

    items = process["items"]
    if not 3 <= len(items) <= 8:
        findings.append(f"{relative}: expected 3–8 process steps, found {len(items)}")
    for index, item in enumerate(items, start=1):
        label = f"{relative} Process Step {index}"
        if item["tag"] != "li":
            findings.append(f"{label} must remain a list item")
        if len(item["strong"]) != 1 or not item["strong"][0]:
            findings.append(f"{label} must contain one non-empty strong title")
        if len(item["span"]) != 1 or not item["span"][0]:
            findings.append(f"{label} must contain one non-empty span description")
        if item["interactive"]:
            findings.append(f"{label} contains interactive elements: {item['interactive']}")
        if item["tabindex"]:
            findings.append(f"{label} must not define tabindex")
        if item["role"] in {"button", "link"}:
            findings.append(f"{label} must not use role={item['role']}")

    counts: list[int] = []
    for payload_text in SCRIPT_RE.findall(text):
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            findings.append(f"{relative}: invalid JSON-LD while checking HowTo: {exc}")
            continue
        counts.extend(howto_step_counts(payload))
    if counts:
        if len(counts) != 1:
            findings.append(f"{relative}: expected one HowTo payload, found {len(counts)}")
        elif counts[0] != len(items):
            findings.append(
                f"{relative}: HowToStep count {counts[0]} differs from visible step count {len(items)}"
            )

    return 1, len(items)


def main() -> int:
    findings: list[str] = []
    required = (
        CONTRACT,
        MANIFEST,
        CATALOG,
        CATALOG_CSS,
        PRODUCTION_CSS,
        BUNDLE,
        RUNNER,
        DOC,
        PRODUCTION_DOC,
    )
    for path in required:
        if not path.is_file():
            findings.append(f"missing Process Step asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        contract = read_json(CONTRACT)
        manifest = read_json(MANIFEST)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Process Step JSON is invalid: {exc}")
        return 1

    component = contract.get("components", {}).get("processStep", {})
    if component.get("figmaName") != "Process Step":
        findings.append("processStep.figmaName must remain 'Process Step'")
    if component.get("anatomy") != ["Number", "Title", "Description"]:
        findings.append("Process Step anatomy must remain Number + Title + Description")
    if component.get("properties") != {
        "number": "generated-counter",
        "title": "text",
        "description": "text",
        "interactive": False,
    }:
        findings.append("Process Step properties differ from the approved contract")
    if component.get("dimensions") != EXPECTED_DIMENSIONS:
        findings.append("Process Step dimensions differ from the approved contract")
    if component.get("accessibility") != EXPECTED_ACCESSIBILITY:
        findings.append("Process Step accessibility differs from the approved contract")

    if manifest.get("components", {}).get("Process Step") != {
        "nodeId": None,
        "status": "pending",
    }:
        findings.append("Figma Process Step must remain pending with null nodeId")

    css = PRODUCTION_CSS.read_text(encoding="utf-8")
    for marker in REQUIRED_CSS:
        if marker not in css:
            findings.append(f"Process Step CSS is missing marker: {marker}")
    for pattern in FORBIDDEN_CSS_PATTERNS:
        if pattern.search(css):
            findings.append(f"Process Step CSS contains forbidden marker: {pattern.pattern}")
    if css.count(".steps {") != 2:
        findings.append("Process Step CSS must contain base and mobile grid blocks")
    if css.count(".steps li {") != 3:
        findings.append("Process Step CSS must contain base, mobile and reduced-motion item blocks")
    if ".steps li:hover" not in css or "transform: none" not in css:
        findings.append("Process Step CSS must explicitly neutralize hover transform")

    try:
        modules = load_css_modules(BUNDLE)
    except (SyntaxError, ValueError) as exc:
        findings.append(str(exc))
        modules = ()
    if modules:
        expected_tail = (
            "breadcrumbs-polish.css",
            "proof-card-polish.css",
            "process-step-polish.css",
            "logo-brand.css",
        )
        if tuple(modules[-4:]) != expected_tail:
            findings.append("Process Step bundle order differs from the approved tail")
        if modules.count("process-step-polish.css") != 1:
            findings.append("process-step-polish.css must appear exactly once in CSS_MODULES")

    catalog = CATALOG.read_text(encoding="utf-8")
    catalog_css = CATALOG_CSS.read_text(encoding="utf-8")
    for marker in (
        'href="./components-v1-process-step.css"',
        'id="process-steps"',
        "Process Step",
        "non-interactive · ordered list",
        '<ol class="process-step-specimen-grid"',
        'class="process-step-specimen"',
    ):
        if marker not in catalog:
            findings.append(f"Process Step catalog is missing marker: {marker}")
    if catalog.count('<li class="process-step-specimen">') != 3:
        findings.append("Process Step catalog must contain exactly three list item specimens")
    if '<a class="process-step-specimen' in catalog or '<button class="process-step-specimen' in catalog:
        findings.append("Process Step catalog specimens must not be interactive")
    for marker in (
        ".process-step-specimen-grid",
        "grid-template-columns: repeat(3, minmax(0, 1fr))",
        "counter-reset: process-step",
        ".process-step-specimen {",
        "min-height: 164px",
        "var(--p36-radius-lg)",
        "var(--p36-shadow-card)",
        "counter-increment: process-step",
        "var(--p36-color-semantic-action-primary)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        if marker not in catalog_css:
            findings.append(f"Process Step catalog CSS is missing marker: {marker}")
    for pattern in FORBIDDEN_CSS_PATTERNS:
        if pattern.search(catalog_css):
            findings.append(f"Process Step catalog CSS contains forbidden marker: {pattern.pattern}")

    page_count = 0
    list_count = 0
    item_count = 0
    for html_file in public_html_files():
        text = html_file.read_text(encoding="utf-8")
        if 'class="steps"' not in text:
            continue
        page_count += 1
        lists, items = validate_page(html_file, text, findings)
        list_count += lists
        item_count += items
    if page_count != EXPECTED_PAGE_COUNT:
        findings.append(
            f"Process Step page inventory changed: expected {EXPECTED_PAGE_COUNT}, found {page_count}"
        )
    if list_count != page_count:
        findings.append(f"Process Step list count {list_count} differs from page count {page_count}")

    runner_text = RUNNER.read_text(encoding="utf-8")
    if "tools/check_process_step_token_migration.py" not in runner_text:
        findings.append("quality runner is missing Process Step check")

    doc = DOC.read_text(encoding="utf-8").lower()
    production_doc = PRODUCTION_DOC.read_text(encoding="utf-8").lower()
    for marker in (
        "86 публичных страницах",
        "<ol class=\"steps\">",
        "css-counter",
        "hover-transform",
        "process-step-polish.css",
        "howto json-ld",
        "javascript",
        "nodeid",
        "pending",
    ):
        if marker.lower() not in doc:
            findings.append(f"Process Step documentation is missing marker: {marker}")
    for marker in ("css/process-step-polish.css", "Process Step", "HowTo"):
        if marker.lower() not in production_doc:
            findings.append(f"production token documentation is missing Process Step marker: {marker}")

    if findings:
        print("Process Step token migration findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print(
        f"Process Step token migration passed across {page_count} pages, "
        f"{list_count} ordered lists and {item_count} steps"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
