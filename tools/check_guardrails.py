#!/usr/bin/env python3
"""Extra non-blocking guardrails for public Parket36 pages.

This script prints additional findings that are useful during review. The main
blocking audit still lives in tools/check_site.py.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {".git", ".github", "tools", "node_modules", "_site"}
PUBLIC_SUFFIXES = {".html", ".css", ".js", ".json", ".xml", ".txt"}
SITE_URL = "https://parket36.ru"

SUPPLEMENTAL_SERVICE_PAGES = {
    "uslugi/muzh-na-chas/",
    "uslugi/melkiy-remont/",
    "uslugi/elektrika/",
    "uslugi/santehnika/",
    "uslugi/vyvoz-musora/",
    "uslugi/demontazh/",
    "uslugi/pereezdy/",
    "uslugi/sborka-mebeli/",
    "uslugi/otdelka/",
}

PUBLIC_ENTRY_PAGES = {
    "zayavka/": "photo assessment request page should stay public and indexable",
}

FOCUS_PAGE_PROMOTED_MARKERS = {
    "index.html": {
        ">Муж на час<": "homepage should not promote husband-for-an-hour as a card or option",
        ">Мелкий ремонт<": "homepage should not promote small repairs as a card or option",
        ">Сборка мебели<": "homepage should not promote furniture assembly as a separate option",
        ">Электрика<": "homepage should not promote electrical work as a separate option",
        ">Сантехника<": "homepage should not promote plumbing as a separate option",
        ">Отделка<": "homepage should not promote finishing as a separate option",
        ">Демонтаж / вывоз<": "homepage should not promote demolition/removal as a separate option",
    },
    "uslugi/index.html": {
        ">Муж на час<": "services index should not promote husband-for-an-hour as a category",
        ">Мелкий ремонт<": "services index should not promote small repairs as a category",
        ">Сборка мебели<": "services index should not promote furniture assembly as a category",
        ">Электрика<": "services index should not promote electrical work as a category",
        ">Сантехника<": "services index should not promote plumbing as a category",
        ">Отделка<": "services index should not promote finishing as a category",
        ">Переезды<": "services index should not promote moving as a category",
        ">Вывоз мусора<": "services index should not promote trash removal as a category",
    },
}


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


def html_path_for_url_path(url_path: str) -> Path:
    return ROOT / url_path / "index.html"


def extract_sitemap_urls() -> set[str]:
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.exists():
        return set()
    text = sitemap.read_text(encoding="utf-8", errors="ignore")
    return set(re.findall(r"<loc>(.*?)</loc>", text))


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

    for rel, markers in FOCUS_PAGE_PROMOTED_MARKERS.items():
        path = ROOT / rel
        if not path.exists():
            findings.append(f"{rel}: focus page is missing")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker, label in markers.items():
            if marker in text:
                findings.append(f"{rel}: {label}: {marker}")

    sitemap_urls = extract_sitemap_urls()
    for page_path in sorted(SUPPLEMENTAL_SERVICE_PAGES):
        html_path = html_path_for_url_path(page_path)
        rel = html_path.relative_to(ROOT).as_posix()
        if not html_path.exists():
            findings.append(f"{rel}: supplemental service page is missing")
            continue

        text = html_path.read_text(encoding="utf-8", errors="ignore")
        if '<meta name="robots" content="noindex, follow">' not in text:
            findings.append(f"{rel}: supplemental service page should be noindex, follow")

        url = f"{SITE_URL}/{page_path}"
        if url in sitemap_urls:
            findings.append(f"sitemap.xml: supplemental service page should not be listed: {url}")

    for page_path, label in sorted(PUBLIC_ENTRY_PAGES.items()):
        html_path = html_path_for_url_path(page_path)
        rel = html_path.relative_to(ROOT).as_posix()
        if not html_path.exists():
            findings.append(f"{rel}: public entry page is missing")
            continue

        text = html_path.read_text(encoding="utf-8", errors="ignore")
        if '<meta name="robots" content="noindex, follow">' in text:
            findings.append(f"{rel}: {label}: must not be noindex")

        url = f"{SITE_URL}/{page_path}"
        if url not in sitemap_urls:
            findings.append(f"sitemap.xml: public entry page should be listed: {url}")

    if findings:
        print("Extra guardrail findings:")
        for finding in sorted(findings):
            print(f"  - {finding}")
    else:
        print("Extra guardrails passed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
