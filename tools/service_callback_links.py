#!/usr/bin/env python3
"""Inject static callback paths into the homepage and high-intent service and problem pages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from home_callback_links import inject_home_callback_links

CALLBACK_URL = "/kontakty/#callback"
HERO_CALLBACK = (
    '<p><a class="text-link" href="/kontakty/#callback">'
    'Неудобно звонить — заказать обратный звонок →</a></p>'
)
SECONDARY_CALLBACK = (
    '<p><a class="text-link" href="/kontakty/#callback">'
    'Оставить номер для обратного звонка →</a></p>'
)


@dataclass(frozen=True)
class CallbackPage:
    relative_path: str
    hero_marker: str
    secondary_marker: str


TARGET_PAGES = (
    CallbackPage(
        relative_path="uslugi/index.html",
        hero_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="tel:+79009267929">'
            'Позвонить Ивану</a><a class="btn btn--ghost" href="/zayavka/">'
            'Оценить по фото</a></div>'
        ),
        secondary_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="/zayavka/">'
            'Получить предварительный ориентир</a><a class="btn btn--ghost" href="tel:+79009267929">'
            'Обсудить задачу по телефону</a></div>'
        ),
    ),
    CallbackPage(
        relative_path="uslugi/parket-i-poly/index.html",
        hero_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="tel:+79009267929">'
            'Позвонить Ивану</a><a class="btn btn--ghost" href="/zayavka/">'
            'Получить оценку по фото</a></div>'
        ),
        secondary_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="tel:+79009267929">'
            'Позвонить и выбрать решение</a><a class="btn btn--ghost" href="/pozvonit-ivanu/">'
            'Что сказать по телефону</a></div>'
        ),
    ),
    CallbackPage(
        relative_path="uslugi/ciklevka-parketa/index.html",
        hero_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="tel:+79009267929">'
            'Позвонить Ивану</a><a class="btn btn--ghost" href="/zayavka/">'
            'Получить оценку по фото</a></div>'
        ),
        secondary_marker=(
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
        secondary_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="tel:+79009267929">'
            'Позвонить по реставрации</a><a class="btn btn--ghost" href="/pozvonit-ivanu/">'
            'Что сказать по телефону</a></div>'
        ),
    ),
    CallbackPage(
        relative_path="sovety/parket-posle-vody/index.html",
        hero_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="tel:+79009267929">'
            'Обсудить паркет после воды</a><a class="btn btn--ghost" href="/zayavka/">'
            'Оценить по фото</a></div>'
        ),
        secondary_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="/zayavka/">'
            'Оценить по фото</a><a class="btn btn--ghost" href="/uslugi/restavraciya-parketa/">'
            'Реставрация паркета</a></div>'
        ),
    ),
    CallbackPage(
        relative_path="sovety/pochemu-skripit-parket/index.html",
        hero_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="tel:+79009267929">'
            'Обсудить скрип пола</a><a class="btn btn--ghost" href="/zayavka/">'
            'Оценить по фото</a></div>'
        ),
        secondary_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="/zayavka/">'
            'Оценить по фото</a><a class="btn btn--ghost" href="/uslugi/restavraciya-parketa/">'
            'Реставрация паркета</a></div>'
        ),
    ),
    CallbackPage(
        relative_path="sovety/shcheli-v-parkete/index.html",
        hero_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="tel:+79009267929">'
            'Обсудить щели</a><a class="btn btn--ghost" href="/zayavka/">'
            'Оценить по фото</a></div>'
        ),
        secondary_marker=(
            '<div class="hero__actions"><a class="btn btn--primary" href="/zayavka/">'
            'Оценить по фото</a><a class="btn btn--ghost" href="/uslugi/restavraciya-parketa/">'
            'Реставрация паркета</a></div>'
        ),
    ),
)


def inject_service_callback_links(site_root: Path, errors: list[str]) -> None:
    """Add static callback links to the homepage and each configured commercial page."""

    inject_home_callback_links(site_root, errors)

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
                ("secondary CTA", page.secondary_marker),
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
        text = text.replace(page.secondary_marker, page.secondary_marker + SECONDARY_CALLBACK, 1)
        path.write_text(text, encoding="utf-8")

        if text.count(CALLBACK_URL) != 2:
            errors.append(f"{page.relative_path}: callback link injection produced an invalid count")
