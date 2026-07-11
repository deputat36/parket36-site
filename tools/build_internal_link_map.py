#!/usr/bin/env python3
"""Build a deterministic internal-link map for indexable Parket36 pages."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
import sys
from urllib.parse import urlsplit

from build_content_inventory import DOMAIN, ROOT, iter_public_html, normalize_url, section_for_url

HOME_URL = f"{DOMAIN}/"
LOW_CONTEXTUAL_INBOUND = 1
REPORT_LIMIT = 30


@dataclass
class SourcePage:
    source_path: str
    url: str
    title: str
    robots: str
    all_links: list[str]
    main_links: list[tuple[str, str]]


@dataclass
class NodeRecord:
    url: str
    source_path: str
    section: str
    title: str
    all_inbound: int
    contextual_inbound: int
    all_outbound: int
    contextual_outbound: int
    all_depth: int | None
    contextual_depth: int | None
    shared_only_inbound: bool


@dataclass
class EdgeRecord:
    source: str
    target: str
    occurrences: int
    anchor_texts: str


class LinkMapParser(HTMLParser):
    """Collect canonical metadata plus all-body and main-only links."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.robots = ""
        self.canonical = ""
        self.all_links: list[str] = []
        self.main_links: list[tuple[str, str]] = []
        self.in_title = False
        self.main_depth = 0
        self.anchor_href: str | None = None
        self.anchor_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs = {key.lower(): (value or "") for key, value in attrs_list}

        if tag == "title":
            self.in_title = True
        elif tag == "main":
            self.main_depth += 1
        elif tag == "meta" and attrs.get("name", "").lower() == "robots":
            self.robots = attrs.get("content", "").strip().lower()
        elif tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonical = attrs.get("href", "").strip()

        if tag == "a":
            href = attrs.get("href", "").strip()
            if href:
                self.all_links.append(href)
                if self.main_depth > 0:
                    self.anchor_href = href
                    self.anchor_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif tag == "a" and self.anchor_href is not None:
            text = " ".join(" ".join(self.anchor_parts).split())
            self.main_links.append((self.anchor_href, text))
            self.anchor_href = None
            self.anchor_parts = []
        elif tag == "main" and self.main_depth:
            self.main_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.anchor_href is not None:
            value = " ".join(data.split())
            if value:
                self.anchor_parts.append(value)


def clean_text(parts: list[str]) -> str:
    return " ".join(" ".join(parts).split())


def collect_source_pages() -> tuple[list[SourcePage], list[str]]:
    findings: list[str] = []
    by_url: dict[str, SourcePage] = {}

    for path in iter_public_html():
        parser = LinkMapParser()
        parser.feed(path.read_text(encoding="utf-8"))
        parser.close()
        relative = path.relative_to(ROOT).as_posix()
        canonical = normalize_url(parser.canonical)
        if canonical is None:
            findings.append(f"{relative}: canonical is missing or outside {DOMAIN}")
            continue
        if "noindex" in parser.robots:
            continue

        page = SourcePage(
            source_path=relative,
            url=canonical,
            title=clean_text(parser.title_parts),
            robots=parser.robots,
            all_links=parser.all_links,
            main_links=parser.main_links,
        )
        if canonical in by_url:
            findings.append(
                f"Indexable canonical conflict: {canonical} is used by "
                f"{by_url[canonical].source_path} and {relative}"
            )
            continue
        by_url[canonical] = page

    return sorted(by_url.values(), key=lambda item: item.url), findings


def shortest_depths(start: str, adjacency: dict[str, set[str]]) -> dict[str, int]:
    if start not in adjacency:
        return {}
    depths = {start: 0}
    queue: deque[str] = deque([start])
    while queue:
        source = queue.popleft()
        for target in sorted(adjacency.get(source, set())):
            if target in depths:
                continue
            depths[target] = depths[source] + 1
            queue.append(target)
    return depths


