#!/usr/bin/env python3
"""Validate the production Problem Card token migration."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CTA_CSS = ROOT / "css" / "cta-polish.css"
ENHANCEMENTS_CSS = ROOT / "css" / "enhancements.css"
ACCESSIBILITY_CSS = ROOT / "css" / "accessibility-polish.css"
COMPONENTS = ROOT / "design" / "components" / "parket36-components.json"
INDEX = ROOT / "index.html"
DOC = ROOT / "docs" / "design" / "parket36-problem-card-token-migration-v1.md"
BLOCK_MARKER = "/* Design system v1: tokenized Problem Card. */"
RAW_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}|rgba?\(")


def main() -> int:
    findings: list[str] = []
    required_paths = (
        CTA_CSS,
        ENHANCEMENTS_CSS,
        ACCESSIBILITY_CSS,
        COMPONENTS,
        INDEX,
        DOC,
    )
    for path in required_paths:
        if not path.is_file():
            findings.append(f"missing Problem Card migration asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        components = json.loads(COMPONENTS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Problem Card component contract is invalid: {exc}")
        return 1

    problem_card = components.get("components", {}).get("problemCard", {})
    properties = problem_card.get("properties", {})
    dimensions = problem_card.get("dimensions", {})
    accessibility = problem_card.get("accessibility", {})

    if problem_card.get("anatomy") != ["Number", "Title", "Description", "Arrow"]:
        findings.append("Problem Card anatomy differs from the approved contract")
    if properties.get("state") != ["default", "hover", "focus"]:
        findings.append("Problem Card states differ from the approved contract")
    if dimensions.get("minimumHeight") != 168:
        findings.append("Problem Card minimumHeight must remain 168 px")
    if dimensions.get("padding") != 24:
        findings.append("Problem Card padding must remain 24 px")
    if dimensions.get("radiusToken") != "radius.lg":
        findings.append("Problem Card radius must remain bound to radius.lg")
    if accessibility.get("entireCardClickable") is not True:
        findings.append("Problem Card must remain entirely clickable")
    if accessibility.get("focusVisible") is not True:
        findings.append("Problem Card must keep a visible focus state")

    css = CTA_CSS.read_text(encoding="utf-8")
    if css.count(BLOCK_MARKER) != 1:
        findings.append("cta-polish.css must contain exactly one tokenized Problem Card block")
        block = ""
    else:
        block = css.split(BLOCK_MARKER, 1)[1]

    required_markers = (
        ".quick-choice__grid {",
        "counter-reset: p36-problem-card;",
        ".quick-choice__grid a {",
        "counter-increment: p36-problem-card;",
        "min-height: 168px;",
        "padding: var(--p36-spacing-xl);",
        "border: 1px solid var(--p36-color-semantic-border-default);",
        "border-radius: var(--p36-radius-lg);",
        "background: var(--p36-color-semantic-surface-default);",
        "color: var(--p36-color-semantic-text-primary);",
        "box-shadow: var(--p36-shadow-card);",
        ".quick-choice__grid a::before {",
        "content: counter(p36-problem-card, decimal-leading-zero);",
        "color: var(--p36-color-semantic-text-warm);",
        ".quick-choice__grid a:hover {",
        "background: var(--p36-color-semantic-surface-subtle);",
        "box-shadow: var(--p36-shadow-floating);",
        ".quick-choice__grid a:focus-visible {",
        "outline: 3px solid var(--p36-color-primitive-brass-200);",
        ".quick-choice__grid strong {",
        "font-size: var(--p36-font-size-lead);",
        ".quick-choice__grid strong::after {",
        "background: var(--p36-color-semantic-surface-accent);",
        ".quick-choice__grid span {",
        "font-size: var(--p36-font-size-body);",
    )
    for marker in required_markers:
        if marker not in block:
            findings.append(f"tokenized Problem Card block is missing marker: {marker}")

    if RAW_COLOR_RE.search(block):
        findings.append("tokenized Problem Card block must not contain raw hex/rgb colors")
    for forbidden in (
        "var(--wood)",
        "var(--gold)",
        "var(--line)",
        "#fff",
        "font-weight: 900",
    ):
        if forbidden in block:
            findings.append(f"tokenized Problem Card block contains legacy value: {forbidden}")

    enhancements = ENHANCEMENTS_CSS.read_text(encoding="utf-8")
    for marker in (
        ".quick-choice__grid strong::after {",
        'content: "→";',
        "@media (max-width: 640px)",
        ".quick-choice__grid {",
        "grid-template-columns: 1fr;",
    ):
        if marker not in enhancements:
            findings.append(f"Problem Card dependency is missing marker: {marker}")

    accessibility_css = ACCESSIBILITY_CSS.read_text(encoding="utf-8")
    if ".quick-choice__grid a:hover," not in accessibility_css:
        findings.append("reduced-motion guard must include Problem Card hover")

    index = INDEX.read_text(encoding="utf-8")
    match = re.search(
        r'<div class="quick-choice__grid">(?P<body>.*?)</div>',
        index,
        flags=re.DOTALL,
    )
    if not match:
        findings.append("index.html is missing the quick-choice Problem Card group")
    else:
        body = match.group("body")
        hrefs = re.findall(r'<a href="([^"]+)">', body)
        expected_hrefs = [
            "/uslugi/ciklevka-parketa/",
            "/sovety/pochemu-skripit-parket/",
            "/sovety/shcheli-v-parkete/",
            "#request",
        ]
        if hrefs != expected_hrefs:
            findings.append(f"Problem Card hrefs changed: expected {expected_hrefs}, found {hrefs}")
        if body.count("<strong>") != 4 or body.count("<span>") != 4:
            findings.append("Problem Card group must keep four titles and four descriptions")

    doc = DOC.read_text(encoding="utf-8").lower()
    for marker in (
        "миграция problem card на токены",
        "только четыре ссылки внутри `.quick-choice__grid`",
        "css-счётчик `01–04`",
        "минимальная высота — 168 px",
        "внутренние поля — 24 px",
        "вся карточка остаётся кликабельной",
        "mobile 390 px",
        "supabase",
    ):
        if marker not in doc:
            findings.append(f"Problem Card migration documentation is missing marker: {marker}")

    if findings:
        print("Problem Card token migration findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Problem Card token migration passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
