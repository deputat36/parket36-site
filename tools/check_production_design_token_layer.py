#!/usr/bin/env python3
"""Validate the no-op production design-token layer before visual migration starts."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / "design" / "parket36-tokens.json"
DESIGN_CSS = ROOT / "design" / "generated" / "parket36-tokens.css"
PRODUCTION_CSS = ROOT / "css" / "design-tokens.css"
GENERATOR = ROOT / "tools" / "build_design_token_css.py"
BUNDLE = ROOT / "tools" / "css_bundle.py"
DOC = ROOT / "docs" / "design" / "parket36-production-token-layer-v1.md"
TOKEN_DECLARATION_RE = re.compile(r"^\s*(--p36-[a-z0-9-]+):", re.MULTILINE)
TOKEN_USAGE_RE = re.compile(r"var\((--p36-[a-z0-9-]+)\)")
EXPECTED_DECLARATION_COUNT = 80


def load_assignment(path: Path, name: str) -> object:
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
    required = (TOKENS, DESIGN_CSS, PRODUCTION_CSS, GENERATOR, BUNDLE, DOC)
    for path in required:
        if not path.is_file():
            findings.append(f"missing production token layer asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        json.loads(TOKENS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Design token JSON is invalid: {exc}")
        return 1

    design_css = DESIGN_CSS.read_text(encoding="utf-8")
    production_css = PRODUCTION_CSS.read_text(encoding="utf-8")
    if design_css != production_css:
        findings.append("design and production generated token CSS must be byte-identical")

    declarations = TOKEN_DECLARATION_RE.findall(production_css)
    if len(declarations) != EXPECTED_DECLARATION_COUNT:
        findings.append(
            f"production token CSS must declare {EXPECTED_DECLARATION_COUNT} variables, found {len(declarations)}"
        )
    if len(declarations) != len(set(declarations)):
        findings.append("production token CSS contains duplicate custom-property declarations")

    if not production_css.startswith(
        "/* Generated from design/parket36-tokens.json. Do not edit directly. */\n:root {"
    ):
        findings.append("production token CSS must keep the generated-file header and :root scope")

    try:
        output_paths = load_assignment(GENERATOR, "OUTPUT_PATHS")
    except (SyntaxError, ValueError) as exc:
        findings.append(str(exc))
        output_paths = ()
    expected_suffixes = {
        ("design", "generated", "parket36-tokens.css"),
        ("css", "design-tokens.css"),
    }
    actual_suffixes = {
        tuple(path.parts[-3:]) if "design" in path.parts else tuple(path.parts[-2:])
        for path in output_paths
        if isinstance(path, Path)
    }
    if actual_suffixes != expected_suffixes:
        findings.append("token generator must write both design and production CSS outputs")

    try:
        css_modules = load_assignment(BUNDLE, "CSS_MODULES")
    except (SyntaxError, ValueError) as exc:
        findings.append(str(exc))
        css_modules = ()
    if not isinstance(css_modules, tuple) or not css_modules:
        findings.append("CSS_MODULES must be a non-empty tuple")
    else:
        if css_modules[0] != "design-tokens.css":
            findings.append("design-tokens.css must be the first production CSS module")
        if css_modules.count("design-tokens.css") != 1:
            findings.append("design-tokens.css must appear exactly once in CSS_MODULES")

    consumers: list[str] = []
    for css_file in sorted((ROOT / "css").glob("*.css")):
        if css_file == PRODUCTION_CSS:
            continue
        text = css_file.read_text(encoding="utf-8")
        if TOKEN_USAGE_RE.search(text):
            consumers.append(css_file.relative_to(ROOT).as_posix())
    if consumers:
        findings.append(
            "stage v1 must remain visually inert; unexpected token consumers: " + ", ".join(consumers)
        )

    doc = DOC.read_text(encoding="utf-8")
    for marker in (
        "визуально нейтральный",
        "css/design-tokens.css",
        "первым модулем",
        "80 CSS-переменных",
        "следующий визуальный PR",
    ):
        if marker not in doc:
            findings.append(f"production token layer documentation is missing marker: {marker}")

    if findings:
        print("Production design token layer findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Production design token layer passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
