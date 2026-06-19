#!/usr/bin/env python3
"""Extra non-blocking guardrails for public Parket36 pages.

This script prints additional findings that are useful during review. The main
blocking audit still lives in tools/check_site.py.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {".git", ".github", "tools", "node_modules", "_site"}
PUBLIC_SUFFIXES = {".html", ".css", ".js", ".json", ".xml", ".txt"}


class BasicHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.viewport_count = 0

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key.lower(): (value or "") for key, value in attrs_list}
        if tag.lower() == "html":
            self.lang = attrs.get("lang", "").lower()
        if tag.lower() == "meta" and attrs.get("name", "").lower() == "viewport":
            self.viewport_count += 1


def is_ignored(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.relative_to(ROOT).parts)


def public_text_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file() and not is_ignored(path) and path.suffix.lower() in PUBLIC_SUFFIXES
    )


def html_files() -> list[Path]:
    return [path for path in public_text_files() if path.suffix.lower() == ".html"]


def main() -> int:
    findings: list[str] = []

    legacy_markers = {
        "https://max.ru/": "generic MAX link",
        "/#services": "old homepage services anchor",
        "/#process": "old homepage process anchor",
        "WhatsApp": "legacy messenger name",
        "wa.me": "legacy messenger URL",
    }

    for path in public_text_files():
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker, label in legacy_markers.items():
            if marker in text:
                findings.append(f"{rel}: contains {label}: {marker}")

    for path in html_files():
        rel = path.relative_to(ROOT).as_posix()
        parser = BasicHtmlParser()
        parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
        if parser.lang != "ru":
            findings.append(f"{rel}: html lang should be ru")
        if parser.viewport_count != 1:
            findings.append(f"{rel}: expected one viewport meta, found {parser.viewport_count}")

    index = ROOT / "index.html"
    index_text = index.read_text(encoding="utf-8", errors="ignore") if index.exists() else ""
    required_form_markers = {
        'id="request-location"': "request location field",
        'id="request-area"': "request area field",
        'id="request-task"': "request task field",
        'id="request-callback"': "request callback field",
        'id="request-contact"': "request contact field",
        'autocomplete="tel"': "telephone autocomplete",
        'inputmode="tel"': "telephone input mode",
    }
    for marker, label in required_form_markers.items():
        if marker not in index_text:
            findings.append(f"index.html: missing {label}: {marker}")

    if findings:
        print("Extra guardrail findings:")
        for finding in sorted(findings):
            print(f"  - {finding}")
    else:
        print("Extra guardrails passed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
