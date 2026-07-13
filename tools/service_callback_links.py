#!/usr/bin/env python3
"""Inject static callback paths into the two highest-intent service pages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

CALLBACK_URL = "/kontakty/#callback"
HERO_CALLBACK = (
    '<p><a class="text-link" href="/kontakty/#callback">'
    'Неудобно звонить — заказать обратный звонок →</a></p>'
)
PHONE_CALLBACK = (
    '<p><a class="text-link" href="/kontakty/#callback">'
    'Оставить номер для обратного звонка →</a></p>'
)


@dataclass(frozen=True)
class CallbackPage:
    relative_path: str
    hero_marker: str
    phone_marker: str


TARGET_PAGES = (
    CallbackPage(
        relative_path="uslugi/ciklevka-parketa/index.html",
        hero_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="tel:+79009267929">'
            'Позвонить Ивану</a><a class="btn btn--ghost" href="/zayavka/">'
            'Получить оценку по фото</a></div>'
        ),
        phone_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="tel:+79009267929">'
            'Позвонить по циклёвке</a><a class="btn btn--ghost" href="/pozvonit-ivanu/">'
            'Что сказать по телефону</a></div>'
        ),
    ),
    CallbackPage(
        relative_path="uslugi/restavraciya-parketa/index.html",
        hero_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="tel:+79009267929">'
            'Позвонить Ивану</a><a class="btn btn--ghost" href="/zayavka/">'
            'Получить оценку по фото</a></div>'
        ),
        phone_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="tel:+79009267929">'
            'Позвонить по реставрации</a><a class="btn btn--ghost" href="/pozvonit-ivanu/">'
            'Что сказать по телефону</a></div>'
        ),
    ),
)


def inject_service_callback_links(site_root: Path, errors: list[str]) -> None:
    """Add two static callback links to each configured built service page."""

    for page in TARGET_PAGES:
        path = site_root / page.relative_path
        if not path.is_file():
            errors.append(f"Callback target page is missing from public build: {page.relative_path}")
            continue

        text = path.read_text(encoding="utf-8")
        if text.count(CALLBACK_URL) == 2:
            continue
        if CALLBACK_URL in text:
            errors.append(
                f"{page.relative_path}: expected either zero or two callback links before injection"
            )
            continue

        missing_markers = [
            label
            for label, marker in (
                ("hero CTA", page.hero_marker),
                ("phone triage CTA", page.phone_marker),
            )
            if marker not in text
        ]
        if missing_markers:
            errors.append(
                f"{page.relative_path}: cannot inject callback links; missing "
                + ", ".join(missing_markers)
            )
            continue

        text = text.replace(page.hero_marker, page.hero_marker + HERO_CALLBACK, 1)
        text = text.replace(page.phone_marker, page.phone_marker + PHONE_CALLBACK, 1)
        path.write_text(text, encoding="utf-8")

        if text.count(CALLBACK_URL) != 2:
            errors.append(f"{page.relative_path}: callback link injection produced an invalid count")
