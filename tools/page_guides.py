"""Add native section navigation and concise service briefs to long public pages."""

from __future__ import annotations

from html import escape, unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re

SECTION = re.compile(r'<section\b(?P<attrs>[^>]*)>(?P<body>.*?)</section>', re.S)
HEADING = re.compile(r'<h2\b(?P<attrs>[^>]*)>(?P<body>.*?)</h2>', re.S)
ID = re.compile(r'\bid=["\']([^"\']+)["\']')
TRANSLITERATION = str.maketrans(dict(zip(
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n",
     "o", "p", "r", "s", "t", "u", "f", "h", "ts", "ch", "sh", "sch", "", "y", "", "e", "yu", "ya"],
)))


class HeadingText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_text(value: str) -> str:
    parser = HeadingText()
    parser.feed(value)
    return " ".join("".join(parser.parts).split())


def section_anchor(title: str, used: set[str]) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower().translate(TRANSLITERATION)).strip('-')
    base = "razdel-" + (slug[:80].rstrip('-') or "info")
    anchor = base
    suffix = 2
    while anchor in used:
        anchor = f"{base}-{suffix}"
        suffix += 1
    used.add(anchor)
    return anchor


def render_brief(entry: dict) -> str:
    points = "".join(
        f'<div><dt>{escape(point["label"])}</dt><dd>{escape(point["text"])}</dd></div>'
        for point in entry["points"]
    )
    return f'<dl class="service-brief" aria-label="Коротко о задаче">{points}</dl>'


def add_page_guide(text: str, entry: dict, context: str, errors: list[str]) -> str:
    if "data-page-guide" in text:
        return text
    main = re.search(r'<main\b[^>]*>(.*?)</main>', text, re.S)
    if main is None:
        errors.append(f"Page guide: main is missing on {context}")
        return text
    used = {unescape(value) for value in ID.findall(text)}
    links: list[tuple[str, str]] = []
    found_titles: set[str] = set()
    labels = entry.get("labels", {})

    def transform_section(section: re.Match) -> str:
        attrs, body = section["attrs"], section["body"]
        # Keep navigation focused on answers, rather than contact cards and related links.
        if any(value in attrs for value in ["subhero", "section--summary", "final-cta"]):
            return section[0]
        if 'lead-card--wide' in body:
            return section[0]

        def transform_heading(heading: re.Match) -> str:
            title = plain_text(heading["body"])
            if title in {"Полезные материалы", "Читайте также", "Другие полезные материалы"}:
                return heading[0]
            found_titles.add(title)
            existing = ID.search(heading["attrs"])
            anchor = unescape(existing[1]) if existing else section_anchor(title, used)
            updated_attrs = heading["attrs"]
            if not existing:
                updated_attrs += f' id="{escape(anchor, quote=True)}"'
            if 'tabindex=' not in updated_attrs:
                updated_attrs += ' tabindex="-1"'
            links.append((anchor, labels.get(title, title)))
            return f'<h2{updated_attrs}>{heading["body"]}</h2>'

        updated = HEADING.sub(transform_heading, body)
        return f'<section{attrs}>{updated}</section>'

    body = SECTION.sub(transform_section, main[1])
    missing_labels = set(labels) - found_titles
    if missing_labels:
        errors.append(f"Page guide: obsolete section labels on {context}: {sorted(missing_labels)}")
    if len(links) < 3:
        errors.append(f"Page guide: fewer than three content sections on {context}")
        return text
    hero = re.search(r'<section\b[^>]*class="subhero"[^>]*>.*?</section>', body, re.S)
    if hero is None:
        errors.append(f"Page guide: subhero is missing on {context}")
        return text
    brief = render_brief(entry) if entry.get("points") else ""
    if brief:
        # Replace the former photo checklist here; detailed preparation remains in the page body.
        body = re.sub(r'<section class="section section--summary">.*?</section>', '', body, count=1, flags=re.S)
    items = "".join(f'<li><a href="#{escape(anchor, quote=True)}">{escape(label)}</a></li>' for anchor, label in links)
    guide = (
        '<div class="page-guide" data-page-guide><div class="container">' + brief
        + '<nav aria-label="Разделы страницы"><details class="page-guide__contents">'
        '<summary>Перейти к нужному разделу</summary>'
        f'<ul>{items}</ul></details></nav></div></div>'
    )
    body = body[:hero.end()] + guide + body[hero.end():]
    return text[:main.start(1)] + body + text[main.end(1):]


def apply_page_guides(root: Path, destination: Path, errors: list[str]) -> None:
    config = json.loads((root / "data" / "page-guides.json").read_text(encoding="utf-8"))
    entries = config["pages"]
    targets = set(entries) | {path.relative_to(destination).as_posix() for path in (destination / "sovety").glob("*/index.html")}
    for relative in sorted(targets):
        target = destination / relative
        if not target.is_file():
            errors.append(f"Page guide: non-public target {relative}")
            continue
        original = target.read_text(encoding="utf-8")
        updated = add_page_guide(original, entries.get(relative, {}), relative, errors)
        target.write_text(updated, encoding="utf-8")
    print(f"Static page guides prepared {len(targets)} long pages; {len(entries)} concise briefs")
