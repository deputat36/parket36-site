#!/usr/bin/env python3
"""Fail CI when the committed content inventory summary is stale."""

from __future__ import annotations

import difflib
from pathlib import Path
import sys

from build_content_inventory import THIN_WORD_LIMIT, collect_pages

ROOT = Path(__file__).resolve().parents[1]
COMMITTED_MARKDOWN = ROOT / "docs" / "content-inventory.md"


def summary_markdown() -> tuple[str, list[str]]:
    records, findings = collect_pages()
    indexable = [record for record in records if "noindex" not in record.robots]
    thin = [record for record in indexable if record.word_count < THIN_WORD_LIMIT]
    orphan_candidates = [
        record
        for record in indexable
        if record.inbound_links == 0 and record.section != "home"
    ]
    duplicate_titles = [record for record in records if record.title_duplicate_count > 1]
    duplicate_h1s = [record for record in records if record.h1_duplicate_count > 1]
    with_phone = sum(1 for record in records if record.phone_links > 0)
    with_request = sum(
        1 for record in records if record.request_links > 0 or record.has_request_form
    )

    lines = [
        "# Content inventory Паркет36",
        "",
        "Сводка проверяется командой `python tools/check_content_inventory.py`.",
        "Полный реестр страниц создаётся командой `python tools/build_content_inventory.py --output-dir reports/content-inventory` и сохраняется в CI artifact `content-inventory` в форматах Markdown и CSV.",
        "",
        "## Сводка",
        "",
        f"- публичных страниц: {len(records)};",
        f"- индексируемых страниц: {len(indexable)};",
        f"- страниц короче {THIN_WORD_LIMIT} слов: {len(thin)};",
        f"- кандидатов без входящих внутренних ссылок: {len(orphan_candidates)};",
        f"- страниц с повторяющимся title: {len(duplicate_titles)};",
        f"- страниц с повторяющимся H1: {len(duplicate_h1s)};",
        f"- страниц со ссылкой на телефон: {with_phone};",
        f"- страниц с путём к заявке или формой: {with_request}.",
        "",
        "Показатели `короче 250 слов` и `без входящих ссылок` являются сигналами для проверки, а не автоматическим выводом о низком качестве страницы.",
        "",
        "## Сигналы к проверке",
        "",
    ]

    if thin:
        lines.append("Тонкие индексируемые страницы:")
        for record in sorted(thin, key=lambda item: (item.word_count, item.url)):
            lines.append(f"- `{record.url}` — {record.word_count} слов.")
    else:
        lines.append("Тонких индексируемых страниц не найдено.")

    lines.append("")
    if orphan_candidates:
        lines.append("Кандидаты без входящих внутренних ссылок:")
        for record in sorted(orphan_candidates, key=lambda item: item.url):
            lines.append(f"- `{record.url}`.")
    else:
        lines.append("Кандидатов без входящих внутренних ссылок не найдено.")

    lines.extend(["", "## Полный реестр", ""])
    lines.append(
        "Artifact `content-inventory` содержит `content-inventory.md` и `content-inventory.csv` с URL, исходным путём, title, H1, description, canonical, robots, word count, lastmod, входящими и исходящими ссылками и конверсионными элементами."
    )
    lines.append("")
    return "\n".join(lines), findings


def main() -> int:
    if not COMMITTED_MARKDOWN.is_file():
        print("Content inventory summary is missing: docs/content-inventory.md")
        return 1

    expected, findings = summary_markdown()
    if findings:
        print("Content inventory generation findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    actual = COMMITTED_MARKDOWN.read_text(encoding="utf-8")
    if actual != expected:
        print("docs/content-inventory.md is stale")
        print("Unified diff:")
        for line in difflib.unified_diff(
            actual.splitlines(),
            expected.splitlines(),
            fromfile="docs/content-inventory.md",
            tofile="generated/content-inventory-summary.md",
            lineterm="",
        ):
            print(line)
        return 1

    print("Content inventory check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
