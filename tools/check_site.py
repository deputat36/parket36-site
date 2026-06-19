#!/usr/bin/env python3
"""Static checks for parket36.ru.

Runs without third-party dependencies and fails CI on broken local links,
missing SEO essentials, obsolete navigation and accidental legacy content.
Additional quality signals are reported as warnings so they can be improved
incrementally without blocking urgent content updates.
"""

from __future__ import annotations

from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://parket36.ru"
IGNORED_DIRS = {".git", ".github", "tools", "node_modules", "_site"}
CURRENT_THEME = "#6f4628"
PUBLIC_TEXT_SUFFIXES = {".html", ".css", ".js", ".json", ".xml", ".txt"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_count = 0
        self.in_title = False
        self.title_text: list[str] = []
        self.h1_count = 0
        self.description_count = 0
        self.description_values: list[str] = []
        self.canonicals: list[str] = []
        self.robots = ""
        self.og_counts: dict[str, int] = defaultdict(int)
        self.theme_colors: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.images_without_alt = 0
        self.main_scripts_without_defer = 0
        self.skip_text_depth = 0

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs = {k.lower(): (v or "") for k, v in attrs_list}

        if tag == "title":
            self.title_count += 1
            self.in_title = True
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "meta":
            name = attrs.get("name", "").lower()
            prop = attrs.get("property", "").lower()
            if name == "description":
                self.description_count += 1
                self.description_values.append(attrs.get("content", "").strip())
            elif name == "robots":
                self.robots = attrs.get("content", "").lower()
            elif name == "theme-color":
                self.theme_colors.append(attrs.get("content", "").strip().lower())
            if prop in {"og:title", "og:description", "og:image", "og:url"}:
                self.og_counts[prop] += 1
                if prop == "og:image":
                    self.links.append(("og:image", attrs.get("content", "")))
        elif tag == "link" and attrs.get("rel", "").lower() == "canonical":
            self.canonicals.append(attrs.get("href", ""))
        elif tag == "img" and "alt" not in attrs:
            self.images_without_alt += 1
        elif tag == "script":
            src = attrs.get("src", "")
            if src.endswith("/js/main.js") or src == "/js/main.js":
                if "defer" not in attrs and "async" not in attrs:
                    self.main_scripts_without_defer += 1
            self.skip_text_depth += 1
        elif tag in {"style", "svg"}:
            self.skip_text_depth += 1

        for attr in ("href", "src"):
            value = attrs.get(attr)
            if value:
                self.links.append((attr, value))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif tag in {"script", "style", "svg"} and self.skip_text_depth:
            self.skip_text_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_text.append(data)


def is_ignored_path(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.relative_to(ROOT).parts)


def iter_html_files() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*.html"):
        if is_ignored_path(path):
            continue
        result.append(path)
    return sorted(result)


def iter_public_text_files() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or is_ignored_path(path):
            continue
        if path.suffix.lower() in PUBLIC_TEXT_SUFFIXES:
            result.append(path)
    return sorted(result)


def resolve_local(value: str) -> Path | None:
    value = value.strip()
    if not value or value.startswith(("#", "tel:", "mailto:", "javascript:", "data:")):
        return None
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        if value.startswith(DOMAIN + "/"):
            path = parsed.path
        else:
            return None
    else:
        path = parsed.path
    if not path.startswith("/"):
        return None
    relative = path.lstrip("/")
    if not relative:
        return ROOT / "index.html"
    candidate = ROOT / relative
    if path.endswith("/"):
        return candidate / "index.html"
    if candidate.suffix:
        return candidate
    if candidate.is_dir() or not candidate.exists():
        return candidate / "index.html"
    return candidate


def page_url(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    if rel == "index.html":
        return DOMAIN + "/"
    if rel.endswith("/index.html"):
        return DOMAIN + "/" + rel.removesuffix("index.html")
    return DOMAIN + "/" + rel


def normalized_title(parser: PageParser) -> str:
    return " ".join("".join(parser.title_text).split())


def check_dynamic_css(errors: list[str]) -> None:
    main_js = ROOT / "js" / "main.js"
    if not main_js.exists():
        errors.append("js/main.js is missing")
        return

    text = main_js.read_text(encoding="utf-8")
    hrefs = sorted(set(re.findall(r"ensureStylesheet\(['\"]([^'\"]+)['\"]\)", text)))
    if not hrefs:
        errors.append("js/main.js does not register dynamic stylesheets")
        return

    for href in hrefs:
        if not href.startswith("/css/") or not href.endswith(".css"):
            errors.append(f"js/main.js: unexpected dynamic stylesheet path: {href}")
            continue
        target = resolve_local(href)
        if target is None or not target.exists():
            errors.append(f"js/main.js: dynamic stylesheet does not exist: {href}")


def check_repository_safety(errors: list[str]) -> None:
    forbidden_paths = [
        ROOT / "app-v4.html",
        ROOT / "crm-v4.html",
        ROOT / "assets" / "v4",
        ROOT / "assets" / "leader",
    ]
    for path in forbidden_paths:
        if path.exists():
            errors.append(f"Unexpected legacy/CRM path is present: {path.relative_to(ROOT)}")

    forbidden_public_terms = {
        "installationJobCardV1": "CRM installation card component",
        "leader_installation_jobs": "CRM leader database table",
        "assets/v4": "CRM v4 asset path",
        "app-v4.html": "CRM v4 HTML page",
        "ivan-work-suit": "artificial workwear image asset",
    }
    for path in iter_public_text_files():
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle, label in forbidden_public_terms.items():
            if needle in text:
                errors.append(f"{rel}: contains forbidden {label}: {needle}")


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    indexable_urls: set[str] = set()
    html_files = iter_html_files()
    titles: dict[str, list[str]] = defaultdict(list)
    canonicals_seen: dict[str, list[str]] = defaultdict(list)

    check_repository_safety(errors)
    check_dynamic_css(errors)

    if not html_files:
        errors.append("No HTML files found")

    for path in html_files:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(text)
        noindex = "noindex" in parser.robots
        title = normalized_title(parser)

        if parser.title_count != 1:
            errors.append(f"{rel}: expected one <title>, found {parser.title_count}")
        elif title:
            titles[title].append(rel)
            if len(title) < 25:
                warnings.append(f"{rel}: title is very short ({len(title)} chars)")
            elif len(title) > 75:
                warnings.append(f"{rel}: title is long ({len(title)} chars)")

        if parser.description_count != 1:
            errors.append(f"{rel}: expected one meta description, found {parser.description_count}")
        elif parser.description_values:
            length = len(parser.description_values[0])
            if length < 70:
                warnings.append(f"{rel}: meta description is short ({length} chars)")
            elif length > 190:
                warnings.append(f"{rel}: meta description is long ({length} chars)")

        if parser.h1_count != 1:
            errors.append(f"{rel}: expected one <h1>, found {parser.h1_count}")
        if len(parser.canonicals) != 1:
            errors.append(f"{rel}: expected one canonical, found {len(parser.canonicals)}")
        elif not parser.canonicals[0].startswith(DOMAIN):
            errors.append(f"{rel}: canonical must use {DOMAIN}")
        elif not noindex:
            canonicals_seen[parser.canonicals[0]].append(rel)

        if rel == "404.html" and not noindex:
            errors.append("404.html must be noindex, follow")
        if rel in {"politika/index.html", "uslugi/master-na-chas/index.html"} and not noindex:
            errors.append(f"{rel}: utility/redirect page must be noindex")

        if not noindex and rel != "404.html":
            indexable_urls.add(page_url(path))
            for prop in ("og:title", "og:description", "og:image", "og:url"):
                if parser.og_counts[prop] != 1:
                    warnings.append(f"{rel}: expected one {prop}, found {parser.og_counts[prop]}")
            if parser.theme_colors != [CURRENT_THEME]:
                warnings.append(f"{rel}: theme-color should be {CURRENT_THEME}")

        if parser.images_without_alt:
            warnings.append(f"{rel}: {parser.images_without_alt} image(s) without alt attribute")
        if parser.main_scripts_without_defer:
            warnings.append(f"{rel}: /js/main.js should use defer or async")

        hard_forbidden = {
            "WhatsApp": "legacy messenger reference",
            "wa.me": "legacy WhatsApp URL",
            "Ключевые запросы по услуге": "visible SEO keyword block",
            "/#process": "obsolete process anchor",
        }
        for needle, label in hard_forbidden.items():
            if needle in text:
                errors.append(f"{rel}: contains {label}: {needle}")

        soft_forbidden = {
            'content="#164e63"': "legacy theme color",
        }
        for needle, label in soft_forbidden.items():
            if needle in text:
                warnings.append(f"{rel}: contains {label}: {needle}")

        if rel != "uslugi/master-na-chas/index.html" and "/uslugi/master-na-chas/" in text:
            errors.append(f"{rel}: links to consolidated master-na-chas page")

        if "https://max.ru/" in text:
            warnings.append(f"{rel}: generic MAX link is still used")

        for attr, value in parser.links:
            if attr == "og:image" and any(part in value for part in ("/img/work-", "/img/hero-master.svg", "/img/ivan-hero.svg")):
                warnings.append(f"{rel}: uses service placeholder as og:image: {value}")

            target = resolve_local(value)
            if target is not None and not target.exists():
                errors.append(f"{rel}: broken local {attr}={value} -> {target.relative_to(ROOT)}")

    for title, pages in sorted(titles.items()):
        if len(pages) > 1:
            warnings.append(f"Duplicate title in {', '.join(pages)}: {title}")
    for canonical, pages in sorted(canonicals_seen.items()):
        if len(pages) > 1:
            warnings.append(f"Duplicate canonical in {', '.join(pages)}: {canonical}")

    robots = ROOT / "robots.txt"
    if not robots.exists():
        errors.append("robots.txt is missing")
    elif "Sitemap: https://parket36.ru/sitemap.xml" not in robots.read_text(encoding="utf-8"):
        errors.append("robots.txt does not reference the canonical sitemap")

    sitemap = ROOT / "sitemap.xml"
    sitemap_urls: set[str] = set()
    if not sitemap.exists():
        errors.append("sitemap.xml is missing")
    else:
        try:
            tree = ET.parse(sitemap)
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            sitemap_urls = {
                (node.text or "").strip()
                for node in tree.findall("sm:url/sm:loc", ns)
                if (node.text or "").strip()
            }
        except ET.ParseError as exc:
            errors.append(f"sitemap.xml is invalid XML: {exc}")

    for url in sorted(indexable_urls - sitemap_urls):
        errors.append(f"Indexable page is absent from sitemap: {url}")
    for url in sorted(sitemap_urls - indexable_urls):
        target = resolve_local(url)
        if target is None or not target.exists():
            errors.append(f"Sitemap URL does not resolve to a page: {url}")

    print(f"Checked {len(html_files)} HTML pages")
    if warnings:
        print("\nWarnings:")
        for warning in sorted(set(warnings)):
            print(f"  - {warning}")
    if errors:
        print("\nErrors:")
        for error in sorted(set(errors)):
            print(f"  - {error}")
        return 1
    print("\nSite audit passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
