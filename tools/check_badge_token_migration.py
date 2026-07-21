#!/usr/bin/env python3
"""Validate the production Badge migration for trust indicators."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CTA_CSS = ROOT / "css" / "cta-polish.css"
INTERFACE_CSS = ROOT / "css" / "interface-polish.css"
COMPONENTS = ROOT / "design" / "components" / "parket36-components.json"
DOC = ROOT / "docs" / "design" / "parket36-badge-token-migration-v1.md"
BLOCK_MARKER = "/* Design system v1: tokenized trust badges. */"
RAW_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}|rgba?\(")


def main() -> int:
    findings: list[str] = []
    for path in (CTA_CSS, INTERFACE_CSS, COMPONENTS, DOC):
        if not path.is_file():
            findings.append(f"missing Badge migration asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        components = json.loads(COMPONENTS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Badge component contract is invalid: {exc}")
        return 1

    badge = components.get("components", {}).get("badge", {})
    properties = badge.get("properties", {})
    dimensions = badge.get("dimensions", {})

    if properties.get("tone") != ["forest", "brass", "neutral"]:
        findings.append("Badge tones differ from the approved component contract")
    if dimensions.get("minimumHeight") != 34:
        findings.append("Badge minimumHeight must remain 34 px")
    if dimensions.get("horizontalPadding") != 12:
        findings.append("Badge horizontalPadding must remain 12 px")
    if dimensions.get("radiusToken") != "radius.full":
        findings.append("Badge radius must remain bound to radius.full")

    css = CTA_CSS.read_text(encoding="utf-8")
    if css.count(BLOCK_MARKER) != 1:
        findings.append("cta-polish.css must contain exactly one tokenized trust Badge block")
        block = ""
    else:
        block = css.split(BLOCK_MARKER, 1)[1]

    required_markers = (
        ".trust span {",
        "display: inline-flex;",
        "align-items: center;",
        "justify-content: center;",
        "min-height: 34px;",
        "padding: 7px var(--p36-spacing-md);",
        "border: 1px solid var(--p36-color-semantic-border-strong);",
        "border-radius: var(--p36-radius-full);",
        "background: var(--p36-color-semantic-surface-subtle);",
        "color: var(--p36-color-semantic-text-accent);",
        "font-size: var(--p36-font-size-small);",
        "font-weight: var(--p36-font-weight-semibold);",
        "box-shadow: none;",
    )
    for marker in required_markers:
        if marker not in block:
            findings.append(f"tokenized Badge block is missing marker: {marker}")

    if RAW_COLOR_RE.search(block):
        findings.append("tokenized Badge block must not contain raw hex/rgb colors")
    for forbidden in ("var(--wood)", "var(--gold)", "var(--line)", "font-weight: 900"):
        if forbidden in block:
            findings.append(f"tokenized Badge block contains legacy value: {forbidden}")

    interface_css = INTERFACE_CSS.read_text(encoding="utf-8")
    mobile_markers = (
        "@media (max-width: 640px)",
        ".trust span {",
        "width: 100%;",
        "justify-content: center;",
        "text-align: center;",
    )
    for marker in mobile_markers:
        if marker not in interface_css:
            findings.append(f"mobile Badge behavior is missing marker: {marker}")

    doc = DOC.read_text(encoding="utf-8").lower()
    for marker in (
        "миграция badge на токены",
        "только элементов внутри `.trust`",
        "интерактивные `.pill`",
        "минимальная высота — 34 px",
        "горизонтальные поля — 12 px",
        "mobile до 640 px",
        "supabase",
    ):
        if marker not in doc:
            findings.append(f"Badge migration documentation is missing marker: {marker}")

    if findings:
        print("Badge token migration findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Badge token migration passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
