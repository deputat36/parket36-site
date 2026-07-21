#!/usr/bin/env python3
"""Validate the first production component migration: tokenized buttons."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CTA_CSS = ROOT / "css" / "cta-polish.css"
COMPONENTS = ROOT / "design" / "components" / "parket36-components.json"
BUNDLE = ROOT / "tools" / "css_bundle.py"
DOC = ROOT / "docs" / "design" / "parket36-button-token-migration-v1.md"
BLOCK_MARKER = "/* Design system v1: tokenized buttons. */"
RAW_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}|rgba?\(")


def load_css_modules() -> tuple[str, ...]:
    tree = ast.parse(BUNDLE.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if "CSS_MODULES" in targets:
            value = ast.literal_eval(node.value)
            if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
                return value
            raise ValueError("CSS_MODULES must be a tuple of strings")
    raise ValueError("CSS_MODULES assignment is missing")


def main() -> int:
    findings: list[str] = []
    for path in (CTA_CSS, COMPONENTS, BUNDLE, DOC):
        if not path.is_file():
            findings.append(f"missing button migration asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        components = json.loads(COMPONENTS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Button component contract is invalid: {exc}")
        return 1

    button = components.get("components", {}).get("button", {})
    properties = button.get("properties", {})
    dimensions = button.get("dimensions", {})
    accessibility = button.get("accessibility", {})

    if properties.get("variant") != ["primary", "secondary", "ghost"]:
        findings.append("button variants differ from the approved component contract")
    if properties.get("state") != ["default", "hover", "focus", "pressed", "disabled"]:
        findings.append("button states differ from the approved component contract")
    if dimensions.get("mdHeight") != 48:
        findings.append("button mdHeight must remain 48 px")
    if dimensions.get("horizontalPadding") != 24:
        findings.append("button horizontalPadding must remain 24 px")
    if dimensions.get("radiusToken") != "radius.full":
        findings.append("button radius must remain bound to radius.full")
    if accessibility.get("minimumTouchTarget") != 44:
        findings.append("button minimum touch target must remain 44 px")
    if accessibility.get("focusVisible") is not True:
        findings.append("button focus-visible requirement must remain enabled")

    css = CTA_CSS.read_text(encoding="utf-8")
    if css.count(BLOCK_MARKER) != 1:
        findings.append("cta-polish.css must contain exactly one tokenized button block")
        block = ""
    else:
        block = css.split(BLOCK_MARKER, 1)[1]

    required_markers = (
        ".btn {",
        "min-height: 48px;",
        "gap: var(--p36-spacing-sm);",
        "padding: 12px var(--p36-spacing-xl);",
        "border-radius: var(--p36-radius-full);",
        "font-weight: var(--p36-font-weight-bold);",
        "box-shadow: var(--p36-shadow-card);",
        ".btn:hover {",
        ".btn:active {",
        ".btn:focus-visible {",
        "outline: 3px solid var(--p36-color-primitive-brass-200);",
        ".btn--primary {",
        "background: var(--p36-color-semantic-action-primary);",
        "background: var(--p36-color-semantic-action-primary-hover);",
        "color: var(--p36-color-semantic-text-inverse);",
        ".btn--ghost {",
        "border-color: var(--p36-color-semantic-border-default);",
        "background: var(--p36-color-semantic-surface-default);",
        "color: var(--p36-color-semantic-text-accent);",
        "border-color: var(--p36-color-semantic-border-strong);",
        ".btn--light {",
        "color: var(--p36-color-semantic-text-primary);",
        ".btn--dark {",
        "background: var(--p36-color-semantic-bg-inverse);",
        "background-image: none;",
        ".btn:disabled,",
        '.btn[aria-disabled="true"] {',
        "opacity: .55;",
        "cursor: not-allowed;",
        "box-shadow: none;",
        "@media (max-width: 640px) {",
        "min-height: 52px;",
    )
    for marker in required_markers:
        if marker not in block:
            findings.append(f"tokenized button block is missing marker: {marker}")

    if RAW_COLOR_RE.search(block):
        findings.append("tokenized button block must not contain raw hex/rgb colors")
    for forbidden in ("var(--wood)", "var(--gold)", "linear-gradient("):
        if forbidden in block:
            findings.append(f"tokenized button block contains legacy visual value: {forbidden}")

    if block.count("background-image: none;") < 2:
        findings.append("primary and dark buttons must explicitly cancel legacy gradients")

    try:
        css_modules = load_css_modules()
    except (SyntaxError, ValueError) as exc:
        findings.append(str(exc))
        css_modules = ()
    if css_modules:
        try:
            cta_index = css_modules.index("cta-polish.css")
            enhancements_index = css_modules.index("enhancements.css")
            accessibility_index = css_modules.index("accessibility-polish.css")
        except ValueError as exc:
            findings.append(f"required CSS module is missing: {exc}")
        else:
            if not (cta_index > enhancements_index and cta_index > accessibility_index):
                findings.append("cta-polish.css must load after legacy button and focus overrides")

    doc = DOC.read_text(encoding="utf-8")
    doc_lower = doc.lower()
    for marker in (
        "миграция кнопок на токены",
        "минимальная высота — 48 px",
        "минимальная высота сохраняется 52 px",
        "focus-state",
        "disabled-state",
        "background-image: none",
        "мобильная нижняя панель",
    ):
        if marker not in doc_lower:
            findings.append(f"button migration documentation is missing marker: {marker}")

    if findings:
        print("Button token migration findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Button token migration passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
