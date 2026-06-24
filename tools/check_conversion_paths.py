#!/usr/bin/env python3
"""Block regressions in the main phone and photo-assessment lead paths."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

CORE_CONVERSION_PAGES = {
    "ceny/index.html",
    "kontakty/index.html",
    "o-mastere/index.html",
    "uslugi/index.html",
    "uslugi/parket-i-poly/index.html",
    "uslugi/ciklevka-parketa/index.html",
    "uslugi/restavraciya-parketa/index.html",
    "uslugi/shlifovka-doshchatogo-pola/index.html",
    "uslugi/pokrytie-lakom-i-maslom/index.html",
    "uslugi/ukladka-parketa/index.html",
    "uslugi/ukladka-laminata/index.html",
    "uslugi/terrasy-i-derevyannye-poly/index.html",
}

CORE_REQUIRED_MARKERS = {
    '<meta name="robots" content="index, follow">': "indexable robots directive",
    '<section class="final-cta">': "final conversion section",
    'href="tel:+79009267929"': "direct phone link",
    'href="/zayavka/">Оценить по фото</a>': "direct photo-assessment CTA",
    '<div class="mobile-cta">': "mobile CTA wrapper",
    'href="/zayavka/">Оценка по фото</a>': "mobile photo-assessment CTA",
}

REQUEST_PAGE_MARKERS = {
    '<meta name="robots" content="index, follow">': "indexable robots directive",
    'id="request"': "request section anchor",
    'id="request-form"': "request form",
    'id="request-service"': "service field",
    'id="request-location"': "location field",
    'id="request-area"': "area field",
    'id="request-photos"': "photo readiness field",
    'id="request-video"': "video readiness field",
    'id="request-task"': "task field",
    'id="request-callback"': "callback field",
    'id="request-contact"': "contact field",
    'type="submit">Скопировать текст для оценки</button>': "copy action",
    'Отправка данных на сервер не выполняется.': "local-processing disclosure",
    '<section class="final-cta">': "final conversion section",
    'href="#request">Собрать текст для оценки</a>': "final local request CTA",
    'href="#request">Оценка по фото</a>': "mobile local request CTA",
    'href="tel:+79009267929"': "direct phone link",
}

STALE_LABELS = {
    "Составить заявку",
    "Подготовить заявку",
    "подготовьте заявку",
}


def read_page(rel: str, findings: list[str]) -> str:
    path = ROOT / rel
    if not path.exists():
        findings.append(f"{rel}: page is missing")
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def check_markers(rel: str, text: str, markers: dict[str, str], findings: list[str]) -> None:
    for marker, label in markers.items():
        if marker not in text:
            findings.append(f"{rel}: missing {label}: {marker}")


def main() -> int:
    findings: list[str] = []

    for rel in sorted(CORE_CONVERSION_PAGES):
        text = read_page(rel, findings)
        if not text:
            continue
        check_markers(rel, text, CORE_REQUIRED_MARKERS, findings)
        if text.count('href="/zayavka/"') < 2:
            findings.append(f"{rel}: expected at least two links to /zayavka/")
        for label in sorted(STALE_LABELS):
            if label in text:
                findings.append(f"{rel}: contains stale CTA label: {label}")

    request_rel = "zayavka/index.html"
    request_text = read_page(request_rel, findings)
    if request_text:
        check_markers(request_rel, request_text, REQUEST_PAGE_MARKERS, findings)
        if request_text.count('href="#request"') < 3:
            findings.append(f"{request_rel}: expected hero, final and mobile links to #request")

    if findings:
        print("Conversion path findings:")
        for finding in sorted(findings):
            print(f"  - {finding}")
        return 1

    print("Conversion paths passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
