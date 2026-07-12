#!/usr/bin/env python3
"""Generate BreadcrumbList JSON-LD from visible breadcrumb navigation."""

from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit

GENERATED_MARKER = "data-generated-breadcrumbs"
SEPARATORS = {"›", ">", "→", "/", "»"}


class BreadcrumbPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonical = ""
        self.robots = ""
        self.has_generated_schema = False
        self._breadcrumb_depth = 0
        self._active_tag = ""
        self._active_href = ""
        self._active_chunks: list[str] = []
        self.items: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key.lower(): (value or "") for key, value in attrs_list}
        lowered = tag.lower()

        if lowered == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonical = attrs.get("href", "").strip()
        elif lowered == "meta" and attrs.get("name", "").lower() == "robots":
            self.robots = attrs.get("content", "").strip()
        elif lowered == "script" and GENERATED_MARKER in attrs:
            self.has_generated_schema = True

        if lowered == "div" and "breadcrumbs" in attrs.get("class", "").split():
            self._breadcrumb_depth = 1
            return
        if self._breadcrumb_depth and lowered == "div":
            self._breadcrumb_depth += 1

        if self._breadcrumb_depth and lowered in {"a", "span"}:
            self._active_tag = lowered
            self._active_href = attrs.get("href", "").strip() if lowered == "a" else ""
            self._active_chunks = []

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if self._breadcrumb_depth and lowered == self._active_tag:
            text = " ".join("".join(self._active_chunks).split())
            if text and text not in SEPARATORS:
                self.items.append((text, self._active_href))
            self._active_tag = ""
            self._active_href = ""
            self._active_chunks = []

        if self._breadcrumb_depth and lowered == "div":
            self._breadcrumb_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._breadcrumb_depth and self._active_tag:
            self._active_chunks.append(data)


def breadcrumb_payload(parser: BreadcrumbPageParser, domain: str) -> dict[str, object] | None:
    if "noindex" in parser.robots.lower() or parser.has_generated_schema:
        return None
    if not parser.canonical or len(parser.items) < 2:
        return None

    expected_host = urlsplit(domain).netloc
    elements: list[dict[str, object]] = []

    for position, (name, href) in enumerate(parser.items, start=1):
        item_url = parser.canonical if not href else urljoin(domain + "/", href)
        parsed = urlsplit(item_url)
        if parsed.scheme != "https" or parsed.netloc != expected_host:
            raise ValueError(f"breadcrumb item uses an unexpected URL: {item_url}")
        elements.append(
            {
                "@type": "ListItem",
                "position": position,
                "name": name,
                "item": item_url,
            }
        )

    if elements[-1]["item"] != parser.canonical:
        elements.append(
            {
                "@type": "ListItem",
                "position": len(elements) + 1,
                "name": parser.items[-1][0],
                "item": parser.canonical,
            }
        )

    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": elements,
    }


def inject_breadcrumb_schemas(site_dir: Path, domain: str, errors: list[str]) -> int:
    injected = 0
    expected_host = urlsplit(domain).netloc

    for html_file in sorted(site_dir.rglob("*.html")):
        relative = html_file.relative_to(site_dir).as_posix()
        text = html_file.read_text(encoding="utf-8")
        parser = BreadcrumbPageParser()
        parser.feed(text)

        try:
            payload = breadcrumb_payload(parser, domain)
        except ValueError as exc:
            errors.append(f"{relative}: {exc}")
            continue

        if payload is None:
            continue

        canonical_host = urlsplit(parser.canonical).netloc
        if canonical_host != expected_host:
            errors.append(f"{relative}: breadcrumb canonical belongs to unexpected host")
            continue
        if "</head>" not in text:
            errors.append(f"{relative}: cannot inject BreadcrumbList without </head>")
            continue

        json_ld = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        script = (
            f'<script type="application/ld+json" {GENERATED_MARKER}>'
            f"{json_ld}</script>"
        )
        text = text.replace("</head>", f"  {script}\n</head>", 1)
        html_file.write_text(text, encoding="utf-8")
        injected += 1

    return injected
