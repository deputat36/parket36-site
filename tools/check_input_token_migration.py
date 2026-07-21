#!/usr/bin/env python3
"""Validate the production request-form Input token migration."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CTA_CSS = ROOT / "css" / "cta-polish.css"
BUNDLE = ROOT / "tools" / "css_bundle.py"
COMPONENTS = ROOT / "design" / "components" / "parket36-components.json"
DOC = ROOT / "docs" / "design" / "parket36-input-token-migration-v1.md"
MAIN_JS = ROOT / "js" / "main.js"
BLOCK_MARKER = "/* Design system v1: tokenized request inputs. */"
RAW_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}|rgba?\(")
FORM_RE = re.compile(
    r'<form class="request-form" id="request-form">(?P<body>.*?)</form>',
    re.DOTALL,
)


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
    for path in (CTA_CSS, BUNDLE, COMPONENTS, DOC, MAIN_JS):
        if not path.is_file():
            findings.append(f"missing Input migration asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        components = json.loads(COMPONENTS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Input component contract is invalid: {exc}")
        return 1

    input_contract = components.get("components", {}).get("input", {})
    properties = input_contract.get("properties", {})
    dimensions = input_contract.get("dimensions", {})
    accessibility = input_contract.get("accessibility", {})

    if input_contract.get("anatomy") != ["Label", "Field", "Value", "Help", "Error"]:
        findings.append("Input anatomy differs from the approved component contract")
    if properties.get("state") != ["default", "focus", "filled", "error", "disabled"]:
        findings.append("Input states differ from the approved component contract")
    if dimensions.get("fieldHeight") != 52:
        findings.append("Input fieldHeight must remain 52 px")
    if dimensions.get("horizontalPadding") != 16:
        findings.append("Input horizontalPadding must remain 16 px")
    if dimensions.get("radiusToken") != "radius.md":
        findings.append("Input radius must remain bound to radius.md")
    if accessibility.get("labelRequired") is not True:
        findings.append("Input labels must remain required")
    if accessibility.get("errorNotColorOnly") is not True:
        findings.append("Input error must not rely on color alone")
    if accessibility.get("minimumTouchTarget") != 44:
        findings.append("Input minimum touch target must remain 44 px")

    css = CTA_CSS.read_text(encoding="utf-8")
    if css.count(BLOCK_MARKER) != 1:
        findings.append("cta-polish.css must contain exactly one tokenized request Input block")
        block = ""
    else:
        block = css.split(BLOCK_MARKER, 1)[1]

    required_markers = (
        ".request-form label:has(> input)",
        ".request-form label:has(> select)",
        ".request-form label:has(> textarea)",
        "gap: var(--p36-spacing-sm);",
        "padding: var(--p36-spacing-md);",
        "border-radius: var(--p36-radius-lg);",
        ".request-form input,",
        ".request-form select,",
        ".request-form textarea {",
        "min-height: 52px;",
        "padding: 12px var(--p36-spacing-lg);",
        "border: 1px solid var(--p36-color-semantic-border-default);",
        "border-radius: var(--p36-radius-md);",
        "background: var(--p36-color-semantic-surface-default);",
        "color: var(--p36-color-semantic-text-primary);",
        "font-size: var(--p36-font-size-body);",
        ".request-form textarea {",
        "min-height: 132px;",
        ".request-form input::placeholder,",
        "color: var(--p36-color-semantic-text-muted);",
        ".request-form input:focus,",
        ".request-form input:focus-visible,",
        "border-color: var(--p36-color-semantic-action-primary);",
        "box-shadow: 0 0 0 4px var(--p36-color-primitive-brass-50);",
        ".request-form input:not(:placeholder-shown),",
        ".request-form select:valid {",
        "background: var(--p36-color-semantic-surface-subtle);",
        ".request-form input:required:valid,",
        "border-left-color: var(--p36-color-semantic-status-success);",
        ".request-form input:required:user-invalid,",
        "border-color: var(--p36-color-semantic-status-error);",
        ".request-form label:has(> input:required:user-invalid)::after,",
        'content: "Проверьте обязательное поле";',
        ".request-form input:disabled,",
        "background: var(--p36-color-primitive-neutral-100);",
        "cursor: not-allowed;",
        "opacity: .72;",
    )
    for marker in required_markers:
        if marker not in block:
            findings.append(f"tokenized Input block is missing marker: {marker}")

    if RAW_COLOR_RE.search(block):
        findings.append("tokenized Input block must not contain raw hex/rgb colors")
    for forbidden in (
        "var(--wood)",
        "var(--gold)",
        "var(--line)",
        "var(--muted)",
        "font-weight: 900",
        "border-radius: 18px",
    ):
        if forbidden in block:
            findings.append(f"tokenized Input block contains legacy value: {forbidden}")

    if block.count('content: "Проверьте обязательное поле";') != 1:
        findings.append("Input error text must exist exactly once")
    if ":user-invalid" not in block:
        findings.append("Input error state must use :user-invalid")
    if ":disabled" not in block:
        findings.append("Input disabled state is missing")

    try:
        css_modules = load_literal_assignment(BUNDLE, "CSS_MODULES")
    except (SyntaxError, ValueError) as exc:
        findings.append(str(exc))
        css_modules = ()
    if isinstance(css_modules, tuple):
        try:
            accessibility_index = css_modules.index("accessibility-polish.css")
            cta_index = css_modules.index("cta-polish.css")
        except ValueError as exc:
            findings.append(f"CSS module order is incomplete: {exc}")
        else:
            if cta_index <= accessibility_index:
                findings.append("cta-polish.css must load after accessibility-polish.css")

    public_html = [
        path
        for path in sorted(ROOT.rglob("*.html"))
        if "_site" not in path.parts and "design" not in path.parts
    ]
    forms: list[tuple[str, str]] = []
    for path in public_html:
        text = path.read_text(encoding="utf-8")
        for match in FORM_RE.finditer(text):
            forms.append((path.relative_to(ROOT).as_posix(), match.group("body")))

    if len(forms) < 2:
        findings.append(f"expected request-form on at least two public pages; found {len(forms)}")

    required_ids = (
        "request-service",
        "request-location",
        "request-area",
        "request-photos",
        "request-video",
        "request-task",
        "request-callback",
        "request-contact",
        "request-status",
    )
    for relative, body in forms:
        for field_id in required_ids:
            if f'id="{field_id}"' not in body:
                findings.append(f"{relative}: request form is missing id={field_id}")
        if not re.search(r'<textarea id="request-task"[^>]*\brequired\b', body):
            findings.append(f"{relative}: request-task must remain required")
        if not re.search(r'<input id="request-contact"[^>]*\brequired\b', body):
            findings.append(f"{relative}: request-contact must remain required")
        if 'autocomplete="tel"' not in body or 'inputmode="tel"' not in body:
            findings.append(f"{relative}: request-contact tel metadata changed")
        if '<button class="btn btn--primary" type="submit">' not in body:
            findings.append(f"{relative}: request submit button contract changed")
        if '<p class="form-status" id="request-status"></p>' not in body:
            findings.append(f"{relative}: request status element changed")

    main_js = MAIN_JS.read_text(encoding="utf-8")
    for marker in required_ids:
        if marker == "request-status":
            expected = "request-status"
        else:
            expected = marker
        if expected not in main_js:
            findings.append(f"js/main.js no longer references {expected}")
    for marker in (
        "submitParketLead",
        "parket36:lead",
        "request-fallback",
        "PARKET_LEAD_ENDPOINT",
    ):
        if marker not in main_js:
            findings.append(f"js/main.js is missing request integration marker: {marker}")

    doc = DOC.read_text(encoding="utf-8").lower()
    for marker in (
        "миграция input на токены",
        "только поля внутри `.request-form`",
        "высота поля — минимум 52 px",
        "горизонтальные поля — 16 px",
        "`radius.md`, 14 px",
        "проверьте обязательное поле",
        "ошибка не передаётся только цветом",
        "mobile 390 px",
        "supabase edge function",
    ):
        if marker not in doc:
            findings.append(f"Input migration documentation is missing marker: {marker}")

    if findings:
        print("Input token migration findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Input token migration passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
