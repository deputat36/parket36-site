#!/usr/bin/env python3
"""Normalize public lead copy so storage and notification are never conflated."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile

REPLACEMENTS = (
    (
        "Заполните короткую форму: заявка уйдёт Ивану, а готовый текст скопируется, чтобы вы могли приложить фотографии пола отдельными сообщениями.",
        "Заполните короткую форму: сервис попробует сохранить заявку, а готовый текст скопируется, чтобы вы могли приложить фотографии пола отдельными сообщениями. Если уведомление Ивану не подтвердится, форма сразу предложит позвонить.",
    ),
    (
        "Заполните форму — сайт отправит заявку Ивану",
        "Заполните форму — получите понятный следующий шаг",
    ),
    (
        "После нажатия кнопки заявка передаётся Ивану через защищённую форму. Готовый текст также копируется в буфер обмена: его удобно отправить вместе с фотографиями пола или использовать как подсказку при звонке.",
        "После нажатия сервис попробует сохранить заявку в защищённой системе. Готовый текст также копируется в буфер обмена: его удобно отправить вместе с фотографиями пола или использовать как подсказку при звонке. Если автоматическое уведомление не подтвердится, форма покажет номер Ивана.",
    ),
    (
        "Заявка отправляется Ивану через защищённую форму. Готовый текст также копируется, чтобы вы могли отправить фото отдельными сообщениями.",
        "Форма попробует сохранить заявку в защищённой системе. Готовый текст также копируется, чтобы вы могли отправить фото отдельными сообщениями. Если уведомление Ивану не подтвердится, сразу появится кнопка звонка.",
    ),
    (
        "Иван получит заявку через ту же защищённую систему и сможет перезвонить для первого уточнения.",
        "Форма попробует сохранить контакт в защищённой системе. Если уведомление Ивану не подтвердится, сразу появится кнопка звонка.",
    ),
    (
        "Заявка отправляется Ивану через защищённую форму. Нажимая кнопку, вы соглашаетесь с",
        "Форма попробует сохранить номер в защищённой системе. Если уведомление Ивану не подтвердится, сразу появится кнопка звонка. Нажимая кнопку, вы соглашаетесь с",
    ),
    (
        "Заявка отправляется Ивану через защищённую форму, а текст обращения дополнительно копируется в буфер обмена. Если автоматическая отправка или копирование не сработали, пользователь видит подготовленный текст и может передать его вручную по телефону или в сообщении.",
        "Форма пытается сохранить заявку в защищённой системе. Отдельный статус сообщает, подтверждено ли автоматическое уведомление Ивану. Текст обращения дополнительно копируется в буфер обмена. Если сохранение, уведомление или копирование не сработали, пользователь видит подготовленный текст и может передать его вручную по телефону или в сообщении.",
    ),
    (
        "Заявки сохраняются в защищённом хранилище Supabase.",
        "Успешно принятые заявки сохраняются в защищённом хранилище Supabase.",
    ),
)

FORBIDDEN_MARKERS = (
    "заявка уйдёт Ивану",
    "сайт отправит заявку Ивану",
    "заявка передаётся Ивану через защищённую форму",
    "Заявка отправляется Ивану через защищённую форму",
    "Иван получит заявку через ту же защищённую систему",
)


def apply_replacements(text: str) -> str:
    normalized = text
    for source, replacement in REPLACEMENTS:
        normalized = normalized.replace(source, replacement)
    return normalized


def normalize_lead_copy(destination: Path, errors: list[str]) -> None:
    targets = sorted([*destination.rglob("*.html"), *destination.rglob("*.js")])
    for path in targets:
        text = path.read_text(encoding="utf-8")
        normalized = apply_replacements(text)
        if normalized != text:
            path.write_text(normalized, encoding="utf-8")

        relative = path.relative_to(destination).as_posix()
        for marker in FORBIDDEN_MARKERS:
            if marker in normalized:
                errors.append(f"{relative}: unconditional lead-delivery claim remains: {marker}")


def self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="parket36-lead-copy-") as temp:
        destination = Path(temp) / "_site"
        (destination / "js").mkdir(parents=True)
        html = destination / "index.html"
        script = destination / "js" / "main.js"
        html.write_text(
            "<p>Заявка отправляется Ивану через защищённую форму. Нажимая кнопку, вы соглашаетесь с правилами.</p>",
            encoding="utf-8",
        )
        script.write_text(
            "const text = 'Заявка отправляется Ивану через защищённую форму. Готовый текст также копируется, чтобы вы могли отправить фото отдельными сообщениями.';",
            encoding="utf-8",
        )

        errors: list[str] = []
        normalize_lead_copy(destination, errors)
        if errors:
            failures.extend(errors)
        combined = html.read_text(encoding="utf-8") + script.read_text(encoding="utf-8")
        if "попробует сохранить" not in combined:
            failures.append("honest storage wording was not inserted")
        if "уведомление Ивану не подтвердится" not in combined:
            failures.append("notification fallback wording was not inserted")
        for marker in FORBIDDEN_MARKERS:
            if marker in combined:
                failures.append(f"stale unconditional claim remained: {marker}")

    if failures:
        print("Lead copy self-test failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Lead copy self-test passed")
    return 0


if __name__ == "__main__":
    sys.exit(self_test())
