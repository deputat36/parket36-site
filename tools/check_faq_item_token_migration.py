#!/usr/bin/env python3
"""Validate the production FAQ Item token migration."""

from __future__ import annotations

import ast
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TYPOGRAPHY_CSS = ROOT / "css" / "typography-polish.css"
STYLE_CSS = ROOT / "css" / "style.css"
BUNDLE = ROOT / "tools" / "css_bundle.py"
CONTRACT = ROOT / "design" / "components" / "parket36-components.json"
PAGE = ROOT / "voprosy-i-otvety" / "index.html"
DOC = ROOT / "docs" / "design" / "parket36-faq-item-token-migration-v1.md"
BLOCK_MARKER = "/* Design system v1: tokenized FAQ Item. */"
RAW_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}|rgba?\(")
JSON_LD_RE = re.compile(
    r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)


class FaqParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, bool]] = []
        self.items: list[dict[str, object]] = []
        self.current: dict[str, object] | None = None
        self.capture: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        parent_inside_faq = self.stack[-1][1] if self.stack else False
        inside_faq = parent_inside_faq or "faq" in classes
        self.stack.append((tag, inside_faq))

        if tag == "details" and inside_faq:
            self.current = {
                "open": "open" in values,
                "summary": "",
                "answer": "",
                "summary_count": 0,
                "answer_count": 0,
            }
            self.items.append(self.current)
        elif self.current is not None and tag == "summary":
            self.current["summary_count"] = int(self.current["summary_count"]) + 1
            self.capture = "summary"
        elif self.current is not None and tag == "p":
            self.current["answer_count"] = int(self.current["answer_count"]) + 1
            self.capture = "answer"

    def handle_data(self, data: str) -> None:
        if self.current is None or self.capture is None:
            return
        current_text = str(self.current[self.capture])
        self.current[self.capture] = f"{current_text} {data}".strip()

    def handle_endtag(self, tag: str) -> None:
        if tag in {"summary", "p"}:
            self.capture = None
        if tag == "details":
            self.current = None
            self.capture = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def load_literal_assignment(path: Path, name: str) -> object:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if name in targets:
            return ast.literal_eval(node.value)
    raise ValueError(f"{name} assignment is missing in {path.relative_to(ROOT)}")


def find_faq_schema(html: str) -> dict[str, object] | None:
    for match in JSON_LD_RE.finditer(html):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        candidates: list[object] = []
        if isinstance(payload, dict):
            candidates.append(payload)
            graph = payload.get("@graph")
            if isinstance(graph, list):
                candidates.extend(graph)
        for candidate in candidates:
            if isinstance(candidate, dict) and candidate.get("@type") == "FAQPage":
                return candidate
    return None


