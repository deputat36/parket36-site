#!/usr/bin/env python3
"""Validate the production Section Header token migration."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TYPOGRAPHY_CSS = ROOT / "css" / "typography-polish.css"
BUNDLE = ROOT / "tools" / "css_bundle.py"
COMPONENTS = ROOT / "design" / "components" / "parket36-components.json"
DOC = ROOT / "docs" / "design" / "parket36-section-header-token-migration-v1.md"
BLOCK_MARKER = "/* Design system v1: tokenized Section Header. */"
RAW_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}|rgba?\(")


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
    for path in (TYPOGRAPHY_CSS, BUNDLE, COMPONENTS, DOC):
        if not path.is_file():
            findings.append(f"missing Section Header migration asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        components = json.loads(COMPONENTS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Section Header component contract is invalid: {exc}")
        return 1

    section_header = components.get("components", {}).get("sectionHeader", {})
    properties = section_header.get("properties", {})
    dimensions = section_header.get("dimensions", {})

    if section_header.get("anatomy") != ["Eyebrow", "Heading", "Description"]:
        findings.append("Section Header anatomy differs from the approved contract")
    if properties.get("alignment") != ["left", "center"]:
        findings.append("Section Header alignments differ from the approved contract")
    if dimensions.get("maximumTextWidth") != 760:
        findings.append("Section Header maximumTextWidth must remain 760 px")
    if dimensions.get("gap") != 16:
        findings.append("Section Header gap must remain 16 px")

    css = TYPOGRAPHY_CSS.read_text(encoding="utf-8")
    if css.count(BLOCK_MARKER) != 1:
        findings.append("typography-polish.css must contain exactly one tokenized Section Header block")
        block = ""
    else:
        block = css.split(BLOCK_MARKER, 1)[1].split("@media (max-width: 1000px)", 1)[0]

    required_markers = (
        ".section__head {",
        "display: grid;",
        "gap: var(--p36-spacing-lg);",
        "width: min(100%, 760px);",
        "max-width: 760px;",
        "margin-bottom: var(--p36-spacing-2xl);",
        ".section__head > * {",
        ".section__head .eyebrow {",
        "color: var(--p36-color-semantic-text-warm);",
        "font-size: var(--p36-font-size-eyebrow);",
        "font-weight: var(--p36-font-weight-bold);",
        ".section__head h2 {",
        "color: var(--p36-color-semantic-text-primary);",
        ".section__head > p:not(.eyebrow) {",
        "color: var(--p36-color-semantic-text-secondary);",
        "font-size: clamp(var(--p36-font-size-body), 1.5vw, var(--p36-font-size-lead));",
        ".section__head::after {",
        "width: var(--p36-spacing-4xl);",
        "height: var(--p36-spacing-xs);",
        "var(--p36-color-semantic-action-primary)",
        "var(--p36-color-semantic-action-secondary)",
        ".section__head--center {",
        "justify-items: center;",
        "margin-inline: auto;",
        "text-align: center;",
    )
    for marker in required_markers:
        if marker not in block:
            findings.append(f"tokenized Section Header block is missing marker: {marker}")

    if RAW_COLOR_RE.search(block):
        findings.append("tokenized Section Header block must not contain raw hex/rgb colors")
    for forbidden in (
        "var(--wood)",
        "var(--gold)",
        "var(--line)",
        "font-weight: 900",
        "max-width: 820px",
        "max-width: 780px",
    ):
        if forbidden in block:
            findings.append(f"tokenized Section Header block contains legacy value: {forbidden}")

    mobile_fragment = css.split("@media (max-width: 640px)", 1)[-1]
    for marker in (
        ".section__head {",
        "margin-bottom: 22px;",
    ):
        if marker not in mobile_fragment:
            findings.append(f"mobile Section Header behavior is missing marker: {marker}")

    try:
        css_modules = load_literal_assignment(BUNDLE, "CSS_MODULES")
    except (SyntaxError, ValueError) as exc:
        findings.append(str(exc))
        css_modules = ()
    if isinstance(css_modules, tuple):
        try:
            enhancements_index = css_modules.index("enhancements.css")
            typography_index = css_modules.index("typography-polish.css")
        except ValueError as exc:
            findings.append(f"CSS module order is incomplete: {exc}")
        else:
            if typography_index <= enhancements_index:
                findings.append("typography-polish.css must load after enhancements.css")

    html_files = sorted(ROOT.rglob("*.html"))
    section_header_count = sum(
        path.read_text(encoding="utf-8").count('class="section__head"')
        for path in html_files
        if "_site" not in path.parts
    )
    if section_header_count < 10:
        findings.append(
            f"expected Section Header to remain a shared component on at least 10 pages; found {section_header_count}"
        )

    doc = DOC.read_text(encoding="utf-8").lower()
    for marker in (
        "миграция section header на токены",
        "существующие контейнеры `.section__head`",
        "максимальная ширина текста — 760 px",
        "расстояние между элементами — 16 px",
        "`.section__head--center`",
        "mobile 390 px",
        "уровни `h2`",
        "supabase",
    ):
        if marker not in doc:
            findings.append(f"Section Header migration documentation is missing marker: {marker}")

    if findings:
        print("Section Header token migration findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Section Header token migration passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
