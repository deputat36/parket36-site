#!/usr/bin/env python3
"""Generate deterministic CSS custom properties from Parket36 design tokens."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
TOKENS_PATH = ROOT / "design" / "parket36-tokens.json"
OUTPUT_PATH = ROOT / "design" / "generated" / "parket36-tokens.css"
REFERENCE_RE = re.compile(r"^\{([A-Za-z0-9_.-]+)\}$")
CAMEL_RE = re.compile(r"([a-z0-9])([A-Z])")


def css_segment(value: str) -> str:
    return CAMEL_RE.sub(r"\1-\2", value).replace("_", "-").lower()


def css_name(path: tuple[str, ...]) -> str:
    return "--p36-" + "-".join(css_segment(part) for part in path)


def iter_tokens(value: Any, path: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], dict[str, Any]]]:
    if isinstance(value, dict) and "$type" in value and "$value" in value:
        yield path, value
        return
    if not isinstance(value, dict):
        return
    for key, child in value.items():
        if key.startswith("$") or key == "meta":
            continue
        yield from iter_tokens(child, (*path, key))


def format_number(value: int | float) -> str:
    return f"{value:g}"


def css_value(token: dict[str, Any]) -> str:
    token_type = token["$type"]
    value = token["$value"]

    if isinstance(value, str):
        reference = REFERENCE_RE.fullmatch(value)
        if reference:
            return f"var({css_name(tuple(reference.group(1).split('.')))})"

    if token_type == "color":
        return str(value)
    if token_type == "dimension":
        return f"{format_number(value['value'])}{value['unit']}"
    if token_type == "fontFamily":
        return json.dumps(value, ensure_ascii=False)
    if token_type == "fontWeight":
        return str(value)
    if token_type == "shadow":
        return " ".join(
            str(value[key])
            for key in ("offsetX", "offsetY", "blur", "spread", "color")
        )

    raise ValueError(f"unsupported token type: {token_type}")


def render_css(tokens: dict[str, Any]) -> str:
    lines = [
        "/* Generated from design/parket36-tokens.json. Do not edit directly. */",
        ":root {",
    ]
    for path, token in iter_tokens(tokens):
        lines.append(f"  {css_name(path)}: {css_value(token)};")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if generated CSS is stale")
    args = parser.parse_args()

    try:
        tokens = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
        expected = render_css(tokens)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"Design token CSS generation failed: {exc}")
        return 1

    if args.check:
        if not OUTPUT_PATH.is_file():
            print(f"Generated CSS is missing: {OUTPUT_PATH.relative_to(ROOT)}")
            return 1
        actual = OUTPUT_PATH.read_text(encoding="utf-8")
        if actual != expected:
            print("Generated design token CSS is stale. Run tools/build_design_token_css.py")
            return 1
        print("Generated design token CSS is current")
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(expected, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
