#!/usr/bin/env python3
"""Validate the documented Parket36 redesign tokens and their internal aliases."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOKENS_PATH = ROOT / "design" / "parket36-tokens.json"
DOC_PATH = ROOT / "docs" / "design" / "parket36-redesign-v1.md"
FIGMA_URL = "https://www.figma.com/design/2ovBluMs8xOKkkUIPevLaH"
REFERENCE_RE = re.compile(r"^\{([A-Za-z0-9_.-]+)\}$")

EXPECTED_VALUES: dict[str, Any] = {
    "color.primitive.neutral.900.$value": "#151915",
    "color.primitive.forest.700.$value": "#1E4A37",
    "color.primitive.forest.900.$value": "#102A20",
    "color.primitive.brass.500.$value": "#C9943E",
    "color.semantic.action.primary.$value": "{color.primitive.forest.700}",
    "color.semantic.action.primaryHover.$value": "{color.primitive.forest.900}",
    "color.semantic.action.secondary.$value": "{color.primitive.brass.500}",
    "spacing.5xl.$value.value": 96,
    "radius.xl.$value.value": 28,
    "size.touchMin.$value.value": 44,
    "size.container.$value.value": 1180,
    "font.family.display.$value": "Manrope",
    "font.family.body.$value": "Onest",
    "font.size.h1.$value.value": 52,
}

REQUIRED_DOC_MARKERS = (
    "Мастер помогает сохранить и восстановить ценный деревянный пол",
    "Manrope",
    "Onest",
    "#1E4A37",
    "#C9943E",
    "минимальная интерактивная зона — 44 px",
    "рабочая ширина контента — до 1180 px",
    "Browser smoke, Lighthouse и Site quality",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_path(data: Any, dotted_path: str) -> Any:
    value = data
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(dotted_path)
        value = value[part]
    return value


def walk(value: Any):
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)
    else:
        yield value


def main() -> int:
    findings: list[str] = []

    if not TOKENS_PATH.is_file():
        findings.append(f"missing token file: {TOKENS_PATH.relative_to(ROOT)}")
    if not DOC_PATH.is_file():
        findings.append(f"missing design document: {DOC_PATH.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        tokens = read_json(TOKENS_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Design token JSON is invalid: {exc}")
        return 1

    doc = DOC_PATH.read_text(encoding="utf-8", errors="ignore")

    if get_path(tokens, "meta.figmaFile") != FIGMA_URL:
        findings.append("meta.figmaFile must point to the approved Parket36 Figma workspace")
    if get_path(tokens, "meta.status") != "draft":
        findings.append("design tokens must remain draft until the screens are approved")
    if FIGMA_URL not in doc:
        findings.append("design document must link to the approved Figma workspace")

    for dotted_path, expected in EXPECTED_VALUES.items():
        try:
            actual = get_path(tokens, dotted_path)
        except KeyError:
            findings.append(f"missing required token path: {dotted_path}")
            continue
        if actual != expected:
            findings.append(f"unexpected value for {dotted_path}: {actual!r} != {expected!r}")

    for marker in REQUIRED_DOC_MARKERS:
        if marker not in doc:
            findings.append(f"design document is missing marker: {marker}")

    for raw_value in walk(tokens):
        if not isinstance(raw_value, str):
            continue
        match = REFERENCE_RE.fullmatch(raw_value)
        if not match:
            continue
        target_path = match.group(1)
        try:
            target = get_path(tokens, target_path)
        except KeyError:
            findings.append(f"unresolved design token reference: {raw_value}")
            continue
        if not isinstance(target, dict) or "$value" not in target:
            findings.append(f"design token reference does not target a token: {raw_value}")

    old_palette_markers = ("#6F4628", "#9B683D", "#D7A86E")
    serialized = json.dumps(tokens, ensure_ascii=False).upper()
    for marker in old_palette_markers:
        if marker in serialized:
            findings.append(f"new token file must not reuse the old primary palette: {marker}")

    if findings:
        print("Design token findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Design tokens passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
