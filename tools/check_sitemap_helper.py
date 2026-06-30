#!/usr/bin/env python3
"""Validate the sitemap helper without changing the real sitemap."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = ROOT / "tools" / "add_sitemap_entry.py"
SAMPLE_SITEMAP = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
  <url><loc>https://parket36.ru/</loc><lastmod>2026-06-23</lastmod><changefreq>weekly</changefreq><priority>1.0</priority></url>
</urlset>"""


def load_helper():
    spec = importlib.util.spec_from_file_location("add_sitemap_entry", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load sitemap helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    findings: list[str] = []
    helper = load_helper()

    if helper.clean_path("sovety/test") != "/sovety/test/":
        findings.append("clean_path must add leading and trailing slashes")
    if helper.clean_path("https://parket36.ru/sovety/test/") != "/sovety/test/":
        findings.append("clean_path must accept full site URLs")

    try:
        helper.clean_path("   ")
        findings.append("clean_path must reject empty paths")
    except SystemExit:
        pass

    try:
        helper.valid_date("2026-13-30")
        findings.append("valid_date must reject invalid dates")
    except Exception:
        pass

    with tempfile.TemporaryDirectory() as tmp:
        sitemap = Path(tmp) / "sitemap.xml"
        sitemap.write_text(SAMPLE_SITEMAP, encoding="utf-8")
        old_argv = sys.argv[:]
        try:
            sys.argv = ["add_sitemap_entry.py", "/sovety/test/", "--lastmod", "2026-06-30", "--file", str(sitemap)]
            helper.main()
            sys.argv = ["add_sitemap_entry.py", "/sovety/test/", "--lastmod", "2026-06-30", "--file", str(sitemap)]
            helper.main()
        finally:
            sys.argv = old_argv

        text = sitemap.read_text(encoding="utf-8")
        loc = "<loc>https://parket36.ru/sovety/test/</loc>"
        if text.count(loc) != 1:
            findings.append("helper must add a URL once and avoid duplicates")
        if "<lastmod>2026-06-30</lastmod>" not in text:
            findings.append("helper must write the requested lastmod date")

    if findings:
        print("Sitemap helper findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Sitemap helper check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
