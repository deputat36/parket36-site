#!/usr/bin/env python3
"""Generate sitemap.xml from indexable canonicals and structured page dates."""

from __future__ import annotations

import argparse
import datetime as dt
from dataclasses import dataclass
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from build_content_inventory import DOMAIN, ROOT, iter_public_html, normalize_url, section_for_url

SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"


@dataclass(frozen=True)
class SitemapMetadata:
    lastmod: str
    changefreq: str
    priority: str


@dataclass(frozen=True)
class SitemapPage:
    url: str
    source_path: str
    structured_date: str


class SitemapPageParser(HTMLParser):
    """Collect robots, canonical and JSON-LD blocks from a source page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.robots = ""
        self.canonical = ""
        self.in_json_ld = False
        self.json_ld_parts: list[str] = []
        self.json_ld_blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs = {key.lower(): (value or "") for key, value in attrs_list}
        if tag == "meta" and attrs.get("name", "").lower() == "robots":
            self.robots = attrs.get("content", "").strip().lower()
        elif tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonical = attrs.get("href", "").strip()
        elif tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self.in_json_ld = True
            self.json_ld_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self.in_json_ld:
            self.json_ld_blocks.append("".join(self.json_ld_parts).strip())
            self.in_json_ld = False
            self.json_ld_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_json_ld:
            self.json_ld_parts.append(data)


def valid_date(value: str) -> str:
    value = value.strip()
    dt.date.fromisoformat(value)
    return value


def iter_json_dates(value: object, key: str) -> list[str]:
    dates: list[str] = []
    if isinstance(value, dict):
        candidate = value.get(key)
        if isinstance(candidate, str):
            try:
                dates.append(valid_date(candidate[:10]))
            except ValueError:
                pass
        for child in value.values():
            dates.extend(iter_json_dates(child, key))
    elif isinstance(value, list):
        for child in value:
            dates.extend(iter_json_dates(child, key))
    return dates


def structured_date(blocks: list[str]) -> tuple[str, list[str]]:
    findings: list[str] = []
    modified: list[str] = []
    published: list[str] = []
    for block in blocks:
        if not block:
            continue
        try:
            payload = json.loads(block)
        except json.JSONDecodeError as exc:
            findings.append(f"invalid JSON-LD: {exc}")
            continue
        modified.extend(iter_json_dates(payload, "dateModified"))
        published.extend(iter_json_dates(payload, "datePublished"))
    if modified:
        return max(modified), findings
    if published:
        return max(published), findings
    return "", findings


def collect_pages() -> tuple[list[SitemapPage], list[str]]:
    pages: dict[str, SitemapPage] = {}
    findings: list[str] = []
    for path in iter_public_html():
        relative = path.relative_to(ROOT).as_posix()
        parser = SitemapPageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
        if "noindex" in parser.robots:
            continue
        canonical = normalize_url(parser.canonical)
        if canonical is None:
            findings.append(f"{relative}: canonical is missing or outside {DOMAIN}")
            continue
        page_date, date_findings = structured_date(parser.json_ld_blocks)
        findings.extend(f"{relative}: {finding}" for finding in date_findings)
        if canonical in pages:
            findings.append(
                f"Indexable canonical conflict: {canonical} is used by "
                f"{pages[canonical].source_path} and {relative}"
            )
            continue
        pages[canonical] = SitemapPage(
            url=canonical,
            source_path=relative,
            structured_date=page_date,
        )
    return sorted(pages.values(), key=lambda item: item.url), findings


def child_text(node: ET.Element, name: str) -> str:
    child = node.find(f"{{{SITEMAP_NAMESPACE}}}{name}")
    return (child.text or "").strip() if child is not None else ""


def load_existing(path: Path) -> tuple[list[str], dict[str, SitemapMetadata], list[str]]:
    findings: list[str] = []
    if not path.is_file():
        return [], {}, [f"{path.relative_to(ROOT)} is missing"]
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        return [], {}, [f"{path.relative_to(ROOT)} is invalid XML: {exc}"]

    order: list[str] = []
    metadata: dict[str, SitemapMetadata] = {}
    for node in tree.findall(f"{{{SITEMAP_NAMESPACE}}}url"):
        loc = normalize_url(child_text(node, "loc"))
        if loc is None:
            findings.append("sitemap entry has an invalid or external loc")
            continue
        if loc in metadata:
            findings.append(f"duplicate sitemap loc: {loc}")
            continue
        lastmod = child_text(node, "lastmod")
        if lastmod:
            try:
                lastmod = valid_date(lastmod)
            except ValueError:
                findings.append(f"{loc}: invalid lastmod {lastmod}")
        changefreq = child_text(node, "changefreq") or default_policy(loc).changefreq
        priority = child_text(node, "priority") or default_policy(loc).priority
        order.append(loc)
        metadata[loc] = SitemapMetadata(lastmod, changefreq, priority)
    return order, metadata, findings


def default_policy(url: str) -> SitemapMetadata:
    path = url.removeprefix(DOMAIN).strip("/")
    if not path:
        return SitemapMetadata("", "weekly", "1.0")
    section = section_for_url(url)
    if url == f"{DOMAIN}/sovety/":
        return SitemapMetadata("", "monthly", "0.8")
    if section == "sovety":
        return SitemapMetadata("", "yearly", "0.72")
    if url == f"{DOMAIN}/uslugi/":
        return SitemapMetadata("", "monthly", "0.9")
    if section == "uslugi":
        return SitemapMetadata("", "monthly", "0.8")
    if url == f"{DOMAIN}/resheniya/":
        return SitemapMetadata("", "monthly", "0.85")
    if section == "resheniya":
        return SitemapMetadata("", "monthly", "0.8")
    return SitemapMetadata("", "monthly", "0.8")


def build_entries(source_sitemap: Path) -> tuple[list[tuple[str, SitemapMetadata]], list[str]]:
    pages, findings = collect_pages()
    existing_order, existing, existing_findings = load_existing(source_sitemap)
    findings.extend(existing_findings)
    page_by_url = {page.url: page for page in pages}

    ordered_urls = [url for url in existing_order if url in page_by_url]
    ordered_urls.extend(sorted(set(page_by_url) - set(ordered_urls)))

    entries: list[tuple[str, SitemapMetadata]] = []
    for url in ordered_urls:
        page = page_by_url[url]
        old = existing.get(url)
        policy = old or default_policy(url)
        lastmod = page.structured_date or policy.lastmod
        if not lastmod:
            findings.append(
                f"{page.source_path}: new indexable page needs JSON-LD datePublished/dateModified "
                "or an approved sitemap lastmod"
            )
            continue
        entries.append(
            (
                url,
                SitemapMetadata(
                    lastmod=lastmod,
                    changefreq=policy.changefreq,
                    priority=policy.priority,
                ),
            )
        )
    return entries, findings


def sitemap_text(entries: list[tuple[str, SitemapMetadata]]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<urlset xmlns="{SITEMAP_NAMESPACE}">',
    ]
    for url, metadata in entries:
        lines.append(
            "  <url><loc>{url}</loc><lastmod>{lastmod}</lastmod>"
            "<changefreq>{changefreq}</changefreq><priority>{priority}</priority></url>".format(
                url=url,
                lastmod=metadata.lastmod,
                changefreq=metadata.changefreq,
                priority=metadata.priority,
            )
        )
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def write_sitemap(source_sitemap: Path, output: Path) -> tuple[Path, list[str]]:
    entries, findings = build_entries(source_sitemap)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(sitemap_text(entries), encoding="utf-8")
    return output, findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="sitemap.xml")
    parser.add_argument("--output", default="reports/generated-sitemap.xml")
    args = parser.parse_args()

    output, findings = write_sitemap(ROOT / args.source, ROOT / args.output)
    if findings:
        print("Sitemap generation findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print(f"Wrote {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
