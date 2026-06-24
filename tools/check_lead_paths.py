#!/usr/bin/env python3
"""Validate the primary phone and photo-assessment lead paths."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PHONE_LINK = 'href="tel:+79009267929"'
DIRECT_ASSESSMENT_LINK = 'href="/zayavka/">Оценить по фото</a>'
LOCAL_ASSESSMENT_LINKS = {
    'href="#request">Получить оценку по фото</a>',
    'href="#request">Оценка по фото</a>',
    'href="#request">Собрать текст для оценки</a>',
}

DIRECT_LEAD_PAGES = {
    "ceny/index.html",
    "kak-rabotaem/index.html",
    "kontakty/index.html",
    "o-mastere/index.html",
    "portfolio/index.html",
    "resheniya/index.html",
    "sovety/index.html",
    "uslugi/index.html",
    "voprosy-i-otvety/index.html",
}

EARLY_DIRECT_LEAD_PAGES = {
    "ceny/index.html",
    "kontakty/index.html",
    "o-mastere/index.html",
    "uslugi/index.html",
}

LOCAL_LEAD_PAGES = {
    "index.html",
    "zayavka/index.html",
}

REQUEST_PAGE_MARKERS = {
    'id="request-form"': "request form",
    'id="request-photos"': "photo readiness field",
    'id="request-video"': "video readiness field",
    'id="request-task"': "task field",
    'id="request-contact"': "contact field",
    'id="request-task" rows="6" required': "required task field",
    'id="request-contact" autocomplete="tel" inputmode="tel" required': "required contact field",
    '>Скопировать текст для оценки</button>': "copy action",
    "Данные не сохраняются на сайте.": "privacy explanation",
}

SCRIPT_MARKERS = {
    "navigator.clipboard.writeText(text)": "clipboard copy",
    "data-request-fallback": "clipboard fallback",
    "Фото:": "photo readiness in copied text",
    "Видео скрипа/подвижности:": "video readiness in copied text",
    "parket36:lead": "lead analytics event",
}


def read_page(rel: str, findings: list[str]) -> str:
    path = ROOT / rel
    if not path.exists():
        findings.append(f"{rel}: page is missing")
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def final_cta(text: str, rel: str, findings: list[str]) -> tuple[str, int]:
    marker = '<section class="final-cta">'
    start = text.rfind(marker)
    if start < 0:
        findings.append(f"{rel}: missing final conversion CTA")
        return "", -1

    end = text.find("</section>", start)
    if end < 0:
        findings.append(f"{rel}: final conversion CTA is not closed")
        return "", start

    main_end = text.find("</main>", end)
    if main_end < 0:
        findings.append(f"{rel}: missing closing main element")
    elif "<section" in text[end + len("</section>"):main_end]:
        findings.append(f"{rel}: final conversion CTA should be the last section in main")

    return text[start:end + len("</section>")], start


def check_phone(rel: str, block: str, findings: list[str]) -> None:
    if PHONE_LINK not in block:
        findings.append(f"{rel}: final CTA is missing the phone link")


def main() -> int:
    findings: list[str] = []

    for rel in sorted(DIRECT_LEAD_PAGES):
        text = read_page(rel, findings)
        if not text:
            continue
        block, start = final_cta(text, rel, findings)
        if not block:
            continue
        check_phone(rel, block, findings)
        if DIRECT_ASSESSMENT_LINK not in block:
            findings.append(f"{rel}: final CTA should link directly to photo assessment")
        if rel in EARLY_DIRECT_LEAD_PAGES and DIRECT_ASSESSMENT_LINK not in text[:start]:
            findings.append(f"{rel}: missing photo assessment CTA before the final section")

    for rel in sorted(LOCAL_LEAD_PAGES):
        text = read_page(rel, findings)
        if not text:
            continue
        block, start = final_cta(text, rel, findings)
        if not block:
            continue
        check_phone(rel, block, findings)
        if not any(marker in block for marker in LOCAL_ASSESSMENT_LINKS):
            findings.append(f"{rel}: final CTA should link to the local request form")
        if 'id="request"' not in text:
            findings.append(f"{rel}: local lead link points to a missing request section")
        if not any(marker in text[:start] for marker in LOCAL_ASSESSMENT_LINKS):
            findings.append(f"{rel}: missing local photo assessment CTA before the final section")

    request_text = read_page("zayavka/index.html", findings)
    for marker, label in REQUEST_PAGE_MARKERS.items():
        if marker not in request_text:
            findings.append(f"zayavka/index.html: missing {label}: {marker}")

    script_text = read_page("js/main.js", findings)
    for marker, label in SCRIPT_MARKERS.items():
        if marker not in script_text:
            findings.append(f"js/main.js: missing {label}: {marker}")

    if findings:
        print("Lead path findings:")
        for finding in sorted(set(findings)):
            print(f"  - {finding}")
        return 1

    print("Lead paths passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
