#!/usr/bin/env python3
"""Build a deterministic report for thin, similar and canonical-alias pages."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from dataclasses import dataclass
from html.parser import HTMLParser
from io import StringIO
from math import log, sqrt
from pathlib import Path
import re
import sys
from urllib.parse import urljoin

from build_content_inventory import (
    DOMAIN,
    ROOT,
    THIN_WORD_LIMIT,
    WORD_RE,
    clean_text,
    iter_public_html,
    normalize_url,
)

SIMILARITY_THRESHOLD = 0.72
CONTEXTUAL_SIMILARITY_THRESHOLD = 0.63
TITLE_OVERLAP_THRESHOLD = 0.30
MAX_REPORTED_PAIRS = 60

STOPWORDS = {
    "будет", "более", "быть", "вам", "вас", "ваш", "ваша", "ваше", "ваши",
    "ведь", "весь", "всего", "всегда", "вместе", "вопрос", "вопросы", "где",
    "даже", "дать", "для", "его", "если", "есть", "ещё", "здесь", "или", "как",
    "какая", "какие", "какой", "когда", "который", "которые", "лучше", "между",
    "может", "можно", "нужно", "него", "нет", "них", "она", "они", "оно",
    "перед", "после", "почему", "при", "про", "просто", "работ", "работы",
    "свой", "свои", "свою", "себя", "так", "также", "такой", "только", "того",
    "тоже", "уже", "чего", "чем", "через", "что", "чтобы", "этого", "этой",
    "этот", "этом", "паркет", "паркета", "паркету", "пол", "пола", "полу",
    "деревянный", "деревянного", "иван", "паркет36", "воронеж", "область",
    "оценка", "оценить", "фото", "позвонить", "заявка",
}


@dataclass
class Document:
    source_path: str
    source_url: str
    canonical: str
    robots: str
    refresh_target: str
    title: str
    h1: str
    word_count: int
    tokens: Counter[str]

    @property
    def indexable(self) -> bool:
        return "noindex" not in self.robots


@dataclass
class SimilarPair:
    score: float
    title_overlap: float
    first_url: str
    second_url: str
    first_title: str
    second_title: str
    shared_terms: str


class MainContentParser(HTMLParser):
    """Extract canonical, robots and visible text from the main page content."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.visible_parts: list[str] = []
        self.robots = ""
        self.canonical = ""
        self.refresh_target = ""
        self.in_title = False
        self.in_h1 = False
        self.in_main = False
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs = {key.lower(): (value or "") for key, value in attrs_list}

        if tag == "main":
            self.in_main = True
        elif tag in {"script", "style", "svg", "noscript"}:
            self.skip_depth += 1
        elif tag == "title":
            self.in_title = True
        elif tag == "h1":
            self.in_h1 = True
        elif tag == "meta":
            name = attrs.get("name", "").lower()
            http_equiv = attrs.get("http-equiv", "").lower()
            if name == "robots":
                self.robots = attrs.get("content", "").strip().lower()
            elif http_equiv == "refresh":
                match = re.search(r"url\s*=\s*([^;]+)$", attrs.get("content", ""), re.IGNORECASE)
                if match:
                    self.refresh_target = match.group(1).strip(" \t\"'")
        elif tag == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonical = attrs.get("href", "").strip()

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "main":
            self.in_main = False
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
        if self.in_main and self.skip_depth == 0:
            value = " ".join(data.split())
            if value:
                self.visible_parts.append(value)


