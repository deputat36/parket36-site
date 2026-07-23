#!/usr/bin/env python3
"""Validate the tokenized non-interactive Proof Card component."""

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
CATALOG_CSS = ROOT / "design" / "prototypes" / "components-v1-proof-card.css"
PRODUCTION_CSS = ROOT / "css" / "proof-card-polish.css"
BUNDLE = ROOT / "tools" / "css_bundle.py"
DOC = ROOT / "docs" / "design" / "parket36-proof-card-token-migration-v1.md"
PRODUCTION_DOC = ROOT / "docs" / "design" / "parket36-production-token-layer-v1.md"

EXPECTED_DIMENSIONS = {
    "minimumHeight": 156,
    "padding": 24,
    "gap": 10,
    "accentWidth": 48,
    "accentHeight": 4,
    "radiusToken": "radius.lg",
}
EXPECTED_ACCESSIBILITY = {
    "semanticArticlePreferred": True,
    "nonInteractive": True,
    "linksForbidden": True,
    "buttonRoleForbidden": True,
    "tabindexForbidden": True,
    "hoverTransformForbidden": True,
    "titleRequired": True,
    "descriptionRequired": True,
}
EXPECTED_PAGE_COUNTS = {
    "index.html": 6,
    "kak-rabotaem/index.html": 6,
    "resheniya/index.html": 6,
    "resheniya/dlya-rieltorov-i-sobstvennikov/index.html": 6,
    "uslugi/melkiy-remont/index.html": 3,
}
REQUIRED_CSS = (
    "/* Tokenized Proof Card:",
    ".proof-card {",
    "min-height: 156px",
    "border: 1px solid var(--p36-color-semantic-border-default)",
    "border-radius: var(--p36-radius-lg)",
    "background: var(--p36-color-semantic-surface-default)",
    "box-shadow: var(--p36-shadow-card)",
    "cursor: default",
    "transform: none",
    ".proof-card::before",
    "width: 48px",
    "height: 4px",
    "background: var(--p36-color-semantic-action-secondary)",
    ".proof-card strong",
    "font-weight: var(--p36-font-weight-extrabold)",
    ".proof-card p",
    "color: var(--p36-color-semantic-text-secondary)",
    ".proof-card:hover",
    "@media (max-width: 640px)",
    "@media (prefers-reduced-motion: reduce)",
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


class ProofCardParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.cards: list[dict[str, Any]] = []
        self.current: dict[str, Any] | None = None
        self.active_text: str | None = None
        self.chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key: value or "" for key, value in attrs_list}
        classes = set(attrs.get("class", "").split())
        if tag == "article" and "proof-card" in classes and self.current is None:
            self.current = {
                "tag": tag,
                "strong": [],
                "p": [],
                "interactive": [],
                "tabindex": "tabindex" in attrs,
                "role": attrs.get("role", ""),
            }
            self.depth = 1
            return
        if self.current is None:
            return
        self.depth += 1
        if tag in {"a", "button", "input", "select", "textarea"}:
            self.current["interactive"].append(tag)
        if "tabindex" in attrs:
            self.current["tabindex"] = True
        if attrs.get("role", "") in {"button", "link"}:
            self.current["role"] = attrs["role"]
        if tag in {"strong", "p"}:
            self.active_text = tag
            self.chunks = []

    def handle_data(self, data: str) -> None:
        if self.current is not None and self.active_text:
            self.chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.current is None:
            return
        if self.active_text == tag:
            text = " ".join("".join(self.chunks).split())
            self.current[tag].append(text)
            self.active_text = None
            self.chunks = []
        self.depth -= 1
        if self.depth == 0:
            self.cards.append(self.current)
            self.current = None


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


def validate_page(path: Path, expected: int, findings: list[str]) -> None:
    parser = ProofCardParser()
    parser.feed(path.read_text(encoding="utf-8"))
    relative = path.relative_to(ROOT).as_posix()
    if len(parser.cards) != expected:
        findings.append(f"{relative}: expected {expected} Proof Cards, found {len(parser.cards)}")
    for index, card in enumerate(parser.cards, start=1):
        label = f"{relative} Proof Card {index}"
        if card["tag"] != "article":
            findings.append(f"{label} must remain an article")
        if len(card["strong"]) != 1 or not card["strong"][0]:
            findings.append(f"{label} must contain one non-empty strong title")
        if len(card["p"]) != 1 or not card["p"][0]:
            findings.append(f"{label} must contain one non-empty paragraph")
        if card["interactive"]:
            findings.append(f"{label} contains interactive elements: {card['interactive']}")
        if card["tabindex"]:
            findings.append(f"{label} must not define tabindex")
        if card["role"] in {"button", "link"}:
            findings.append(f"{label} must not use role={card['role']}")


