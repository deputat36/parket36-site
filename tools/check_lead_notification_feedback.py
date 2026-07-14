#!/usr/bin/env python3
"""Validate honest lead-notification feedback across frontend, docs, backend and E2E."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "js" / "lead-notification-feedback.js"
CALLBACK = ROOT / "js" / "callback-form.js"
BUILD = ROOT / "tools" / "build_pages.py"
BACKEND = ROOT / "supabase" / "functions" / "parket-public-lead" / "index.ts"
E2E = ROOT / "tests" / "e2e" / "lead-notification-feedback.spec.mjs"
DOC = ROOT / "docs" / "lead-notification-feedback.md"
CALLBACK_DOC = ROOT / "docs" / "callback-form.md"
ANALYTICS_DOC = ROOT / "docs" / "analytics-events.md"

REQUIRED_MARKERS = {
    FRONTEND: (
        "new Set(['sent', 'disabled', 'partial_failure'])",
        "? value : 'unknown'",
        "window.parket36LastLeadDelivery = null",
        "const publishDelivery = delivery =>",
        "window.parket36LastLeadDelivery = delivery ? Object.freeze({ ...delivery }) : null",
        "notificationConfirmed = delivery.notification === 'sent'",
        "Заявка сохранена",
        "Номер сохранён",
        "автоматическое уведомление Ивану пока не настроено",
        "доставку уведомления Ивану подтвердить не удалось",
        "автоматическое уведомление Ивану не подтверждено",
        "8 (900) 926-79-29",
        "parket36:lead-notification",
        "parket36_lead_notification",
        "notification_state",
        "lead-notification",
    ),
    CALLBACK: (
        "const readLeadDelivery = leadDetail =>",
        "window.parket36LastLeadDelivery || {}",
        "notification = leadDetail.notification || delivery.notification || 'unknown'",
        "notificationConfirmed",
        "notification_state: detail.notification",
        "notification_confirmed: detail.notificationConfirmed",
        "duplicate: detail.duplicate",
    ),
    BUILD: (
        "LEAD_NOTIFICATION_FEEDBACK_SCRIPT",
        'DEST / "js" / "lead-notification-feedback.js"',
        "replacement = [*scripts_before, MAIN_SCRIPT]",
        "replacement.append(LEAD_NOTIFICATION_FEEDBACK_SCRIPT)",
    ),
    BACKEND: (
        'notificationState = configuredNotifications.length === 0',
        '? "disabled"',
        ': "sent"',
        ': "partial_failure"',
        "notification: notificationState",
    ),
    E2E: (
        "sent подтверждает отправку Ивану",
        "disabled сообщает, что заявка сохранена",
        "partial_failure в callback не обещает звонок",
        "старый backend без notification считается unknown",
        "notificationConfirmed: true",
        "notificationConfirmed: false",
        "parket36_lead_notification",
    ),
    DOC: (
        "Факт сохранения заявки и подтверждение уведомления не смешиваются",
        "notification: sent",
        "notification: disabled",
        "notification: partial_failure",
        "unknown",
        "window.parket36LastLeadDelivery",
        "callback-request",
        "notification_state",
        "parket36:lead-notification",
        "parket36_lead_notification",
        "lead-notification",
        "контролируемая заявка",
    ),
    CALLBACK_DOC: (
        "HTTP 200 подтверждает сохранение заявки, но не всегда подтверждает автоматическое уведомление Ивану",
        "notification: sent",
        "notification: disabled",
        "notification: partial_failure",
        "notification: unknown",
        "`request-submit` означает, что заявка сохранена backend",
        "notification_state",
        "notification_confirmed",
        "lead-notification",
        "не означает, что Иван уже прочитал сообщение",
    ),
    ANALYTICS_DOC: (
        "Сохранение заявки и подтверждение автоматического уведомления Ивану — разные технические факты",
        "Backend подтвердил сохранение заявки в Supabase",
        "но не подтверждение доставки уведомления Ивану",
        "parket36:lead-notification",
        "notificationConfirmed: true",
        "notification: sent",
        "parket36_lead_notification",
        "notification_state",
        "notification_confirmed",
        "Не считать `request-submit` подтверждением",
    ),
}

FORBIDDEN_FRONTEND_MARKERS = (
    "notification !== 'sent' ? false : true",
    "notification || 'sent'",
    "payload?.notification || 'sent'",
)

FORBIDDEN_DOC_MARKERS = {
    CALLBACK_DOC: (
        "Заявка на обратный звонок отправлена Ивану. Он свяжется по указанному номеру.",
    ),
    ANALYTICS_DOC: (
        "Заявка успешно отправлена через Supabase",
        "Успешная заявка через Supabase",
    ),
}


def main() -> int:
    findings: list[str] = []

    texts: dict[Path, str] = {}
    for path, markers in REQUIRED_MARKERS.items():
        if not path.is_file():
            findings.append(f"missing required file: {path.relative_to(ROOT)}")
            texts[path] = ""
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        texts[path] = text
        for marker in markers:
            if marker not in text:
                findings.append(f"{path.relative_to(ROOT)}: missing marker: {marker}")

    frontend = texts.get(FRONTEND, "")
    for marker in FORBIDDEN_FRONTEND_MARKERS:
        if marker in frontend:
            findings.append(f"frontend must not turn an unknown notification into sent: {marker}")

    for path, markers in FORBIDDEN_DOC_MARKERS.items():
        text = texts.get(path, "")
        for marker in markers:
            if marker in text:
                findings.append(f"{path.relative_to(ROOT)}: stale unconditional delivery claim: {marker}")

    build = texts.get(BUILD, "")
    main_position = build.find("replacement = [*scripts_before, MAIN_SCRIPT]")
    feedback_position = build.find("replacement.append(LEAD_NOTIFICATION_FEEDBACK_SCRIPT)")
    if main_position < 0 or feedback_position < 0 or feedback_position < main_position:
        findings.append("lead notification feedback must be appended after main.js")

    callback = texts.get(CALLBACK, "")
    delivery_position = callback.find("const delivery = readLeadDelivery(leadDetail)")
    dispatch_position = callback.find("window.dispatchEvent(new CustomEvent('parket36:callback-request'")
    if delivery_position < 0 or dispatch_position < 0 or delivery_position > dispatch_position:
        findings.append("callback request must read delivery state before dispatching its event")

    if findings:
        print("Lead notification feedback findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Lead notification feedback passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
