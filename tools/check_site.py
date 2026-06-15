#!/usr/bin/env python3
"""Static checks for parket36.ru.

Runs without third-party dependencies and fails CI on broken local links,
missing SEO essentials, obsolete navigation and accidental legacy content.
"""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://parket36.ru"
IGNORED_DIRS = {".git", ".github", "tools", "node_modules", "_site"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_count = 0
        self.in_title = False
        self.title_text: list[str] = []
        self.h1_count = 0
        self.description_count = 0
        self.canonicals: list[str] = []
        self.robots = ""
        self.links: list[tuple[str, str]] = []
        self.visible_text: list[str] = []
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
            if name == "robots":
                self.robots = attrs.get("content", "").lower()
            if prop == "og:image":
                self.links.append(("og:image", attrs.get("content", "")))
        elif tag == "link" and attrs.get("rel", "").lower() == "canonical":
            self.canonicals.append(attrs.get("href", ""))
        elif tag in {"script", "style", "svg"}:
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
        if not self.skip_text_depth and data.strip():
            self.visible_text.append(data.strip())


def iter_html_files() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*.html"):
        if any(part in IGNORED_DIRS for part in path.relative_to(ROOT).parts):
            continue
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


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    indexable_urls: set[str] = set()
    html_files = iter_html_files()

    if not html_files:
        errors.append("No HTML files found")

    for path in html_files:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(text)
        visible = " ".join(parser.visible_text)
        noindex = "noindex" in parser.robots

        if parser.title_count != 1:
            errors.append(f"{rel}: expected one <title>, found {parser.title_count}")
        if parser.description_count != 1:
            errors.append(f"{rel}: expected one meta description, found {parser.description_count}")
        if parser.h1_count != 1:
            errors.append(f"{rel}: expected one <h1>, found {parser.h1_count}")
        if len(parser.canonicals) != 1:
            errors.append(f"{rel}: expected one canonical, found {len(parser.canonicals)}")
        elif not parser.canonicals[0].startswith(DOMAIN):
            errors.append(f"{rel}: canonical must use {DOMAIN}")

        if rel == "404.html" and not noindex:
            errors.append("404.html must be noindex, follow")
        if rel in {"politika/index.html", "uslugi/master-na-chas/index.html"} and not noindex:
            errors.append(f"{rel}: utility/redirect page must be noindex")

        if not noindex and rel != "404.html":
            indexable_urls.add(page_url(path))

        forbidden = {
            "WhatsApp": "legacy messenger reference",
            "wa.me": "legacy WhatsApp URL",
            "Ключевые запросы по услуге": "visible SEO keyword block",
            "/#process": "obsolete process anchor",
        }
        for needle, label in forbidden.items():
            if needle in text:
                errors.append(f"{rel}: contains {label}: {needle}")

        if rel != "uslugi/master-na-chas/index.html" and "/uslugi/master-na-chas/" in text:
            errors.append(f"{rel}: links to consolidated master-na-chas page")

        if "https://max.ru/" in text:
            warnings.append(f"{rel}: generic MAX link is still used")

        for attr, value in parser.links:
            target = resolve_local(value)
            if target is not None and not target.exists():
                errors.append(f"{rel}: broken local {attr}={value} -> {target.relative_to(ROOT)}")

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
