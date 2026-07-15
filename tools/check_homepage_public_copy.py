#!/usr/bin/env python3
"""Ensure the source homepage is client-ready without build-time text repair."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
HOMEPAGE = ROOT / "index.html"

FORBIDDEN = (
    "Фото вместо иллюстрации",
    "Место под реальное фото",
    "Место под фото",
    "Место для фото",
    "Сюда нужен реальный кадр",
    "Места под будущие реальные фотографии",
    "будущие кейсы",
    "после съёмки по ТЗ",
)

REQUIRED = (
    'aria-label="Как подготовить фотографии пола для предварительной оценки"',
    '<span class="photo-slot__mark">Оценка по фото</span>',
    '<span class="photo-slot__label">Общий вид комнаты</span>',
    '<span class="photo-slot__mark">Дефект крупно</span>',
    '<span class="photo-slot__label">Проблемное место</span>',
    '<span class="photo-slot__mark">Короткое видео</span>',
    '<span class="photo-slot__label">Скрип или движение</span>',
    "Для первого ориентира достаточно фото пола и короткого описания задачи.",
    'href="tel:+79009267929">Позвонить Ивану</a>',
)


def validate(text: str) -> list[str]:
    findings = [f"forbidden source copy remains: {phrase}" for phrase in FORBIDDEN if phrase in text]
    findings.extend(f"required source marker is missing: {marker}" for marker in REQUIRED if marker not in text)
    return findings


def main() -> int:
    if not HOMEPAGE.is_file():
        print("Homepage public-copy findings:\n  - index.html is missing")
        return 1

    findings = validate(HOMEPAGE.read_text(encoding="utf-8", errors="ignore"))
    if findings:
        print("Homepage public-copy findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Homepage source copy is client-ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