def build_map() -> tuple[list[NodeRecord], list[EdgeRecord], dict[tuple[str, str], int], list[str]]:
    pages, findings = collect_source_pages()
    page_by_url = {page.url: page for page in pages}
    urls = set(page_by_url)

    all_adjacency: dict[str, set[str]] = {url: set() for url in urls}
    contextual_adjacency: dict[str, set[str]] = {url: set() for url in urls}
    all_inbound_sources: dict[str, set[str]] = {url: set() for url in urls}
    contextual_inbound_sources: dict[str, set[str]] = {url: set() for url in urls}
    contextual_occurrences: Counter[tuple[str, str]] = Counter()
    contextual_anchors: dict[tuple[str, str], set[str]] = defaultdict(set)

    for page in pages:
        for href in page.all_links:
            target = normalize_url(href, page.url)
            if target and target in urls and target != page.url:
                all_adjacency[page.url].add(target)
                all_inbound_sources[target].add(page.url)

        for href, anchor_text in page.main_links:
            target = normalize_url(href, page.url)
            if not target or target not in urls or target == page.url:
                continue
            contextual_adjacency[page.url].add(target)
            contextual_inbound_sources[target].add(page.url)
            contextual_occurrences[(page.url, target)] += 1
            if anchor_text:
                contextual_anchors[(page.url, target)].add(anchor_text)

    all_depths = shortest_depths(HOME_URL, all_adjacency)
    contextual_depths = shortest_depths(HOME_URL, contextual_adjacency)

    nodes: list[NodeRecord] = []
    for page in pages:
        all_inbound = len(all_inbound_sources[page.url])
        contextual_inbound = len(contextual_inbound_sources[page.url])
        nodes.append(
            NodeRecord(
                url=page.url,
                source_path=page.source_path,
                section=section_for_url(page.url),
                title=page.title,
                all_inbound=all_inbound,
                contextual_inbound=contextual_inbound,
                all_outbound=len(all_adjacency[page.url]),
                contextual_outbound=len(contextual_adjacency[page.url]),
                all_depth=all_depths.get(page.url),
                contextual_depth=contextual_depths.get(page.url),
                shared_only_inbound=all_inbound > 0 and contextual_inbound == 0,
            )
        )

    edges = [
        EdgeRecord(
            source=source,
            target=target,
            occurrences=contextual_occurrences[(source, target)],
            anchor_texts=" | ".join(sorted(contextual_anchors[(source, target)])),
        )
        for source, target in sorted(contextual_occurrences)
    ]

    section_matrix: dict[tuple[str, str], int] = Counter()
    for edge in edges:
        source_section = section_for_url(edge.source)
        target_section = section_for_url(edge.target)
        section_matrix[(source_section, target_section)] += 1

    return nodes, edges, dict(section_matrix), findings


def csv_text(records: list[NodeRecord] | list[EdgeRecord]) -> str:
    output = StringIO(newline="")
    fieldnames = list(asdict(records[0]).keys()) if records else []
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    if fieldnames:
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))
    return output.getvalue()


def depth_text(value: int | None) -> str:
    return str(value) if value is not None else "—"


