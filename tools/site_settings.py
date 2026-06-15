#!/usr/bin/env python3
"""Check or update shared Parket36 contact settings.

Usage:
    python tools/site_settings.py --check
    python tools/site_settings.py --write

The script intentionally touches only predictable contact values inside HTML
pages. It does not rewrite JavaScript, documentation or marketing copy.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "data" / "site.json"
IGNORED_DIRS = {".git", ".github", "tools", "node_modules", "_site"}

TEL_RE = re.compile(r"tel:\+7\d{10}")
DISPLAY_PHONE_RE = re.compile(r"8\s*\(\d{3}\)\s*\d{3}[\-– ]\d{2}[\-– ]\d{2}")
MAX_HREF_RE = re.compile(r'href="https://max\.ru[^\"]*"')


def iter_html_files() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*.html"):
        rel_parts = path.relative_to(ROOT).parts
        if any(part in IGNORED_DIRS for part in rel_parts):
            continue
        result.append(path)
    return sorted(result)


def load_config() -> dict[str, object]:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    required = {"phone_display", "phone_e164", "domain", "max_url", "default_request_path"}
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"Missing settings: {', '.join(missing)}")
    phone_e164 = str(data["phone_e164"])
    if not re.fullmatch(r"\+7\d{10}", phone_e164):
        raise ValueError("phone_e164 must have the format +7XXXXXXXXXX")
    return data


def update_text(text: str, config: dict[str, object]) -> str:
    phone_e164 = str(config["phone_e164"])
    phone_display = str(config["phone_display"])
    max_url = str(config.get("max_url", "")).strip()

    text = TEL_RE.sub(f"tel:{phone_e164}", text)
    text = DISPLAY_PHONE_RE.sub(phone_display, text)

    if max_url:
        text = MAX_HREF_RE.sub(f'href="{max_url}"', text)

    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()

    try:
        config = load_config()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Configuration error: {exc}")
        return 1

    changed: list[str] = []
    for path in iter_html_files():
        original = path.read_text(encoding="utf-8")
        updated = update_text(original, config)
        if original == updated:
            continue
        rel = path.relative_to(ROOT).as_posix()
        changed.append(rel)
        if args.write:
            path.write_text(updated, encoding="utf-8")

    if args.check and changed:
        print("Shared settings are not synchronized:")
        for rel in changed:
            print(f"  - {rel}")
        print("Run: python tools/site_settings.py --write")
        return 1

    if args.write:
        if changed:
            print(f"Updated {len(changed)} files")
            for rel in changed:
                print(f"  - {rel}")
        else:
            print("Shared settings are already synchronized")
    else:
        print("Shared settings check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
