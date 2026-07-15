#!/usr/bin/env python3
"""Block regressions in the main phone, callback and photo-assessment lead paths."""

from __future__ import annotations

from pathlib import Path
import sys

from site_settings import load_config

ROOT = Path(__file__).resolve().parents[1]
FORM_POLICY_NOTICE = 'Нажимая кнопку, вы соглашаетесь с <a href="/politika/">обработкой контактных данных</a>.'
CONTACT_MOBILE_CALLBACK_LINK = 'href="#callback">Обратный звонок</a>'
SHARED_HEADER_FRAGMENT = "data/shared-shell/header.htmlfrag"
SHARED_MOBILE_FRAGMENT = "data/shared-shell/mobile-cta.htmlfrag"
SHARED_FINAL_FRAGMENT = "data/shared-shell/final-cta.htmlfrag"
SHARED_FOOTER_FRAGMENT = "data/shared-shell/footer.htmlfrag"
CALL_CSS = "css/cta-polish.css"
PHONE_HELPER_PAGE = "pozvonit-ivanu/index.html"

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

PHONE_TRIAGE_PAGES = {
    "uslugi/parket-i-poly/index.html",
    "uslugi/ciklevka-parketa/index.html",
    "uslugi/restavraciya-parketa/index.html",
    "uslugi/shlifovka-doshchatogo-pola/index.html",
    "uslugi/pokrytie-lakom-i-maslom/index.html",
}

CORE_STATIC_REQUIRED_MARKERS = {
    '<meta name="robots" content="index, follow">': "indexable robots directive",
    '<section class="final-cta">': "final conversion section",
    '<div class="mobile-cta">': "mobile CTA wrapper",
}

PHONE_TRIAGE_REQUIRED_MARKERS = {
    "Когда лучше сразу звонить": "phone triage section heading",
    'href="/pozvonit-ivanu/"': "phone script helper link",
    "Что сказать по телефону": "phone script CTA label",
}

PRICE_PAGE_PHONE_MARKERS = {
    "Ориентир по телефону": "price page phone estimate section",
    'href="/pozvonit-ivanu/"': "phone script helper link",
    "Что сказать по телефону": "phone script CTA label",
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
    FORM_POLICY_NOTICE: "privacy policy consent notice",
    '<section class="final-cta">': "final conversion section",
    'href="#request">Собрать текст для оценки</a>': "final local request CTA",
    'href="#request">Оценка по фото</a>': "mobile local request CTA",
}

SHARED_HEADER_MARKERS = {
    'class="phone phone--header"': "prominent header phone style hook",
    'data-call-source="header"': "header call source marker",
    '<span class="phone__label">Позвонить Ивану</span>': "header call action label",
    '<span class="phone__number">': "header phone number wrapper",
}

SHARED_MOBILE_MARKERS = {
    'class="mobile-cta" aria-label="Быстрые действия"': "accessible sticky action label",
    'data-call-source="mobile-sticky"': "sticky call source marker",
    '>Позвонить Ивану</a>': "explicit sticky phone action",
    'href="#request">Оценка по фото</a>': "canonical sticky assessment action",
}

SHARED_FINAL_MARKERS = {
    "Не знаете, с чего начать с полом? Позвоните Ивану": "call-first final heading",
    'data-call-source="final-cta"': "final CTA call source marker",
    "Не нужно выбирать услугу заранее.": "low-friction call explanation",
}

SHARED_FOOTER_MARKERS = {
    "Не знаете название услуги — опишите состояние пола своими словами.": "footer call reassurance",
    'data-call-source="footer"': "footer call source marker",
}

