#!/usr/bin/env python3
"""Build deterministic Markdown and CSV inventories for public Parket36 pages."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlsplit, urlunsplit

from site_settings import load_config

ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config()
DOMAIN = str(CONFIG["domain"]).rstrip("/")
IGNORED_DIRS = {".git", ".github", "tools", "data", "node_modules", "_site"}
INTERNAL_WORKING_PATHS = {
    Path("foto-dlya-sajta") / "index.html",
    Path("portfolio") / "shablon-kejsa" / "index.html",
}
WORD_RE = re.compile(r"[0-9A-Za-zА-Яа-яЁё]+(?:[-–—][0-9A-Za-zА-Яа-яЁё]+)*")
THIN_WORD_LIMIT = 250


@dataclass
class PageRecord:
    url: str
    source_path: str
    section: str
    title: str
    h1: str
    description: str
    robots: str
    word_count: int
    inbound_links: int
    outbound_links: int
    phone_links: int
    request_links: int
    has_request_form: bool
    lastmod: str
    title_duplicate_count: int
    h1_duplicate_count: int


class InventoryParser(HTMLParser):
    """Extract SEO, conversion and visible-text signals from one HTML page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.description = ""
        self.robots = ""
        self.canonical = ""
        self.links: list[str] = []
        self.phone_links = 0
        self.request_links = 0
        self.has_request_form = False
        self.visible_parts: list[str] = []
        self.in_title = False
        self.in_h1 = False
        self.in_body = False
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs = {key.lower(): (value or "") for key, value in attrs_list}

        if tag == "body":
            self.in_body = True
        elif tag in {"script", "style", "svg", "noscript"}:
            self.skip_depth += 1
        elif tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.in_h1 = True
        elif tag == "meta":
            name = attrs.get("name", "").lower()
            if name == "description":
                self.description = attrs.get("content", "").strip()
            elif name == "robots":
                self.robots = attrs.get("content", "").strip().lower()
        elif tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonical = attrs.get("href", "").strip()
        elif tag == "form" and attrs.get("id") == "request-form":
            self.has_request_form = True

        href = attrs.get("href", "").strip()
        if href:
            self.links.append(href)
            if href.startswith("tel:"):
                self.phone_links += 1
            if href == "#request" or href.startswith("/zayavka/"):
                self.request_links += 1

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "body":
            self.in_body = False
        elif tag in {"script", "style", "svg", "noscript"} and self.skip_depth:
            self.skip_depth -= 1
        elif tag == "title":
            self.in_title = False
        elif tag == "h1":
            self.in_h1 = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.in_h1:
            self.h1_parts.append(data)
        if self.in_body and self.skip_depth == 0:
            value = " ".join(data.split())
            if value:
                self.visible_parts.append(value)


def clean_text(parts: list[str]) -> str:
    return " ".join(" ".join(parts).split())


def iter_public_html() -> list[Path]:
    pages: list[Path] = []
    for path in ROOT.rglob("*.html"):
        relative = path.relative_to(ROOT)
        if any(part in IGNORED_DIRS for part in relative.parts):
            continue
        if relative in INTERNAL_WORKING_PATHS:
            continue
        pages.append(path)
    return sorted(pages)


def normalize_url(value: str, base_url: str = "") -> str | None:
    value = value.strip()
    if not value or value.startswith(("#", "tel:", "mailto:", "javascript:", "data:")):
        return None

    absolute = urljoin(base_url or DOMAIN + "/", value)
    parsed = urlsplit(absolute)
    domain = urlsplit(DOMAIN)
    if parsed.scheme not in {"http", "https"} or parsed.netloc != domain.netloc:
        return None

    path = parsed.path or "/"
    if not Path(path).suffix and not path.endswith("/"):
        path += "/"
    return urlunsplit((domain.scheme, domain.netloc, path, "", ""))


def section_for_url(url: str) -> str:
    path = urlsplit(url).path.strip("/")
    return path.split("/", 1)[0] if path else "home"


def load_lastmods() -> dict[str, str]:
    sitemap = ROOT / "sitemap.xml"
    if not sitemap.is_file():
        return {}
    try:
        tree = ET.parse(sitemap)
    except ET.ParseError:
        return {}

    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    result: dict[str, str] = {}
    for node in tree.findall("sm:url", namespace):
        loc = node.find("sm:loc", namespace)
        lastmod = node.find("sm:lastmod", namespace)
        if loc is None or not (loc.text or "").strip():
            continue
        normalized = normalize_url((loc.text or "").strip())
        if normalized:
            result[normalized] = (lastmod.text or "").strip() if lastmod is not None else ""
    return result


