#!/usr/bin/env python3
"""Validate JSON-LD structured data across public Parket36 source pages."""

from __future__ import annotations

from datetime import date
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://parket36.ru"
PHONE = "+79009267929"
IGNORED_DIRS = {".git", ".github", "tools", "data", "node_modules", "_site"}
INTERNAL_PATHS = {Path("foto-dlya-sajta"), Path("portfolio") / "shablon-kejsa"}
FORBIDDEN_TYPES = {"AggregateRating", "Review", "Offer"}
FORBIDDEN_PROPERTIES = {"aggregateRating", "review", "reviews", "offers"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonical = ""
        self.robots = ""
        self.h1_chunks: list[str] = []
        self._in_h1 = False
        self._in_json_ld = False
        self._json_chunks: list[str] = []
        self.json_ld_blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key.lower(): (value or "") for key, value in attrs_list}
        lowered = tag.lower()
        if lowered == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonical = attrs.get("href", "").strip()
        elif lowered == "meta" and attrs.get("name", "").lower() == "robots":
            self.robots = attrs.get("content", "").strip()
        elif lowered == "h1" and not self.h1_chunks:
            self._in_h1 = True
        elif lowered == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._json_chunks = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered == "h1" and self._in_h1:
            self._in_h1 = False
        elif lowered == "script" and self._in_json_ld:
            self.json_ld_blocks.append("".join(self._json_chunks).strip())
            self._in_json_ld = False
            self._json_chunks = []

    def handle_data(self, data: str) -> None:
        if self._in_h1:
            self.h1_chunks.append(data)
        if self._in_json_ld:
            self._json_chunks.append(data)

    @property
    def h1(self) -> str:
        return " ".join("".join(self.h1_chunks).split())


def is_internal_path(relative: Path) -> bool:
    return any(relative == path or path in relative.parents for path in INTERNAL_PATHS)


def iter_public_html() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*.html"):
        relative = path.relative_to(ROOT)
        if any(part in IGNORED_DIRS for part in relative.parts):
            continue
        if is_internal_path(relative):
            continue
        result.append(path)
    return sorted(result)


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def normalize_type(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str)}
    return set()