def main() -> int:
    findings: list[str] = []
    required = (TYPOGRAPHY_CSS, STYLE_CSS, BUNDLE, CONTRACT, PAGE, DOC)
    for path in required:
        if not path.is_file():
            findings.append(f"missing FAQ Item migration asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAQ Item component contract is invalid: {exc}")
        return 1

    component = contract.get("components", {}).get("faqItem", {})
    properties = component.get("properties", {})
    dimensions = component.get("dimensions", {})
    accessibility = component.get("accessibility", {})

    if component.get("figmaName") != "FAQ Item":
        findings.append("FAQ Item figmaName must remain 'FAQ Item'")
    if component.get("anatomy") != ["Container", "Trigger", "Question", "Indicator", "Answer"]:
        findings.append("FAQ Item anatomy differs from the approved contract")
    if properties.get("state") != ["closed", "open", "hover", "focus"]:
        findings.append("FAQ Item states must remain closed, open, hover and focus")
    if dimensions.get("minimumTriggerHeight") != 52:
        findings.append("FAQ Item minimumTriggerHeight must remain 52 px")
    if dimensions.get("indicatorSize") != 32:
        findings.append("FAQ Item indicatorSize must remain 32 px")
    if dimensions.get("radiusToken") != "radius.lg":
        findings.append("FAQ Item radius must remain bound to radius.lg")
    for key in ("nativeDetailsRequired", "focusVisible", "indicatorNotColorOnly"):
        if accessibility.get(key) is not True:
            findings.append(f"FAQ Item accessibility flag must remain true: {key}")
    if accessibility.get("minimumTouchTarget") != 44:
        findings.append("FAQ Item minimumTouchTarget must remain 44 px")

    css = TYPOGRAPHY_CSS.read_text(encoding="utf-8")
    if css.count(BLOCK_MARKER) != 1:
        findings.append("typography-polish.css must contain exactly one tokenized FAQ Item block")
        block = ""
    else:
        block = css.split(BLOCK_MARKER, 1)[1]

    required_markers = (
        ".faq details {",
        "margin: 0 0 var(--p36-spacing-md);",
        "border: 1px solid var(--p36-color-semantic-border-default);",
        "border-radius: var(--p36-radius-lg);",
        "background: var(--p36-color-semantic-surface-default);",
        "box-shadow: var(--p36-shadow-card);",
        ".faq details:hover {",
        "box-shadow: var(--p36-shadow-floating);",
        ".faq details[open] {",
        "background: var(--p36-color-semantic-surface-subtle);",
        ".faq summary {",
        "min-height: 52px;",
        "grid-template-columns: minmax(0, 1fr) 32px;",
        ".faq summary::after {",
        'content: "+";',
        '.faq details[open] summary::after {',
        'content: "−";',
        ".faq summary:focus-visible {",
        "outline: 3px solid var(--p36-color-primitive-brass-200);",
        ".faq details > p {",
        "@media (prefers-reduced-motion: reduce)",
        "transition: none;",
    )
    for marker in required_markers:
        if marker not in block:
            findings.append(f"tokenized FAQ Item block is missing marker: {marker}")

    if RAW_COLOR_RE.search(block):
        findings.append("tokenized FAQ Item block must not contain raw hex/rgb colors")
    for forbidden in (
        "var(--wood)",
        "var(--gold)",
        "var(--line)",
        "var(--radius)",
        "var(--shadow)",
        "font-weight: 900",
    ):
        if forbidden in block:
            findings.append(f"tokenized FAQ Item block contains legacy value: {forbidden}")

    style_css = STYLE_CSS.read_text(encoding="utf-8")
    for marker in (".faq details{", ".faq summary{", ".faq p{"):
        if marker not in style_css:
            findings.append(f"legacy FAQ base marker is missing: {marker}")

    try:
        css_modules = load_literal_assignment(BUNDLE, "CSS_MODULES")
    except (SyntaxError, ValueError) as exc:
        findings.append(str(exc))
        css_modules = ()
    if isinstance(css_modules, tuple):
        try:
            style_index = css_modules.index("style.css")
            typography_index = css_modules.index("typography-polish.css")
        except ValueError as exc:
            findings.append(f"CSS module order is incomplete: {exc}")
        else:
            if typography_index <= style_index:
                findings.append("typography-polish.css must load after style.css")

    html = PAGE.read_text(encoding="utf-8")
    parser = FaqParser()
    parser.feed(html)

    if len(parser.items) != 16:
        findings.append(f"expected exactly 16 production FAQ Items, found {len(parser.items)}")
    open_count = sum(1 for item in parser.items if item["open"])
    if open_count != 4:
        findings.append(f"expected exactly 4 FAQ Items open by default, found {open_count}")

    for index, item in enumerate(parser.items, start=1):
        if item["summary_count"] != 1:
            findings.append(f"FAQ Item {index} must contain exactly one summary")
        if item["answer_count"] != 1:
            findings.append(f"FAQ Item {index} must contain exactly one paragraph answer")
        if not str(item["summary"]).strip():
            findings.append(f"FAQ Item {index} has an empty question")
        if not str(item["answer"]).strip():
            findings.append(f"FAQ Item {index} has an empty answer")

    schema = find_faq_schema(html)
    if schema is None:
        findings.append("voprosy-i-otvety must contain valid FAQPage JSON-LD")
        schema_items: list[object] = []
    else:
        raw_items = schema.get("mainEntity")
        schema_items = raw_items if isinstance(raw_items, list) else []
        if len(schema_items) < 5:
            findings.append("FAQPage JSON-LD must retain at least five questions")
    for index, item in enumerate(schema_items, start=1):
        if not isinstance(item, dict) or item.get("@type") != "Question":
            findings.append(f"FAQPage entity {index} must be a Question")
            continue
        answer = item.get("acceptedAnswer")
        if not isinstance(answer, dict) or answer.get("@type") != "Answer":
            findings.append(f"FAQPage entity {index} must contain an accepted Answer")

    doc = DOC.read_text(encoding="utf-8").lower()
    for marker in (
        "production-миграция faq item",
        "16 вопросов",
        "четыре вопроса",
        "`<details>`",
        "`<summary>`",
        "минимальная высота trigger — 52 px",
        "faqpage",
        "prefers-reduced-motion",
        "supabase",
        "nodeid: null",
    ):
        if marker not in doc:
            findings.append(f"FAQ Item migration documentation is missing marker: {marker}")

    if findings:
        print("FAQ Item token migration findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print(
        "FAQ Item token migration passed "
        f"({len(parser.items)} items, {open_count} open, {len(schema_items)} schema questions)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
