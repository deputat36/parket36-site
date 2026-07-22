#!/usr/bin/env python3
"""Validate the production Mobile CTA token migration."""

from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "css" / "cta-polish.css"
CONTRACT = ROOT / "design" / "components" / "parket36-components.json"
CATALOG = ROOT / "design" / "prototypes" / "components-v1.htm"
CATALOG_CSS = ROOT / "design" / "prototypes" / "components-v1-mobile-cta.css"
DOC = ROOT / "docs" / "design" / "parket36-mobile-cta-token-migration-v1.md"
BLOCK_MARKER = "/* Design system v1: tokenized Mobile CTA. */"
RAW_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}|rgba?\(")


class MobileCtaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.current_links: list[dict[str, str]] | None = None
        self.current_link: dict[str, str] | None = None
        self.bars: list[list[dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if self.current_links is None and "mobile-cta" in classes:
            self.current_links = []
            self.depth = 1
            return
        if self.current_links is not None:
            self.depth += 1
            if tag == "a":
                self.current_link = {"href": (values.get("href") or "").strip(), "text": ""}

    def handle_data(self, data: str) -> None:
        if self.current_link is not None:
            self.current_link["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if self.current_links is None:
            return
        if tag == "a" and self.current_link is not None:
            self.current_link["text"] = " ".join(self.current_link["text"].split())
            self.current_links.append(self.current_link)
            self.current_link = None
        self.depth -= 1
        if self.depth == 0:
            self.bars.append(self.current_links)
            self.current_links = None


def main() -> int:
    findings: list[str] = []
    for path in (CSS, CONTRACT, CATALOG, CATALOG_CSS, DOC):
        if not path.is_file():
            findings.append(f"missing Mobile CTA migration asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Mobile CTA component contract is invalid: {exc}")
        return 1

    component = contract.get("components", {}).get("mobileCta", {})
    properties = component.get("properties", {})
    dimensions = component.get("dimensions", {})
    accessibility = component.get("accessibility", {})
    if component.get("figmaName") != "Mobile CTA":
        findings.append("Mobile CTA figmaName must remain 'Mobile CTA'")
    if component.get("anatomy") != ["Container", "Primary Action", "Secondary Action"]:
        findings.append("Mobile CTA anatomy differs from the approved contract")
    if properties.get("state") != ["default", "hover", "focus", "pressed"]:
        findings.append("Mobile CTA states must remain default, hover, focus and pressed")
    expected_dimensions = {
        "maximumWidth": 620,
        "breakpoint": 1000,
        "actionHeight": 52,
        "gap": 8,
        "padding": 8,
        "radiusToken": "radius.lg",
    }
    for key, expected in expected_dimensions.items():
        if dimensions.get(key) != expected:
            findings.append(f"Mobile CTA {key} must remain {expected!r}")
    for key in (
        "twoActionsRequired",
        "primaryActionIsPhone",
        "focusVisible",
        "safeAreaAware",
    ):
        if accessibility.get(key) is not True:
            findings.append(f"Mobile CTA accessibility flag must remain true: {key}")
    if accessibility.get("minimumTouchTarget", 0) < 44:
        findings.append("Mobile CTA minimumTouchTarget must remain at least 44 px")

    css = CSS.read_text(encoding="utf-8")
    if css.count(BLOCK_MARKER) != 1:
        findings.append("cta-polish.css must contain exactly one tokenized Mobile CTA block")
        block = ""
    else:
        block = css.split(BLOCK_MARKER, 1)[1]

    required_markers = (
        "@media (max-width: 1000px)",
        "padding-bottom: calc(92px + env(safe-area-inset-bottom));",
        ".mobile-cta {",
        "width: min(620px, calc(100% - 24px));",
        "padding: var(--p36-spacing-sm);",
        "border: 1px solid var(--p36-color-semantic-border-default);",
        "border-radius: var(--p36-radius-lg);",
        "background: var(--p36-color-semantic-surface-default);",
        "box-shadow: var(--p36-shadow-floating);",
        ".mobile-cta a {",
        "min-height: 52px;",
        "border-radius: var(--p36-radius-md);",
        "background: var(--p36-color-semantic-action-primary);",
        "color: var(--p36-color-semantic-text-inverse);",
        ".mobile-cta a:last-child {",
        "background: var(--p36-color-semantic-action-secondary);",
        ".mobile-cta a:focus-visible {",
        "outline: 3px solid var(--p36-color-primitive-brass-200);",
        ".mobile-cta a:active {",
        "@media (prefers-reduced-motion: reduce)",
        "transition: none;",
    )
    for marker in required_markers:
        if marker not in block:
            findings.append(f"tokenized Mobile CTA block is missing marker: {marker}")
    if RAW_COLOR_RE.search(block):
        findings.append("tokenized Mobile CTA block must not contain raw hex/rgb colors")
    for forbidden in (
        "var(--wood)",
        "var(--blue)",
        "var(--shadow)",
        "font-weight: 900",
        "min-height: 50px",
    ):
        if forbidden in block:
            findings.append(f"tokenized Mobile CTA block contains legacy value: {forbidden}")

    catalog = CATALOG.read_text(encoding="utf-8")
    catalog_css = CATALOG_CSS.read_text(encoding="utf-8")
    for marker in (
        'href="./components-v1-mobile-cta.css"',
        'id="mobile-cta"',
        "Mobile CTA",
        "default · hover · focus · pressed",
        "tel:+79009267929",
    ):
        if marker not in catalog:
            findings.append(f"component catalog is missing Mobile CTA marker: {marker}")
    for marker in (
        ".mobile-cta-specimen",
        "min-height: 52px",
        "var(--p36-color-semantic-action-primary)",
        "var(--p36-color-semantic-action-secondary)",
        "@media (prefers-reduced-motion: reduce)",
    ):
        if marker not in catalog_css:
            findings.append(f"Mobile CTA catalog CSS is missing marker: {marker}")

    html_files = [
        path
        for path in sorted(ROOT.rglob("*.html"))
        if "_site" not in path.parts and "node_modules" not in path.parts
    ]
    total_bars = 0
    for path in html_files:
        parser = MobileCtaParser()
        parser.feed(path.read_text(encoding="utf-8"))
        if not parser.bars:
            continue
        relative = path.relative_to(ROOT).as_posix()
        total_bars += len(parser.bars)
        if len(parser.bars) != 1:
            findings.append(f"{relative}: expected one Mobile CTA, found {len(parser.bars)}")
        for links in parser.bars:
            if len(links) != 2:
                findings.append(f"{relative}: Mobile CTA must contain exactly two links, found {len(links)}")
                continue
            first, second = links
            if first["href"] != "tel:+79009267929":
                findings.append(f"{relative}: first Mobile CTA action must call +79009267929")
            if not first["text"]:
                findings.append(f"{relative}: first Mobile CTA action has no label")
            if not second["href"] or second["href"] == "#" or second["href"].lower().startswith("javascript:"):
                findings.append(f"{relative}: second Mobile CTA action has invalid href {second['href']!r}")
            if second["href"].startswith("tel:"):
                findings.append(f"{relative}: second Mobile CTA action must lead to assessment, not phone")
            if not second["text"]:
                findings.append(f"{relative}: second Mobile CTA action has no label")

    if total_bars < 20:
        findings.append(f"expected Mobile CTA on at least 20 public pages, found {total_bars}")

    doc = DOC.read_text(encoding="utf-8").lower()
    for marker in (
        "production-миграция mobile cta",
        "максимальная ширина — 620 px",
        "breakpoint — 1000 px",
        "минимальная высота действия — 52 px",
        "env(safe-area-inset-bottom)",
        "prefers-reduced-motion",
        "tel:+79009267929",
        "supabase",
    ):
        if marker not in doc:
            findings.append(f"Mobile CTA documentation is missing marker: {marker}")

    if findings:
        print("Mobile CTA token migration findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print(f"Mobile CTA token migration passed ({total_bars} public bars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
