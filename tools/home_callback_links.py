#!/usr/bin/env python3
"""Inject static callback paths into the Parket36 homepage public build."""

from __future__ import annotations

from pathlib import Path

CALLBACK_URL = "/kontakty/#callback"
HERO_MARKER = (
    '<div class="hero__actions"><a class="btn btn--primary" href="tel:+79009267929">'
    'Позвонить Ивану</a><a class="btn btn--ghost" href="#request">'
    'Получить оценку по фото</a></div>'
)
PHONE_MARKER = (
    '<div class="hero__actions"><a class="btn btn--primary" href="tel:+79009267929">'
    'Позвонить Ивану</a><a class="btn btn--ghost" href="#request">'
    'Отправить фото после звонка</a></div>'
)
HERO_CALLBACK = (
    '<p><a class="text-link" href="/kontakty/#callback">'
    'Неудобно звонить — оставить номер для обратного звонка →</a></p>'
)
PHONE_CALLBACK = (
    '<p><a class="text-link" href="/kontakty/#callback">'
    'Удобнее, чтобы Иван позвонил сам — оставить номер →</a></p>'
)


def inject_home_callback_links(site_root: Path, errors: list[str]) -> None:
    """Add two static callback links to the built homepage."""

    path = site_root / "index.html"
    if not path.is_file():
        errors.append("Homepage is missing from public build")
        return

    text = path.read_text(encoding="utf-8")
    callback_count = text.count(CALLBACK_URL)
    if callback_count == 2:
        return
    if callback_count:
        errors.append(
            f"index.html: expected either zero or two homepage callback links before injection; found {callback_count}"
        )
        return

    missing_markers = [
        label
        for label, marker in (
            ("hero CTA", HERO_MARKER),
            ("quick-call CTA", PHONE_MARKER),
        )
        if marker not in text
    ]
    if missing_markers:
        errors.append(
            "index.html: cannot inject homepage callback links; missing " + ", ".join(missing_markers)
        )
        return

    text = text.replace(HERO_MARKER, HERO_MARKER + HERO_CALLBACK, 1)
    text = text.replace(PHONE_MARKER, PHONE_MARKER + PHONE_CALLBACK, 1)
    path.write_text(text, encoding="utf-8")

    if text.count(CALLBACK_URL) != 2:
        errors.append("index.html: homepage callback link injection produced an invalid count")
