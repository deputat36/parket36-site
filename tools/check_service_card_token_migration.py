#!/usr/bin/env python3
"""Validate the production Service Card token migration."""

from __future__ import annotations

import ast
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ENHANCEMENTS_CSS = ROOT / "css" / "enhancements.css"
STYLE_CSS = ROOT / "css" / "style.css"
BUNDLE = ROOT / "tools" / "css_bundle.py"
CONTRACT = ROOT / "design" / "components" / "parket36-components.json"
DOC = ROOT / "docs" / "design" / "parket36-service-card-token-migration-v1.md"
BLOCK_MARKER = "/* Design system v1: tokenized Service Card. */"
RAW_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}|rgba?\(")
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class ServiceCardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, bool]] = []
        self.card_count = 0
        self.hrefs: list[str] = []
        self.images_without_alt: list[str] = []
        self.icon_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        parent_inside = self.stack[-1][1] if self.stack else False
        is_card = "service-card" in classes
        inside = parent_inside or is_card

        if is_card:
            self.card_count += 1
        if inside and tag == "a":
            self.hrefs.append((values.get("href") or "").strip())
        if inside and tag == "img" and not (values.get("alt") or "").strip():
            self.images_without_alt.append(values.get("src") or "<unknown>")
        if inside and "service-card__icon" in classes:
            self.icon_count += 1

        if tag not in VOID_TAGS:
            self.stack.append((tag, inside))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return


def load_literal_assignment(path: Path, name: str) -> object:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if name in targets:
            return ast.literal_eval(node.value)
    raise ValueError(f"{name} assignment is missing in {path.relative_to(ROOT)}")


