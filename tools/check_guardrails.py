#!/usr/bin/env python3
"""Extra blocking guardrails for public Parket36 pages.

This script catches focused project regressions that are useful to keep separate
from the broader static audit in tools/check_site.py.
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
    "uslugi/master-na-chas/",
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

INTERNAL_NOINDEX_PAGES = {
    "foto-dlya-sajta/": "internal photo brief should stay noindex",
    "politika/": "privacy policy should stay noindex",
    "portfolio/shablon-kejsa/": "internal portfolio case template should stay noindex",
}

PUBLIC_ENTRY_PAGES = {
    "zayavka/": "photo assessment request page should stay public and indexable",
}

CTA_LABEL_GUARDRAIL_PAGES = {
    "ceny/index.html",
    "kontakty/index.html",
    "o-mastere/index.html",
    "sovety/kak-sfotografirovat-pol-dlya-ocenki/index.html",
    "uslugi/ciklevka-parketa/index.html",
    "uslugi/index.html",
    "uslugi/parket-i-poly/index.html",
    "uslugi/pokrytie-lakom-i-maslom/index.html",
    "uslugi/restavraciya-parketa/index.html",
    "uslugi/shlifovka-doshchatogo-pola/index.html",
    "uslugi/terrasy-i-derevyannye-poly/index.html",
    "uslugi/ukladka-laminata/index.html",
    "uslugi/ukladka-parketa/index.html",
}

PHOTO_ASSESSMENT_FORM_MARKERS = {
    'id="request-photos"': "photo readiness field",
    'id="request-video"': "video readiness field",
    "insertAssessmentSelect": "request forms should backfill photo/video fields when HTML lacks them",
    "Фото:": "copied text should include photo readiness",
    "Видео скрипа/подвижности:": "copied text should include video readiness",
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
        "Сопутствующие вопросы": "homepage should stay focused on parquet and floor-specific adjacent details",
        "Дополнительные задачи согласуются отдельно": "homepage should not end the process with broad task wording",
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

STALE_CTA_MARKERS = {
    "Составить заявку": "key public page should use direct photo assessment CTA language",
    "Подготовить заявку": "key public page should use direct photo assessment CTA language",
    "подготовьте заявку": "key public page should use direct photo assessment CTA language",
}

DATE_RE = r"\d{4}-\d{2}-\d{2}"
NOINDEX_META = '<meta name="robots" content="noindex, follow">'


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


def sitemap_text() -> str:
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.exists():
        return ""
    return sitemap.read_text(encoding="utf-8", errors="ignore")


def extract_sitemap_urls() -> set[str]:
    return set(re.findall(r"<loc>(.*?)</loc>", sitemap_text()))


def extract_sitemap_lastmods() -> dict[str, str]:
    lastmods: dict[str, str] = {}
    for url_block in re.findall(r"<url>(.*?)</url>", sitemap_text(), flags=re.DOTALL):
        loc_match = re.search(r"<loc>(.*?)</loc>", url_block)
        lastmod_match = re.search(rf"<lastmod>({DATE_RE})</lastmod>", url_block)
        if loc_match and lastmod_match:
            lastmods[loc_match.group(1)] = lastmod_match.group(1)
    return lastmods


def canonical_url_for_html(path: Path) -> str | None:
    rel = path.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return f"{SITE_URL}/"
    if not rel.endswith("/index.html"):
        return None
    return f"{SITE_URL}/{rel.removesuffix('index.html')}"


def html_path_for_site_url(url: str) -> Path | None:
    if url == f"{SITE_URL}/":
        return ROOT / "index.html"
    prefix = f"{SITE_URL}/"
    if not url.startswith(prefix):
        return None
    url_path = url.removeprefix(prefix)
    if not url_path.endswith("/"):
        return None
    return html_path_for_url_path(url_path)


def extract_declared_canonical(text: str) -> str | None:
    match = re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', text)
    if match:
        return match.group(1)
    return None


def extract_date_modified_values(text: str) -> list[str]:
    return re.findall(rf'"dateModified"\s*:\s*"({DATE_RE})"', text)


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

    sitemap_urls = extract_sitemap_urls()
    sitemap_lastmods = extract_sitemap_lastmods()

    for url in sorted(sitemap_urls):
        html_path = html_path_for_site_url(url)
        if html_path is None:
            findings.append(f"sitemap.xml: unsupported URL format: {url}")
            continue
        rel = html_path.relative_to(ROOT).as_posix()
        if not html_path.exists():
            findings.append(f"sitemap.xml: listed URL has no matching HTML file: {url} -> {rel}")
            continue
        text = html_path.read_text(encoding="utf-8", errors="ignore")
        if NOINDEX_META in text:
            findings.append(f"sitemap.xml: listed URL should not be noindex: {url}")

    for path in html_files():
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        parser = BasicHtmlParser()
        parser.feed(text)
        if parser.lang != "ru":
            findings.append(f"{rel}: html lang should be ru")
        if parser.viewport_count != 1:
            findings.append(f"{rel}: expected one viewport meta, found {parser.viewport_count}")

        url = canonical_url_for_html(path)
        declared_canonical = extract_declared_canonical(text)
        if url and declared_canonical and declared_canonical != url:
            findings.append(f"{rel}: canonical should be {url}, found {declared_canonical}")

        if url and declared_canonical and declared_canonical.startswith(SITE_URL) and NOINDEX_META not in text and url not in sitemap_urls:
            findings.append(f"sitemap.xml: indexable canonical page should be listed: {url}")

        date_modified_values = extract_date_modified_values(text)
        if url in sitemap_urls and date_modified_values:
            expected_lastmod = max(date_modified_values)
            actual_lastmod = sitemap_lastmods.get(url)
            if actual_lastmod != expected_lastmod:
                findings.append(
                    f"sitemap.xml: lastmod for {url} should match dateModified "
                    f"{expected_lastmod}, found {actual_lastmod or 'missing'}"
                )

    index = ROOT / "index.html"
    index_text = index.read_text(encoding="utf-8", errors="ignore") if index.exists() else ""
    required_form_markers = {
        'id="request-location"': "request location field",
        'id="request-area"': "request area field",
        'id="request-photos"': "request photo readiness field",
        'id="request-video"': "request video readiness field",
        'id="request-task"': "request task field",
        'id="request-callback"': "request callback field",
        'id="request-contact"': "request contact field",
        'autocomplete="tel"': "telephone autocomplete",
        'inputmode="tel"': "telephone input mode",
    }
    for marker, label in required_form_markers.items():
        if marker not in index_text:
            findings.append(f"index.html: missing {label}: {marker}")

    zayavka = ROOT / "zayavka" / "index.html"
    zayavka_text = zayavka.read_text(encoding="utf-8", errors="ignore") if zayavka.exists() else ""
    js = ROOT / "js" / "main.js"
    js_text = js.read_text(encoding="utf-8", errors="ignore") if js.exists() else ""
    for marker, label in PHOTO_ASSESSMENT_FORM_MARKERS.items():
        if marker.startswith('id='):
            if marker not in zayavka_text:
                findings.append(f"zayavka/index.html: missing {label}: {marker}")
        elif marker not in js_text:
            findings.append(f"js/main.js: missing {label}: {marker}")

    for rel, markers in FOCUS_PAGE_PROMOTED_MARKERS.items():
        path = ROOT / rel
        if not path.exists():
            findings.append(f"{rel}: focus page is missing")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker, label in markers.items():
            if marker in text:
                findings.append(f"{rel}: {label}: {marker}")

    for rel in sorted(CTA_LABEL_GUARDRAIL_PAGES):
        path = ROOT / rel
        if not path.exists():
            findings.append(f"{rel}: CTA guardrail page is missing")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker, label in STALE_CTA_MARKERS.items():
            if marker in text:
                findings.append(f"{rel}: {label}: {marker}")

    for page_path in sorted(SUPPLEMENTAL_SERVICE_PAGES):
        html_path = html_path_for_url_path(page_path)
        rel = html_path.relative_to(ROOT).as_posix()
        if not html_path.exists():
            findings.append(f"{rel}: supplemental service page is missing")
            continue

        text = html_path.read_text(encoding="utf-8", errors="ignore")
        if NOINDEX_META not in text:
            findings.append(f"{rel}: supplemental service page should be noindex, follow")

        url = f"{SITE_URL}/{page_path}"
        if url in sitemap_urls:
            findings.append(f"sitemap.xml: supplemental service page should not be listed: {url}")

    for page_path, label in sorted(INTERNAL_NOINDEX_PAGES.items()):
        html_path = html_path_for_url_path(page_path)
        rel = html_path.relative_to(ROOT).as_posix()
        if not html_path.exists():
            findings.append(f"{rel}: internal page is missing")
            continue

        text = html_path.read_text(encoding="utf-8", errors="ignore")
        if NOINDEX_META not in text:
            findings.append(f"{rel}: {label}: should be noindex, follow")

        url = f"{SITE_URL}/{page_path}"
        if url in sitemap_urls:
            findings.append(f"sitemap.xml: internal page should not be listed: {url}")

    for page_path, label in sorted(PUBLIC_ENTRY_PAGES.items()):
        html_path = html_path_for_url_path(page_path)
        rel = html_path.relative_to(ROOT).as_posix()
        if not html_path.exists():
            findings.append(f"{rel}: public entry page is missing")
            continue

        text = html_path.read_text(encoding="utf-8", errors="ignore")
        if NOINDEX_META in text:
            findings.append(f"{rel}: {label}: must not be noindex")

        url = f"{SITE_URL}/{page_path}"
        if url not in sitemap_urls:
            findings.append(f"sitemap.xml: public entry page should be listed: {url}")

    if findings:
        print("Extra guardrail findings:")
        for finding in sorted(findings):
            print(f"  - {finding}")
        return 1

    print("Extra guardrails passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())