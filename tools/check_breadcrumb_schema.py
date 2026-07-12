#!/usr/bin/env python3
"""Self-test build-time BreadcrumbList generation."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

from breadcrumb_schema import GENERATED_MARKER, BreadcrumbPageParser, inject_breadcrumb_schemas

DOMAIN = "https://parket36.ru"


def extract_generated_payload(text: str) -> dict[str, object]:
    parser = BreadcrumbPageParser()
    parser.feed(text)
    marker = f'<script type="application/ld+json" {GENERATED_MARKER}>'
    if marker not in text:
        raise ValueError("generated BreadcrumbList marker is missing")
    payload_text = text.split(marker, 1)[1].split("</script>", 1)[0]
    payload = json.loads(payload_text)
    if not isinstance(payload, dict):
        raise ValueError("generated BreadcrumbList must be an object")
    return payload


def main() -> int:
    findings: list[str] = []

    with tempfile.TemporaryDirectory() as temporary:
        site = Path(temporary)
        nested = site / "uslugi" / "ciklevka-parketa"
        nested.mkdir(parents=True)
        page = nested / "index.html"
        page.write_text(
            """<!doctype html><html><head>
<link rel="canonical" href="https://parket36.ru/uslugi/ciklevka-parketa/">
<meta name="robots" content="index, follow">
</head><body><main><div class="breadcrumbs">
<a href="/">Главная</a><span>›</span><a href="/uslugi/">Услуги</a><span>›</span><span>Циклёвка паркета</span>
</div></main></body></html>""",
            encoding="utf-8",
        )

        noindex = site / "404.html"
        noindex.write_text(
            """<!doctype html><html><head>
<link rel="canonical" href="https://parket36.ru/404.html">
<meta name="robots" content="noindex, follow">
</head><body><div class="breadcrumbs"><a href="/">Главная</a><span>›</span><span>Ошибка</span></div></body></html>""",
            encoding="utf-8",
        )

        errors: list[str] = []
        injected = inject_breadcrumb_schemas(site, DOMAIN, errors)
        if errors:
            findings.extend(errors)
        if injected != 1:
            findings.append(f"expected one indexable breadcrumb schema, got {injected}")

        try:
            payload = extract_generated_payload(page.read_text(encoding="utf-8"))
            if payload.get("@type") != "BreadcrumbList":
                findings.append("generated payload must use BreadcrumbList")
            items = payload.get("itemListElement")
            if not isinstance(items, list) or len(items) != 3:
                findings.append("generated payload must contain three visible breadcrumb items")
            else:
                expected = [
                    (1, "Главная", "https://parket36.ru/"),
                    (2, "Услуги", "https://parket36.ru/uslugi/"),
                    (3, "Циклёвка паркета", "https://parket36.ru/uslugi/ciklevka-parketa/"),
                ]
                actual = [
                    (item.get("position"), item.get("name"), item.get("item"))
                    for item in items
                    if isinstance(item, dict)
                ]
                if actual != expected:
                    findings.append(f"unexpected breadcrumb items: {actual}")
        except (ValueError, json.JSONDecodeError) as exc:
            findings.append(str(exc))

        if GENERATED_MARKER in noindex.read_text(encoding="utf-8"):
            findings.append("noindex page must not receive generated BreadcrumbList")

    if findings:
        print("Breadcrumb schema findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Breadcrumb schema self-test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