def main() -> int:
    findings: list[str] = []
    required = (ENHANCEMENTS_CSS, STYLE_CSS, BUNDLE, CONTRACT, DOC)
    for path in required:
        if not path.is_file():
            findings.append(f"missing Service Card migration asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Service Card component contract is invalid: {exc}")
        return 1

    component = contract.get("components", {}).get("serviceCard", {})
    properties = component.get("properties", {})
    dimensions = component.get("dimensions", {})
    accessibility = component.get("accessibility", {})

    if component.get("figmaName") != "Service Card":
        findings.append("Service Card figmaName must remain 'Service Card'")
    if component.get("anatomy") != ["Media", "Icon", "Body", "Title", "Description"]:
        findings.append("Service Card anatomy differs from the approved contract")
    if properties.get("variant") != ["compact", "media"]:
        findings.append("Service Card variants must remain compact and media")
    if properties.get("state") != ["default", "hover", "focus"]:
        findings.append("Service Card states must remain default, hover and focus")
    if dimensions.get("minimumHeight") != 192:
        findings.append("Service Card minimumHeight must remain 192 px")
    if dimensions.get("padding") != 24:
        findings.append("Service Card padding must remain 24 px")
    if dimensions.get("mediaAspectRatio") != "1000/760":
        findings.append("Service Card mediaAspectRatio must remain 1000/760")
    if dimensions.get("radiusToken") != "radius.lg":
        findings.append("Service Card radius must remain bound to radius.lg")
    for key in ("entireCardClickable", "focusVisible", "descriptiveLabelRequired", "imageAltRequired"):
        if accessibility.get(key) is not True:
            findings.append(f"Service Card accessibility flag must remain true: {key}")

    css = ENHANCEMENTS_CSS.read_text(encoding="utf-8")
    if css.count(BLOCK_MARKER) != 1:
        findings.append("enhancements.css must contain exactly one tokenized Service Card block")
        block = ""
    else:
        block = css.split(BLOCK_MARKER, 1)[1]

    required_markers = (
        ".service-card a {",
        "display: grid;",
        "min-height: 192px;",
        "padding: var(--p36-spacing-xl);",
        "border: 1px solid var(--p36-color-semantic-border-default);",
        "border-radius: var(--p36-radius-lg);",
        "background: var(--p36-color-semantic-surface-default);",
        "box-shadow: var(--p36-shadow-card);",
        ".service-card a:hover {",
        "background: var(--p36-color-semantic-surface-subtle);",
        "box-shadow: var(--p36-shadow-floating);",
        ".service-card a:focus-visible {",
        "outline: 3px solid var(--p36-color-primitive-brass-200);",
        ".service-card img {",
        "aspect-ratio: 1000 / 760;",
        "object-fit: cover;",
        ".service-card__icon {",
        "background: var(--p36-color-semantic-surface-accent);",
        "color: var(--p36-color-semantic-text-warm);",
        "@media (prefers-reduced-motion: reduce)",
        "transform: none;",
    )
    for marker in required_markers:
        if marker not in block:
            findings.append(f"tokenized Service Card block is missing marker: {marker}")

    if RAW_COLOR_RE.search(block):
        findings.append("tokenized Service Card block must not contain raw hex/rgb colors")
    for forbidden in (
        "var(--wood)",
        "var(--gold)",
        "var(--line)",
        "var(--radius)",
        "var(--shadow)",
        "font-weight: 900",
    ):
        if forbidden in block:
            findings.append(f"tokenized Service Card block contains legacy value: {forbidden}")

    style_css = STYLE_CSS.read_text(encoding="utf-8")
    for marker in (
        ".services-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}",
        ".services-grid,.services-grid--featured{grid-template-columns:repeat(2,1fr)}",
        ".services-grid,.services-grid--featured,.scenario-grid,.price-grid,.steps,.portfolio-grid,.footer__grid{grid-template-columns:1fr}",
    ):
        if marker not in style_css:
            findings.append(f"Service Card responsive grid marker is missing: {marker}")

    try:
        css_modules = load_literal_assignment(BUNDLE, "CSS_MODULES")
    except (SyntaxError, ValueError) as exc:
        findings.append(str(exc))
        css_modules = ()
    if isinstance(css_modules, tuple):
        try:
            style_index = css_modules.index("style.css")
            enhancements_index = css_modules.index("enhancements.css")
        except ValueError as exc:
            findings.append(f"CSS module order is incomplete: {exc}")
        else:
            if enhancements_index <= style_index:
                findings.append("enhancements.css must load after style.css")

    parser = ServiceCardParser()
    html_files = [
        path
        for path in sorted(ROOT.rglob("*.html"))
        if "_site" not in path.parts and "node_modules" not in path.parts
    ]
    for path in html_files:
        parser.feed(path.read_text(encoding="utf-8"))

    if parser.card_count < 6:
        findings.append(f"expected at least 6 production Service Cards, found {parser.card_count}")
    if len(parser.hrefs) != parser.card_count:
        findings.append(
            f"every Service Card must contain exactly one link: {len(parser.hrefs)} links for {parser.card_count} cards"
        )
    for href in parser.hrefs:
        if not href or href == "#" or href.lower().startswith("javascript:"):
            findings.append(f"Service Card contains an invalid href: {href!r}")
    for source in parser.images_without_alt:
        findings.append(f"Service Card image is missing alt: {source}")
    if parser.icon_count < 6:
        findings.append(f"expected compact Service Card icons to remain present; found {parser.icon_count}")

    doc = DOC.read_text(encoding="utf-8").lower()
    for marker in (
        "миграция service card на токены",
        "`compact`",
        "`media`",
        "минимальная высота — 192 px",
        "соотношение изображения — `1000/760`",
        "осмысленный `alt`",
        "prefers-reduced-motion",
        "supabase",
    ):
        if marker not in doc:
            findings.append(f"Service Card migration documentation is missing marker: {marker}")

    if findings:
        print("Service Card token migration findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print(
        "Service Card token migration passed "
        f"({parser.card_count} cards, {len(parser.hrefs)} links, {parser.icon_count} icons)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