def markdown_text(
    nodes: list[NodeRecord],
    edges: list[EdgeRecord],
    section_matrix: dict[tuple[str, str], int],
) -> str:
    non_home = [node for node in nodes if node.url != HOME_URL]
    no_contextual = [node for node in non_home if node.contextual_inbound == 0]
    low_contextual = [node for node in non_home if node.contextual_inbound <= LOW_CONTEXTUAL_INBOUND]
    contextual_unreachable = [node for node in non_home if node.contextual_depth is None]
    all_unreachable = [node for node in non_home if node.all_depth is None]
    shared_only = [node for node in non_home if node.shared_only_inbound]

    weak = sorted(
        low_contextual,
        key=lambda item: (
            item.contextual_inbound,
            item.all_inbound,
            item.contextual_depth is None,
            item.url,
        ),
    )[:REPORT_LIMIT]
    authorities = sorted(
        non_home,
        key=lambda item: (-item.contextual_inbound, -item.all_inbound, item.url),
    )[:15]
    hubs = sorted(
        nodes,
        key=lambda item: (-item.contextual_outbound, -item.all_outbound, item.url),
    )[:15]

    lines = [
        "# Карта внутренних ссылок Паркет36",
        "",
        "Файл генерируется командой `python tools/build_internal_link_map.py --output-dir reports/internal-links`.",
        "Контекстными считаются ссылки внутри `<main>`; ссылки общей шапки, футера и мобильной панели учитываются только в полном графе.",
        "",
        "## Сводка",
        "",
        f"- индексируемых страниц: {len(nodes)};",
        f"- уникальных внутренних связей во всём HTML: {sum(node.all_outbound for node in nodes)};",
        f"- уникальных контекстных связей внутри `<main>`: {len(edges)};",
        f"- страниц без контекстных входящих ссылок: {len(no_contextual)};",
        f"- страниц с 0–{LOW_CONTEXTUAL_INBOUND} контекстной входящей ссылкой: {len(low_contextual)};",
        f"- страниц, зависящих только от общих элементов: {len(shared_only)};",
        f"- страниц, недостижимых от главной по контекстным ссылкам: {len(contextual_unreachable)};",
        f"- страниц, недостижимых от главной по любым внутренним ссылкам: {len(all_unreachable)}.",
        "",
        "Порог низкой связности является сигналом для редакторской проверки, а не автоматическим требованием добавить ссылку.",
        "",
        "## Страницы с низкой контекстной связностью",
        "",
    ]

    if weak:
        lines.extend(
            [
                "| URL | Раздел | Контекстные входящие | Все входящие | Контекстная глубина | Только общие элементы |",
                "|---|---|---:|---:|---:|:---:|",
            ]
        )
        for node in weak:
            lines.append(
                f"| {node.url} | {node.section} | {node.contextual_inbound} | {node.all_inbound} | "
                f"{depth_text(node.contextual_depth)} | {'да' if node.shared_only_inbound else 'нет'} |"
            )
    else:
        lines.append("Страниц с низкой контекстной связностью не найдено.")

    lines.extend(
        [
            "",
            "## Главные получатели контекстных ссылок",
            "",
            "| URL | Контекстные входящие | Все входящие |",
            "|---|---:|---:|",
        ]
    )
    for node in authorities:
        lines.append(f"| {node.url} | {node.contextual_inbound} | {node.all_inbound} |")

    lines.extend(
        [
            "",
            "## Главные контекстные хабы",
            "",
            "| URL | Контекстные исходящие | Все исходящие |",
            "|---|---:|---:|",
        ]
    )
    for node in hubs:
        lines.append(f"| {node.url} | {node.contextual_outbound} | {node.all_outbound} |")

    sections = sorted({node.section for node in nodes})
    lines.extend(["", "## Связи между разделами", ""])
    lines.append("| Из раздела \\ В раздел | " + " | ".join(sections) + " |")
    lines.append("|---|" + "---:|" * len(sections))
    for source_section in sections:
        values = [str(section_matrix.get((source_section, target_section), 0)) for target_section in sections]
        lines.append(f"| {source_section} | " + " | ".join(values) + " |")

    lines.extend(
        [
            "",
            "## Полные данные",
            "",
            "Artifact `internal-link-map` содержит:",
            "",
            "- `internal-link-nodes.csv` — показатели каждой индексируемой страницы;",
            "- `internal-link-edges.csv` — контекстные связи и тексты анкоров;",
            "- `internal-link-map.md` — этот отчёт с полной актуальной сводкой.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(output_dir: Path) -> tuple[Path, Path, Path, list[str]]:
    nodes, edges, section_matrix, findings = build_map()
    if not nodes:
        findings.append("No indexable pages were collected")

    output_dir.mkdir(parents=True, exist_ok=True)
    nodes_path = output_dir / "internal-link-nodes.csv"
    edges_path = output_dir / "internal-link-edges.csv"
    markdown_path = output_dir / "internal-link-map.md"
    nodes_path.write_text(csv_text(nodes), encoding="utf-8")
    edges_path.write_text(csv_text(edges), encoding="utf-8")
    markdown_path.write_text(markdown_text(nodes, edges, section_matrix), encoding="utf-8")
    return nodes_path, edges_path, markdown_path, findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="reports/internal-links")
    args = parser.parse_args()

    nodes_path, edges_path, markdown_path, findings = write_report(ROOT / args.output_dir)
    if findings:
        print("Internal link map findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print(f"Wrote {nodes_path.relative_to(ROOT)}")
    print(f"Wrote {edges_path.relative_to(ROOT)}")
    print(f"Wrote {markdown_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