def top_level_nodes(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    graph = payload.get("@graph")
    if isinstance(graph, list):
        return [item for item in graph if isinstance(item, dict)]
    return [payload]


def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from walk(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from walk(nested)


def parse_date(value: Any, label: str, relative: str, errors: list[str]) -> date | None:
    text = normalize_text(value)
    if not DATE_RE.fullmatch(text):
        errors.append(f"{relative}: {label} must use YYYY-MM-DD, got {text or '<empty>'}")
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        errors.append(f"{relative}: {label} is not a valid calendar date: {text}")
        return None


def validate_url(value: Any, label: str, relative: str, errors: list[str]) -> str:
    text = normalize_text(value)
    parsed = urlsplit(text)
    if not text or parsed.scheme != "https" or parsed.netloc != "parket36.ru":
        errors.append(f"{relative}: {label} must be an absolute https://parket36.ru URL")
    return text


def validate_faq(node: dict[str, Any], relative: str, errors: list[str]) -> None:
    entities = node.get("mainEntity")
    if not isinstance(entities, list) or not entities:
        errors.append(f"{relative}: FAQPage must contain a non-empty mainEntity list")
        return

    seen: set[str] = set()
    for index, question in enumerate(entities, start=1):
        if not isinstance(question, dict) or "Question" not in normalize_type(question.get("@type")):
            errors.append(f"{relative}: FAQ item {index} must use @type Question")
            continue
        name = normalize_text(question.get("name"))
        if not name:
            errors.append(f"{relative}: FAQ item {index} has an empty question")
        elif name in seen:
            errors.append(f"{relative}: FAQ question is duplicated: {name}")
        seen.add(name)

        answer = question.get("acceptedAnswer")
        if not isinstance(answer, dict) or "Answer" not in normalize_type(answer.get("@type")):
            errors.append(f"{relative}: FAQ item {index} must contain acceptedAnswer of type Answer")
            continue
        if not normalize_text(answer.get("text")):
            errors.append(f"{relative}: FAQ item {index} has an empty accepted answer")


def validate_article(
    node: dict[str, Any], canonical: str, h1: str, relative: str, errors: list[str]
) -> None:
    headline = normalize_text(node.get("headline"))
    if not headline:
        errors.append(f"{relative}: Article headline is empty")
    elif h1 and headline != h1:
        errors.append(f"{relative}: Article headline must match H1 ({headline!r} != {h1!r})")

    main_entity = validate_url(node.get("mainEntityOfPage"), "Article mainEntityOfPage", relative, errors)
    if main_entity and canonical and main_entity != canonical:
        errors.append(f"{relative}: Article mainEntityOfPage must match canonical")

    published = parse_date(node.get("datePublished"), "Article datePublished", relative, errors)
    modified = parse_date(node.get("dateModified"), "Article dateModified", relative, errors)
    if published and modified and modified < published:
        errors.append(f"{relative}: Article dateModified cannot be earlier than datePublished")

    for key in ("author", "publisher"):
        entity = node.get(key)
        if not isinstance(entity, dict) or not normalize_text(entity.get("name")):
            errors.append(f"{relative}: Article {key} must contain a non-empty name")


def validate_service(node: dict[str, Any], canonical: str, relative: str, errors: list[str]) -> None:
    url = validate_url(node.get("url"), "Service url", relative, errors)
    if url and canonical and url != canonical:
        errors.append(f"{relative}: Service url must match canonical")
    if not normalize_text(node.get("name")):
        errors.append(f"{relative}: Service name is empty")
    if not normalize_text(node.get("serviceType")):
        errors.append(f"{relative}: Service serviceType is empty")
    provider = node.get("provider")
    if not isinstance(provider, dict):
        errors.append(f"{relative}: Service provider is missing")
    elif normalize_text(provider.get("telephone")) != PHONE:
        errors.append(f"{relative}: Service provider telephone must be {PHONE}")

    area = node.get("areaServed")
    area_text = json.dumps(area, ensure_ascii=False) if area is not None else ""
    if "Воронеж" not in area_text:
        errors.append(f"{relative}: Service areaServed must include Воронеж")


def validate_payload(
    payload: Any, parser: PageParser, relative: str, errors: list[str], type_counts: dict[str, int]
) -> None:
    if not isinstance(payload, (dict, list)):
        errors.append(f"{relative}: JSON-LD root must be an object or array")
        return

    context = payload.get("@context") if isinstance(payload, dict) else None
    if context not in {"https://schema.org", "http://schema.org"}:
        errors.append(f"{relative}: JSON-LD @context must be https://schema.org")

    nodes = top_level_nodes(payload)
    if not nodes:
        errors.append(f"{relative}: JSON-LD contains no schema nodes")
        return

    for item in walk(payload):
        types = normalize_type(item.get("@type"))
        forbidden = types & FORBIDDEN_TYPES
        if forbidden:
            errors.append(f"{relative}: unsupported structured-data type: {', '.join(sorted(forbidden))}")
        for key in FORBIDDEN_PROPERTIES:
            if key in item:
                errors.append(f"{relative}: unsupported structured-data property: {key}")
        telephone = item.get("telephone")
        if telephone is not None and normalize_text(telephone) != PHONE:
            errors.append(f"{relative}: structured-data telephone must be {PHONE}")

    for node in nodes:
        types = normalize_type(node.get("@type"))
        if not types:
            errors.append(f"{relative}: top-level schema node is missing @type")
            continue
        for schema_type in types:
            type_counts[schema_type] = type_counts.get(schema_type, 0) + 1
        if "Article" in types:
            validate_article(node, parser.canonical, parser.h1, relative, errors)
        if "Service" in types:
            validate_service(node, parser.canonical, relative, errors)
        if "FAQPage" in types:
            validate_faq(node, relative, errors)
        if "WebPage" in types and "url" in node:
            url = validate_url(node.get("url"), "WebPage url", relative, errors)
            if url and parser.canonical and url != parser.canonical:
                errors.append(f"{relative}: WebPage url must match canonical")


def main() -> int:
    errors: list[str] = []
    page_count = 0
    indexable_count = 0
    schema_page_count = 0
    block_count = 0
    type_counts: dict[str, int] = {}

    for html_file in iter_public_html():
        page_count += 1
        relative = html_file.relative_to(ROOT).as_posix()
        parser = PageParser()
        parser.feed(html_file.read_text(encoding="utf-8"))
        indexable = "noindex" not in parser.robots.lower()
        if indexable:
            indexable_count += 1
            if not parser.canonical:
                errors.append(f"{relative}: indexable page is missing canonical")
            elif not parser.canonical.startswith(DOMAIN + "/") and parser.canonical != DOMAIN + "/":
                errors.append(f"{relative}: canonical must use {DOMAIN}")
            if not parser.json_ld_blocks:
                errors.append(f"{relative}: indexable page is missing JSON-LD")

        if parser.json_ld_blocks:
            schema_page_count += 1

        for block_index, block in enumerate(parser.json_ld_blocks, start=1):
            block_count += 1
            if not block:
                errors.append(f"{relative}: JSON-LD block {block_index} is empty")
                continue
            try:
                payload = json.loads(block)
            except json.JSONDecodeError as exc:
                errors.append(
                    f"{relative}: JSON-LD block {block_index} is invalid JSON "
                    f"(line {exc.lineno}, column {exc.colno}: {exc.msg})"
                )
                continue
            validate_payload(payload, parser, relative, errors, type_counts)

    if page_count == 0:
        errors.append("No public HTML pages were found")

    if errors:
        print("Structured data findings:")
        for error in errors:
            print(f"  - {error}")
        print(
            f"Checked {page_count} pages, {indexable_count} indexable pages and "
            f"{block_count} JSON-LD blocks"
        )
        return 1

    types = ", ".join(f"{key}={type_counts[key]}" for key in sorted(type_counts))
    print(
        f"Structured data check passed: {page_count} pages, {indexable_count} indexable, "
        f"{schema_page_count} with JSON-LD, {block_count} blocks; {types}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