def source_url(path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    if relative == "index.html":
        return DOMAIN + "/"
    if relative.endswith("/index.html"):
        return DOMAIN + "/" + relative.removesuffix("index.html")
    return DOMAIN + "/" + relative


def token_counter(text: str) -> Counter[str]:
    words = WORD_RE.findall(text.lower())
    return Counter(
        word
        for word in words
        if len(word) >= 4 and not word.isdigit() and word not in STOPWORDS
    )


def collect_documents() -> tuple[list[Document], list[str]]:
    documents: list[Document] = []
    findings: list[str] = []

    for path in iter_public_html():
        parser = MainContentParser()
        parser.feed(path.read_text(encoding="utf-8"))
        canonical = normalize_url(parser.canonical)
        current_source_url = source_url(path)
        if canonical is None:
            findings.append(f"{path.relative_to(ROOT).as_posix()}: canonical is missing")
            continue

        refresh_target = ""
        if parser.refresh_target:
            refresh_target = normalize_url(
                urljoin(current_source_url, parser.refresh_target),
                current_source_url,
            ) or ""

        visible = " ".join(parser.visible_parts)
        documents.append(
            Document(
                source_path=path.relative_to(ROOT).as_posix(),
                source_url=current_source_url,
                canonical=canonical,
                robots=parser.robots,
                refresh_target=refresh_target,
                title=clean_text(parser.title_parts),
                h1=clean_text(parser.h1_parts),
                word_count=len(WORD_RE.findall(visible)),
                tokens=token_counter(visible),
            )
        )

    return sorted(documents, key=lambda item: item.source_url), findings


def title_tokens(value: str) -> set[str]:
    return set(token_counter(value))


def jaccard(first: set[str], second: set[str]) -> float:
    union = first | second
    return len(first & second) / len(union) if union else 0.0


def tfidf_vectors(documents: list[Document]) -> list[dict[str, float]]:
    document_frequency: Counter[str] = Counter()
    for document in documents:
        document_frequency.update(document.tokens.keys())

    total = len(documents)
    vectors: list[dict[str, float]] = []
    for document in documents:
        vector: dict[str, float] = {}
        for term, count in document.tokens.items():
            inverse_document_frequency = log((1 + total) / (1 + document_frequency[term])) + 1
            vector[term] = (1 + log(count)) * inverse_document_frequency
        vectors.append(vector)
    return vectors


def cosine(first: dict[str, float], second: dict[str, float]) -> float:
    if not first or not second:
        return 0.0
    shared = first.keys() & second.keys()
    numerator = sum(first[term] * second[term] for term in shared)
    first_norm = sqrt(sum(value * value for value in first.values()))
    second_norm = sqrt(sum(value * value for value in second.values()))
    if first_norm == 0 or second_norm == 0:
        return 0.0
    return numerator / (first_norm * second_norm)


def similar_pairs(documents: list[Document]) -> list[SimilarPair]:
    indexable = [document for document in documents if document.indexable and len(document.tokens) >= 25]
    vectors = tfidf_vectors(indexable)
    pairs: list[SimilarPair] = []

    for first_index, first in enumerate(indexable):
        for second_index in range(first_index + 1, len(indexable)):
            second = indexable[second_index]
            score = cosine(vectors[first_index], vectors[second_index])
            overlap = jaccard(title_tokens(first.title), title_tokens(second.title))
            if not (
                score >= SIMILARITY_THRESHOLD
                or (score >= CONTEXTUAL_SIMILARITY_THRESHOLD and overlap >= TITLE_OVERLAP_THRESHOLD)
            ):
                continue

            shared = sorted(
                set(first.tokens) & set(second.tokens),
                key=lambda term: first.tokens[term] + second.tokens[term],
                reverse=True,
            )
            pairs.append(
                SimilarPair(
                    score=score,
                    title_overlap=overlap,
                    first_url=first.canonical,
                    second_url=second.canonical,
                    first_title=first.title,
                    second_title=second.title,
                    shared_terms=", ".join(shared[:8]),
                )
            )

    return sorted(pairs, key=lambda item: (-item.score, -item.title_overlap, item.first_url, item.second_url))


def canonical_groups(documents: list[Document]) -> tuple[list[tuple[str, list[Document]]], list[tuple[str, list[Document]]]]:
    grouped: defaultdict[str, list[Document]] = defaultdict(list)
    for document in documents:
        grouped[document.canonical].append(document)

    aliases: list[tuple[str, list[Document]]] = []
    conflicts: list[tuple[str, list[Document]]] = []

    for canonical, group in sorted(grouped.items()):
        if len(group) < 2:
            continue
        self_canonical = [document for document in group if document.source_url == canonical]
        redirected_aliases = [
            document
            for document in group
            if document.source_url != canonical
            and not document.indexable
            and document.refresh_target == canonical
        ]
        if len(self_canonical) == 1 and len(redirected_aliases) == len(group) - 1:
            aliases.append((canonical, group))
        else:
            conflicts.append((canonical, group))

    return aliases, conflicts


def csv_text(pairs: list[SimilarPair]) -> str:
    output = StringIO(newline="")
    fieldnames = [
        "score",
        "title_overlap",
        "first_url",
        "second_url",
        "first_title",
        "second_title",
        "shared_terms",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for pair in pairs:
        writer.writerow(
            {
                "score": f"{pair.score:.4f}",
                "title_overlap": f"{pair.title_overlap:.4f}",
                "first_url": pair.first_url,
                "second_url": pair.second_url,
                "first_title": pair.first_title,
                "second_title": pair.second_title,
                "shared_terms": pair.shared_terms,
            }
        )
    return output.getvalue()


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def markdown_text(documents: list[Document], pairs: list[SimilarPair]) -> str:
    indexable = [document for document in documents if document.indexable]
    thin = [document for document in indexable if document.word_count < THIN_WORD_LIMIT]
    aliases, conflicts = canonical_groups(documents)

    lines = [
        "# Отчёт по тонким, похожим и canonical-alias страницам",
        "",
        "Файл генерируется командой `python tools/build_content_similarity_report.py --output-dir reports/content-similarity`.",
        "Сходство является сигналом для редакторской проверки, а не автоматическим основанием объединять страницы.",
        "",
        "## Сводка",
        "",
        f"- публичных исходных страниц: {len(documents)};",
        f"- индексируемых страниц в сравнении: {len(indexable)};",
        f"- индексируемых страниц короче {THIN_WORD_LIMIT} слов: {len(thin)};",
        f"- пар с повышенным текстовым сходством: {len(pairs)};",
        f"- допустимых canonical-alias групп: {len(aliases)};",
        f"- конфликтных canonical-групп: {len(conflicts)}.",
        "",
        "## Тонкие индексируемые страницы",
        "",
    ]

    if thin:
        lines.extend(
            [
                "| URL | Слов | Входящий сигнал | Title |",
                "|---|---:|---|---|",
            ]
        )
        for document in sorted(thin, key=lambda item: (item.word_count, item.canonical)):
            lines.append(
                f"| {markdown_escape(document.canonical)} | {document.word_count} | проверить полноту ответа | {markdown_escape(document.title)} |"
            )
    else:
        lines.append("Индексируемых страниц короче установленного порога не найдено.")

    lines.extend(["", "## Похожие страницы", ""])
    if pairs:
        lines.extend(
            [
                "| Сходство | Заголовки | Первая страница | Вторая страница | Общие термины |",
                "|---:|---:|---|---|---|",
            ]
        )
        for pair in pairs[:MAX_REPORTED_PAIRS]:
            lines.append(
                "| {score:.3f} | {title:.3f} | {first} | {second} | {terms} |".format(
                    score=pair.score,
                    title=pair.title_overlap,
                    first=markdown_escape(pair.first_url),
                    second=markdown_escape(pair.second_url),
                    terms=markdown_escape(pair.shared_terms or "—"),
                )
            )
        if len(pairs) > MAX_REPORTED_PAIRS:
            lines.append("")
            lines.append(f"В таблице показаны первые {MAX_REPORTED_PAIRS} пар из {len(pairs)}; полный список хранится в CSV artifact.")
    else:
        lines.append("Пар выше установленных порогов сходства не найдено.")

    lines.extend(["", "## Допустимые canonical-alias", ""])
    if aliases:
        lines.extend(["| Canonical | Исходные адреса |", "|---|---|"])
        for canonical, group in aliases:
            sources = "<br>".join(markdown_escape(document.source_url) for document in group)
            lines.append(f"| {markdown_escape(canonical)} | {sources} |")
    else:
        lines.append("Canonical-alias группы не найдены.")

    lines.extend(["", "## Конфликтные canonical-группы", ""])
    if conflicts:
        lines.extend(["| Canonical | Исходные адреса |", "|---|---|"])
        for canonical, group in conflicts:
            sources = "<br>".join(markdown_escape(document.source_url) for document in group)
            lines.append(f"| {markdown_escape(canonical)} | {sources} |")
    else:
        lines.append("Конфликтных canonical-групп не найдено.")

    lines.extend(
        [
            "",
            "## Методика",
            "",
            "- сравнивается только видимый текст внутри `<main>`;",
            "- служебная шапка, футер и мобильная CTA не участвуют в сходстве;",
            "- используются TF-IDF и cosine similarity без внешних библиотек;",
            "- высокочастотные общие слова и основные брендовые термины исключены;",
            "- noindex-переходник считается допустимым alias только при meta refresh на canonical и наличии одной основной страницы.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(output_dir: Path) -> tuple[Path, Path, list[str]]:
    documents, findings = collect_documents()
    pairs = similar_pairs(documents)
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "content-similarity-report.md"
    csv_path = output_dir / "content-similarity-pairs.csv"
    markdown_path.write_text(markdown_text(documents, pairs), encoding="utf-8")
    csv_path.write_text(csv_text(pairs), encoding="utf-8")
    return markdown_path, csv_path, findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="reports/content-similarity")
    args = parser.parse_args()

    markdown_path, csv_path, findings = write_report(ROOT / args.output_dir)
    if findings:
        print("Content similarity findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print(f"Wrote {markdown_path.relative_to(ROOT)}")
    print(f"Wrote {csv_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