RESPONSIVE_CALL_CSS_MARKERS = {
    ".phone--header {": "prominent desktop phone component",
    ".phone__label {": "header phone action label style",
    "@media (max-width: 1000px) {": "tablet call breakpoint",
    "padding-bottom: calc(86px + env(safe-area-inset-bottom));": "sticky CTA body clearance",
    "bottom: calc(10px + env(safe-area-inset-bottom));": "safe-area-aware sticky position",
    "width: min(620px, calc(100% - 24px));": "tablet sticky CTA width",
    ".mobile-cta a {": "sticky CTA action style",
}

PHONE_HELPER_MARKERS = {
    '<meta name="robots" content="noindex, follow">': "intentional helper noindex directive",
    "Что сказать Ивану по телефону про паркет": "phone helper heading",
    "Самый простой первый шаг — короткий звонок": "phone helper final CTA",
    'class="mobile-cta" aria-label="Быстрые действия"': "accessible phone helper sticky CTA",
}

STALE_LABELS = {
    "Составить заявку",
    "Подготовить заявку",
    "подготовьте заявку",
    "Отправка данных на сервер не выполняется",
    "Сайт не отправляет данные на сервер",
    "Без отправки данных на сайт",
    "Данные не сохраняются на сайте",
    "Данные никуда не отправляются",
}


def read_text(rel: str, findings: list[str]) -> str:
    path = ROOT / rel
    if not path.exists():
        findings.append(f"{rel}: file is missing")
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

    shared_checks = (
        (SHARED_HEADER_FRAGMENT, SHARED_HEADER_MARKERS),
        (SHARED_MOBILE_FRAGMENT, SHARED_MOBILE_MARKERS),
        (SHARED_FINAL_FRAGMENT, SHARED_FINAL_MARKERS),
        (SHARED_FOOTER_FRAGMENT, SHARED_FOOTER_MARKERS),
        (CALL_CSS, RESPONSIVE_CALL_CSS_MARKERS),
    )
    for rel, markers in shared_checks:
        text = read_text(rel, findings)
        if not text:
            continue
        check_markers(rel, text, markers, findings)
        if rel != CALL_CSS and phone_link not in text:
            findings.append(f"{rel}: missing configured phone link: {phone_link}")

    for rel in sorted(CORE_CONVERSION_PAGES):
        text = read_text(rel, findings)
        if not text:
            continue
        page_markers = dict(core_required_markers)
        if rel == "kontakty/index.html":
            page_markers.pop(mobile_assessment_link, None)
            page_markers[CONTACT_MOBILE_CALLBACK_LINK] = "mobile callback CTA"
        check_markers(rel, text, page_markers, findings)
        if rel in PHONE_TRIAGE_PAGES:
            check_markers(rel, text, PHONE_TRIAGE_REQUIRED_MARKERS, findings)
        if rel == "ceny/index.html":
            check_markers(rel, text, PRICE_PAGE_PHONE_MARKERS, findings)
        if text.count(f'href="{request_path}"') < 2:
            findings.append(f"{rel}: expected at least two links to {request_path}")
        for label in sorted(STALE_LABELS):
            if label in text:
                findings.append(f"{rel}: contains stale CTA label: {label}")

    request_rel = "zayavka/index.html"
    request_text = read_text(request_rel, findings)
    if request_text:
        check_markers(request_rel, request_text, request_page_markers, findings)
        if request_text.count('href="#request"') < 3:
            findings.append(f"{request_rel}: expected hero, final and mobile links to #request")
        for label in sorted(STALE_LABELS):
            if label in request_text:
                findings.append(f"{request_rel}: contains stale lead disclosure: {label}")

    helper_text = read_text(PHONE_HELPER_PAGE, findings)
    if helper_text:
        check_markers(PHONE_HELPER_PAGE, helper_text, PHONE_HELPER_MARKERS, findings)
        if helper_text.count(phone_link) < 5:
            findings.append(f"{PHONE_HELPER_PAGE}: expected at least five direct phone links")

    if findings:
        print("Conversion path findings:")
        for finding in sorted(findings):
            print(f"  - {finding}")
        return 1

    print("Conversion paths passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
