#!/usr/bin/env python3
"""Block regressions in the main phone and photo-assessment lead paths."""

from __future__ import annotations

from pathlib import Path
import sys

from site_settings import load_config

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

CORE_STATIC_REQUIRED_MARKERS = {
    '<meta name="robots" content="index, follow">': "indexable robots directive",
    '<section class="final-cta">': "final conversion section",
    '<div class="mobile-cta">': "mobile CTA wrapper",
}

REQUEST_STATIC_PAGE_MARKERS = {
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
    'type="submit">Отправить заявку и скопировать текст</button>': "submit and copy action",
    'Заявка отправляется Ивану через защищённую форму.': "lead submission disclosure",
    '<section class="final-cta">': "final conversion section",
    'href="#request">Собрать текст для оценки</a>': "final local request CTA",
    'href="#request">Оценка по фото</a>': "mobile local request CTA",
}

STALE_LABELS = {
    "Составить заявку",
    "Подготовить заявку",
    "подготовьте заявку",
    "Отправка данных на сервер не выполняется",
    "Сайт не отправляет данные на сервер",
    "Без отправки данных на сайт",
    "Данные не сохраняются на сайте",
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
    config = load_config()
    phone_link = f'href="tel:{config["phone_e164"]}"'
    request_path = str(config["default_request_path"])
    direct_assessment_link = f'href="{request_path}">Оценить по фото</a>'
    mobile_assessment_link = f'href="{request_path}">Оценка по фото</a>'

    core_required_markers = {
        **CORE_STATIC_REQUIRED_MARKERS,
        phone_link: "direct phone link",
        direct_assessment_link: "direct photo-assessment CTA",
        mobile_assessment_link: "mobile photo-assessment CTA",
    }

    request_page_markers = {
        **REQUEST_STATIC_PAGE_MARKERS,
        phone_link: "direct phone link",
    }

    for rel in sorted(CORE_CONVERSION_PAGES):
        text = read_page(rel, findings)
        if not text:
            continue
        check_markers(rel, text, core_required_markers, findings)
        if text.count(f'href="{request_path}"') < 2:
            findings.append(f"{rel}: expected at least two links to {request_path}")
        for label in sorted(STALE_LABELS):
            if label in text:
                findings.append(f"{rel}: contains stale CTA label: {label}")

    request_rel = "zayavka/index.html"
    request_text = read_page(request_rel, findings)
    if request_text:
        check_markers(request_rel, request_text, request_page_markers, findings)
        if request_text.count('href="#request"') < 3:
            findings.append(f"{request_rel}: expected hero, final and mobile links to #request")
        for label in sorted(STALE_LABELS):
            if label in request_text:
                findings.append(f"{request_rel}: contains stale lead disclosure: {label}")

    if findings:
        print("Conversion path findings:")
        for finding in sorted(findings):
            print(f"  - {finding}")
        return 1

    print("Conversion paths passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