def collect_pages() -> tuple[list[PageRecord], list[str]]:
    parsed_pages: list[tuple[Path, InventoryParser, str]] = []
    findings: list[str] = []

    for path in iter_public_html():
        parser = InventoryParser()
        parser.feed(path.read_text(encoding="utf-8"))
        relative = path.relative_to(ROOT).as_posix()
        canonical = normalize_url(parser.canonical)
        if canonical is None:
            findings.append(f"{relative}: canonical is missing or outside {DOMAIN}")
            continue
        parsed_pages.append((path, parser, canonical))

    canonical_urls = {canonical for _, _, canonical in parsed_pages}
    inbound: Counter[str] = Counter()
    outbound_counts: dict[str, int] = {}

    for _, parser, canonical in parsed_pages:
        targets: set[str] = set()
        for href in parser.links:
            target = normalize_url(href, canonical)
            if target and target in canonical_urls and target != canonical:
                targets.add(target)
        outbound_counts[canonical] = len(targets)
        for target in targets:
            inbound[target] += 1

    title_counts = Counter(clean_text(parser.title_parts) for _, parser, _ in parsed_pages)
    h1_counts = Counter(clean_text(parser.h1_parts) for _, parser, _ in parsed_pages)
    lastmods = load_lastmods()
    records: list[PageRecord] = []

    for path, parser, canonical in parsed_pages:
        title = clean_text(parser.title_parts)
        h1 = clean_text(parser.h1_parts)
        words = WORD_RE.findall(" ".join(parser.visible_parts))
        records.append(
            PageRecord(
                url=canonical,
                source_path=path.relative_to(ROOT).as_posix(),
                section=section_for_url(canonical),
                title=title,
                h1=h1,
                description=parser.description,
                robots=parser.robots,
                word_count=len(words),
                inbound_links=inbound[canonical],
                outbound_links=outbound_counts.get(canonical, 0),
                phone_links=parser.phone_links,
                request_links=parser.request_links,
                has_request_form=parser.has_request_form,
                lastmod=lastmods.get(canonical, ""),
                title_duplicate_count=title_counts[title] if title else 0,
                h1_duplicate_count=h1_counts[h1] if h1 else 0,
            )
        )

    return sorted(records, key=lambda item: item.url), findings


def csv_text(records: list[PageRecord]) -> str:
    output = StringIO(newline="")
    fieldnames = list(asdict(records[0]).keys()) if records else [field.name for field in PageRecord.__dataclass_fields__.values()]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow(asdict(record))
    return output.getvalue()


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def markdown_text(records: list[PageRecord]) -> str:
    indexable = [record for record in records if "noindex" not in record.robots]
    thin = [record for record in indexable if record.word_count < THIN_WORD_LIMIT]
    orphan_candidates = [record for record in indexable if record.inbound_links == 0 and record.section != "home"]
    duplicate_titles = sum(1 for record in records if record.title_duplicate_count > 1)
    duplicate_h1s = sum(1 for record in records if record.h1_duplicate_count > 1)
    with_phone = sum(1 for record in records if record.phone_links > 0)
    with_request = sum(1 for record in records if record.request_links > 0 or record.has_request_form)

    lines = [
        "# Content inventory Паркет36",
        "",
        "Файл генерируется командой `python tools/build_content_inventory.py --output-dir reports/content-inventory`.",
        "Ручное редактирование таблицы не требуется: источником являются публичные HTML-страницы и `sitemap.xml`.",
        "",
        "## Сводка",
        "",
        f"- публичных страниц: {len(records)};",
        f"- индексируемых страниц: {len(indexable)};",
        f"- страниц короче {THIN_WORD_LIMIT} слов: {len(thin)};",
        f"- кандидатов без входящих внутренних ссылок: {len(orphan_candidates)};",
        f"- страниц с повторяющимся title: {duplicate_titles};",
        f"- страниц с повторяющимся H1: {duplicate_h1s};",
        f"- страниц со ссылкой на телефон: {with_phone};",
        f"- страниц с путём к заявке или формой: {with_request}.",
        "",
        "Показатели `короче 250 слов` и `без входящих ссылок` являются сигналами для проверки, а не автоматическим выводом о низком качестве страницы.",
        "",
        "## Реестр страниц",
        "",
        "| URL | Раздел | Слов | Входящие | Исходящие | Телефон | Заявка | Форма | Lastmod | Title |",
        "|---|---:|---:|---:|---:|---:|---:|:---:|---|---|",
    ]

    for record in records:
        lines.append(
            "| {url} | {section} | {words} | {incoming} | {outgoing} | {phone} | {request} | {form} | {lastmod} | {title} |".format(
                url=markdown_escape(record.url),
                section=markdown_escape(record.section),
                words=record.word_count,
                incoming=record.inbound_links,
                outgoing=record.outbound_links,
                phone=record.phone_links,
                request=record.request_links,
                form="да" if record.has_request_form else "нет",
                lastmod=record.lastmod or "—",
                title=markdown_escape(record.title),
            )
        )

    lines.extend(
        [
            "",
            "## Поля CSV",
            "",
            "CSV дополнительно содержит исходный путь, description, robots, H1 и количество точных дублей title/H1. Эти поля используются следующими этапами SEO-аудита.",
            "",
        ]
    )
    return "\n".join(lines)


def write_inventory(output_dir: Path) -> tuple[Path, Path, list[str]]:
    records, findings = collect_pages()
    if not records:
        findings.append("No public pages were collected")
        return output_dir / "content-inventory.csv", output_dir / "content-inventory.md", findings

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "content-inventory.csv"
    markdown_path = output_dir / "content-inventory.md"
    csv_path.write_text(csv_text(records), encoding="utf-8")
    markdown_path.write_text(markdown_text(records), encoding="utf-8")
    return csv_path, markdown_path, findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="reports/content-inventory")
    args = parser.parse_args()

    output_dir = ROOT / args.output_dir
    csv_path, markdown_path, findings = write_inventory(output_dir)
    if findings:
        print("Content inventory findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print(f"Wrote {csv_path.relative_to(ROOT)}")
    print(f"Wrote {markdown_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
