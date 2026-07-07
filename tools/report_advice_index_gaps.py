#!/usr/bin/env python3
"""Report mismatches between advice sitemap URLs and /sovety/ cards."""

from __future__ import annotations

from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "https://parket36.ru"
SITEMAP_PATH = ROOT / "sitemap.xml"
ADVICE_INDEX_PATH = ROOT / "sovety" / "index.html"


def sitemap_advice_urls() -> list[str]:
    tree = ET.parse(SITEMAP_PATH)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls: list[str] = []
    for loc in tree.findall(".//sm:loc", ns):
        value = (loc.text or "").strip()
        if value.startswith(f"{DOMAIN}/sovety/") and value != f"{DOMAIN}/sovety/":
            urls.append(value.removeprefix(DOMAIN))
    return sorted(urls)


def linked_advice_urls() -> set[str]:
    html = ADVICE_INDEX_PATH.read_text(encoding="utf-8", errors="ignore")
    return set(re.findall(r'href="(/sovety/[^"]+/)"', html))


def print_list(title: str, urls: list[str]) -> None:
    print(title)
    for url in urls:
        print(f"  - {url}")
    print(f"Total: {len(urls)}")


def main() -> int:
    sitemap_urls = sitemap_advice_urls()
    linked_urls = sorted(linked_advice_urls())
    sitemap_url_set = set(sitemap_urls)
    linked_url_set = set(linked_urls)

    missing_cards = [url for url in sitemap_urls if url not in linked_url_set]
    missing_sitemap_entries = [url for url in linked_urls if url not in sitemap_url_set]

    print(f"Sitemap advice pages: {len(sitemap_urls)}")
    print(f"/sovety/ advice cards: {len(linked_urls)}")

    if not missing_cards and not missing_sitemap_entries:
        print("Advice sitemap and /sovety/ cards are in sync.")
        return 0

    if missing_cards:
        print_list("Advice pages from sitemap without a /sovety/ card:", missing_cards)

    if missing_sitemap_entries:
        print_list("Advice cards that are missing from sitemap:", missing_sitemap_entries)

    return 0


if __name__ == "__main__":
    sys.exit(main())
