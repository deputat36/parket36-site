#!/usr/bin/env python3
"""Validate transparent commercial guidance on the key Parket36 pages."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

PAGE_MARKERS = {
    "index.html": {
        'href="/kontakty/">Работы в Воронеже и области: география и контакты →</a>': "homepage local commercial link",
    },
    "uslugi/index.html": {
        "Что будет согласовано до старта": "scope agreement heading",
        "Состав работ": "scope card",
        "Материалы и подготовка": "materials and preparation card",
        "Границы предварительной оценки": "estimate limitations card",
        "Изменения по ходу": "change agreement card",
        "согласуется отдельно до выполнения": "separate approval wording",
        'href="/zayavka/">Получить предварительный ориентир</a>': "assessment CTA",
        'href="tel:+79009267929">Обсудить задачу по телефону</a>': "phone CTA",
    },
    "uslugi/parket-i-poly/index.html": {
        "Проверка ограничений": "limitations step",
        "Состав работ": "scope step",
        "возможные доплаты": "possible extras disclosure",
        "без лишних обещаний": "realistic expectation wording",
        'href="/ceny/">Как рассчитывается цена</a>': "price explanation link",
    },
    "ceny/index.html": {
        "Что влияет на цену": "price factor section",
        "Что лучше уточнить до старта": "pre-start checklist",
        "Что не включается молча": "no silent extras heading",
        "Новые задачи и скрытые дефекты нужно согласовывать отдельно": "separate approval heading",
        "не заменить осмотр": "estimate limitation wording",
    },
    "kontakty/index.html": {
        "Циклёвка, реставрация и ремонт паркета в Воронеже и области": "local commercial H1",
        "Что сообщить при первом звонке": "first-call guidance",
        "Как получить предварительный ориентир по объекту в Воронеже или области": "local assessment process",
        "Что важно уточнить для объекта за пределами Воронежа": "regional visit guidance",
        "Предварительный разговор не заменяет осмотр": "remote estimate limitation",
        'href="tel:+79009267929">Позвонить Ивану</a>': "local phone CTA",
        'href="/zayavka/">Получить оценку по фото</a>': "local assessment CTA",
    },
}

FORBIDDEN_PROMISES = {
    "точная цена по фото": "unsupported exact remote price promise",
    "цена не изменится": "unsupported fixed price promise",
    "гарантированно без доплат": "unsupported no-extras promise",
    "любой паркет как новый": "unsupported restoration promise",
}


def main() -> int:
    findings: list[str] = []

    for relative, markers in PAGE_MARKERS.items():
        path = ROOT / relative
        if not path.is_file():
            findings.append(f"{relative}: page is missing")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker, label in markers.items():
            if marker not in text:
                findings.append(f"{relative}: missing {label}: {marker}")
        lowered = text.lower()
        for phrase, label in FORBIDDEN_PROMISES.items():
            if phrase in lowered:
                findings.append(f"{relative}: contains {label}: {phrase}")

    if findings:
        print("Commercial page findings:")
        for finding in sorted(findings):
            print(f"  - {finding}")
        return 1

    print("Commercial page guidance passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
