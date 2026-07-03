#!/usr/bin/env python3
"""Report advice pages from sitemap that are not linked from /sovety/."""

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


def main() -> int:
    sitemap_urls = sitemap_advice_urls()
    linked_urls = linked_advice_urls()
    missing = [url for url in sitemap_urls if url not in linked_urls]

    if not missing:
        print("All sitemap advice pages are linked from /sovety/.")
        return 0

    print("Advice pages from sitemap without a /sovety/ card:")
    for url in missing:
        print(f"  - {url}")
    print(f"Total: {len(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
