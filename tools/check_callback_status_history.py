#!/usr/bin/env python3
"""Prevent transient false success announcements in the callback live region."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CALLBACK = ROOT / "js" / "callback-form.js"
E2E = ROOT / "tests" / "e2e" / "callback-status-history.spec.mjs"
DOC = ROOT / "docs" / "callback-status-history.md"
RUNNER = ROOT / "tools" / "run_quality_checks.py"
QUALITY_CHECKER = ROOT / "tools" / "check_quality_runner.py"

REQUIRED_MARKERS = {
    CALLBACK: (
        "const PHONE_DISPLAY = '8 (900) 926-79-29'",
        "const callbackStatusText = delivery =>",
        "if (delivery.notification === 'sent')",
        "const subject = delivery.duplicate ? 'Номер уже был сохранён' : 'Номер сохранён'",
        "повторная отправка не подтверждает автоматическое уведомление Ивану",
        "автоматическое уведомление Ивану пока не настроено",
        "доставку уведомления Ивану подтвердить не удалось",
        "const delivery = readLeadDelivery(event.detail)",
        "status.textContent = callbackStatusText(delivery)",
        "emitCallbackRequest({ ...event.detail, ...delivery })",
    ),
    E2E: (
        "неподтверждённое callback-уведомление никогда не показывает ложное обещание звонка",
        "подтверждённое callback-уведомление сохраняет обычное обещание обратного звонка",
        "window.__parketCallbackStatusHistory",
        "new MutationObserver(record)",
        "Он свяжется по указанному номеру",
        "toHaveAttribute('data-status-tone', 'warning')",
        "toHaveAttribute('data-status-tone', 'success')",
        "notification: 'disabled'",
        "notification: 'sent'",
    ),
    DOC: (
        "aria-live=\"polite\"",
        "каждое промежуточное сообщение",
        "сначала устанавливал текст",
        "читает фактическое состояние доставки до первой записи итогового текста",
        "MutationObserver",
        "не содержит фразу `Он свяжется по указанному номеру`",
        "tools/check_callback_status_history.py",
    ),
    RUNNER: (
        '"Validate callback status history", ["tools/check_callback_status_history.py"]',
    ),
    QUALITY_CHECKER: (
        '["tools/check_callback_status_history.py"]',
    ),
}

FORBIDDEN_CALLBACK_MARKERS = (
    "status.textContent = 'Заявка на обратный звонок отправлена Ивану. Он свяжется по указанному номеру.'",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def main() -> int:
    findings: list[str] = []
    texts: dict[Path, str] = {}

    for path, markers in REQUIRED_MARKERS.items():
        if not path.is_file():
            findings.append(f"missing required file: {path.relative_to(ROOT)}")
            texts[path] = ""
            continue
        text = read(path)
        texts[path] = text
        for marker in markers:
            if marker not in text:
                findings.append(f"{path.relative_to(ROOT)}: missing marker: {marker}")

    callback = texts.get(CALLBACK, "")
    for marker in FORBIDDEN_CALLBACK_MARKERS:
        if marker in callback:
            findings.append(
                "callback form must not publish an unconditional success message before delivery is checked"
            )

    delivery_position = callback.find("const delivery = readLeadDelivery(event.detail)")
    status_position = callback.find("status.textContent = callbackStatusText(delivery)")
    dispatch_position = callback.find("emitCallbackRequest({ ...event.detail, ...delivery })")
    if min(delivery_position, status_position, dispatch_position) < 0 or not (
        delivery_position < status_position < dispatch_position
    ):
        findings.append(
            "callback request must resolve delivery before writing the live-region status and dispatching analytics"
        )

    e2e = texts.get(E2E, "")
    if "history.some(text => text.includes('Он свяжется по указанному номеру'))).toBe(false)" not in e2e:
        findings.append("E2E must reject the transient false callback promise")

    if findings:
        print("Callback status history findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Callback status history passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
