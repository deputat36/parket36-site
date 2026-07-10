#!/usr/bin/env python3
"""Fail when public HTML contains unsafe link and resource attributes."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {".git", ".github", "tools", "node_modules", "_site"}


class LinkAttributeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.findings: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs = {name.lower(): (value or "") for name, value in attrs_list}

        for attr in ("href", "src"):
            if attr not in attrs:
                continue
            value = attrs[attr]
            if not value.strip():
                self.findings.append(f"<{tag}> has empty {attr}")
                continue
            if value.strip().lower().startswith("http://"):
                self.findings.append(f"<{tag}> has insecure {attr}: {value.strip()}")

        if attrs.get("target", "").strip().lower() == "_blank":
            rel_tokens = set(attrs.get("rel", "").lower().split())
            missing = sorted({"noopener", "noreferrer"} - rel_tokens)
            if missing:
                self.findings.append(
                    f"<{tag}> target=_blank is missing rel tokens: {', '.join(missing)}"
                )


def is_ignored(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.relative_to(ROOT).parts)


def html_files() -> list[Path]:
    return sorted(path for path in ROOT.rglob("*.html") if not is_ignored(path))


def main() -> int:
    findings: list[str] = []

    for path in html_files():
        parser = LinkAttributeParser()
        parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
        rel = path.relative_to(ROOT).as_posix()
        findings.extend(f"{rel}: {finding}" for finding in parser.findings)

    if findings:
        print("Link attribute findings:")
        for finding in sorted(findings):
            print(f"  - {finding}")
        return 1

    print("Link attribute check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