def main() -> int:
    findings: list[str] = []
    required = (CONTRACT, MANIFEST, CATALOG, CATALOG_CSS, PRODUCTION_CSS, BUNDLE, DOC, PRODUCTION_DOC)
    for path in required:
        if not path.is_file():
            findings.append(f"missing Proof Card asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        contract = read_json(CONTRACT)
        manifest = read_json(MANIFEST)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Proof Card JSON is invalid: {exc}")
        return 1

    component = contract.get("components", {}).get("proofCard", {})
    if component.get("figmaName") != "Proof Card":
        findings.append("proofCard.figmaName must remain 'Proof Card'")
    if component.get("anatomy") != ["Accent", "Title", "Description"]:
        findings.append("Proof Card anatomy must remain Accent + Title + Description")
    properties = component.get("properties", {})
    if properties != {"title": "text", "description": "text", "interactive": False}:
        findings.append("Proof Card properties differ from the approved non-interactive contract")
    if component.get("dimensions") != EXPECTED_DIMENSIONS:
        findings.append("Proof Card dimensions differ from the approved contract")
    if component.get("accessibility") != EXPECTED_ACCESSIBILITY:
        findings.append("Proof Card accessibility contract differs from the approved contract")

    state = manifest.get("components", {}).get("Proof Card", {})
    if state != {"nodeId": None, "status": "pending"}:
        findings.append("Figma Proof Card must remain pending with null nodeId")

    css = PRODUCTION_CSS.read_text(encoding="utf-8")
    for marker in REQUIRED_CSS:
        if marker not in css:
            findings.append(f"Proof Card CSS is missing marker: {marker}")
    for pattern in FORBIDDEN_CSS_PATTERNS:
        if pattern.search(css):
            findings.append(f"Proof Card CSS contains forbidden interactive/raw marker: {pattern.pattern}")
    if css.count(".proof-card {") != 2:
        findings.append("Proof Card CSS must contain base and mobile container blocks")
    if ".proof-card:hover" not in css or "transform: none" not in css:
        findings.append("Proof Card CSS must explicitly neutralize legacy hover transform")

    try:
        modules = load_css_modules(BUNDLE)
    except (SyntaxError, ValueError) as exc:
        findings.append(str(exc))
        modules = ()
    if modules:
        expected_tail = (
            "back-to-top-polish.css",
            "breadcrumbs-polish.css",
            "proof-card-polish.css",
            "logo-brand.css",
        )
        if tuple(modules[-4:]) != expected_tail:
            findings.append("Proof Card bundle order differs from the approved tail")
        if modules.count("proof-card-polish.css") != 1:
            findings.append("proof-card-polish.css must appear exactly once in CSS_MODULES")

    catalog = CATALOG.read_text(encoding="utf-8")
    catalog_css = CATALOG_CSS.read_text(encoding="utf-8")
    for marker in (
        'href="./components-v1-proof-card.css"',
        'id="proof-cards"',
        "Proof Card",
        "non-interactive · article",
        'class="proof-card-specimen-grid"',
        'class="proof-card-specimen"',
        "proof-card-specimen proof-card-specimen--long",
    ):
        if marker not in catalog:
            findings.append(f"Proof Card catalog is missing marker: {marker}")
    if catalog.count("<article class=\"proof-card-specimen") != 3:
        findings.append("Proof Card catalog must contain exactly three article specimens")
    if '<a class="proof-card-specimen' in catalog or '<button class="proof-card-specimen' in catalog:
        findings.append("Proof Card catalog specimens must not be interactive")
    for marker in (
        ".proof-card-specimen-grid",
        ".proof-card-specimen {",
        "min-height: 156px",
        "var(--p36-radius-lg)",
        "var(--p36-shadow-card)",
        "var(--p36-color-semantic-action-secondary)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        if marker not in catalog_css:
            findings.append(f"Proof Card catalog CSS is missing marker: {marker}")
    for pattern in FORBIDDEN_CSS_PATTERNS:
        if pattern.search(catalog_css):
            findings.append(f"Proof Card catalog CSS contains forbidden marker: {pattern.pattern}")

    for relative, expected in EXPECTED_PAGE_COUNTS.items():
        validate_page(ROOT / relative, expected, findings)

    discovered = []
    for html_file in sorted(ROOT.rglob("*.html")):
        if any(part in {".git", "_site", "node_modules"} for part in html_file.parts):
            continue
        text = html_file.read_text(encoding="utf-8")
        if 'class="proof-card"' in text:
            discovered.append(html_file.relative_to(ROOT).as_posix())
    if discovered != list(EXPECTED_PAGE_COUNTS):
        findings.append(f"Proof Card page inventory changed: {discovered}")

    doc = DOC.read_text(encoding="utf-8")
    production_doc = PRODUCTION_DOC.read_text(encoding="utf-8")
    for marker in (
        "27 элементов",
        "пяти публичных страницах",
        "hover-transform",
        "transform: none",
        "proof-card-polish.css",
        "JavaScript",
        "nodeId",
        "pending",
    ):
        if marker.lower() not in doc.lower():
            findings.append(f"Proof Card documentation is missing marker: {marker}")
    for marker in ("css/proof-card-polish.css", "Proof Card", "неинтерактив"):
        if marker.lower() not in production_doc.lower():
            findings.append(f"production token documentation is missing Proof Card marker: {marker}")

    if findings:
        print("Proof Card token migration findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Proof Card token migration passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
