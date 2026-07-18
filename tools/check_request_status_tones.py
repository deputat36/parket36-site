#!/usr/bin/env python3
"""Validate accessible semantic tones for public request-form status messages."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
STATUS_SCRIPT = ROOT / "js" / "request-status-tone.js"
CSS = ROOT / "css" / "accessibility-polish.css"
BUILD = ROOT / "tools" / "build_pages.py"
E2E = ROOT / "tests" / "e2e" / "request-status-tone.spec.mjs"
HISTORY_E2E = ROOT / "tests" / "e2e" / "assessment-status-history.spec.mjs"
DOC = ROOT / "docs" / "request-status-tones.md"
HISTORY_DOC = ROOT / "docs" / "assessment-status-history.md"
RUNNER = ROOT / "tools" / "run_quality_checks.py"
QUALITY_CHECKER = ROOT / "tools" / "check_quality_runner.py"

REQUIRED_MARKERS = {
    STATUS_SCRIPT: (
        "const form = document.getElementById('request-form')",
        "const status = form.querySelector('#request-status')",
        "new Set(['info', 'success', 'warning', 'error'])",
        "const assessmentWarningText = (delivery, fallbackVisible) => {",
        "const installAssessmentStatusGuard = () => {",
        "form.dataset.formKind === 'callback'",
        "Object.getOwnPropertyDescriptor(Node.prototype, 'textContent')",
        "window.parket36LastLeadDelivery",
        "delivery.notification !== 'sent'",
        "Boolean(form.querySelector('[data-request-fallback]'))",
        "installAssessmentStatusGuard();",
        "status.dataset.statusTone = tone",
        "status.setAttribute('role', 'status')",
        "status.setAttribute('aria-live', 'polite')",
        "status.setAttribute('aria-atomic', 'true')",
        "new MutationObserver(syncToneFromText)",
        "detail.type === 'request-copy'",
        "detail.type !== 'request-submit'",
        "detail.notification === 'sent' ? 'success' : 'warning'",
        "Автоматически отправить заявку не удалось",
        "уведомление Ивану",
        "Заявка отправлена Ивану",
    ),
    CSS: (
        '.form-status[data-status-tone="info"]:not(:empty)',
        '.form-status[data-status-tone="success"]:not(:empty)',
        '.form-status[data-status-tone="warning"]:not(:empty)',
        '.form-status[data-status-tone="error"]:not(:empty)',
        "background: #edf5fb",
        "background: #e6f2ea",
        "background: #fff1d6",
        "background: #fde9e6",
    ),
    BUILD: (
        "REQUEST_STATUS_TONE_SCRIPT",
        '<script src="/js/request-status-tone.js" defer></script>',
        'DEST / "js" / "request-status-tone.js"',
        '"request status tone"',
        "needs_status_tone = REQUEST_STATUS_TONE_SCRIPT not in text",
        "replacement.append(REQUEST_STATUS_TONE_SCRIPT)",
        "if 'id=\"request-form\"' not in text",
    ),
    E2E: (
        "шаблон задачи показывает нейтральный информационный статус",
        "ошибка телефона получает красный error-статус",
        "подтверждённое уведомление получает зелёный success-статус",
        "неподтверждённое уведомление получает warning-статус",
        "ошибка backend получает error-статус и сохраняет fallback",
        "data-status-tone",
        "aria-live",
        "aria-atomic",
    ),
    HISTORY_E2E: (
        "подробная форма не показывает ложный успех при отключённом уведомлении",
        "ручной текстовый fallback не показывает ложный успех при partial failure",
        "window.__parketAssessmentStatusHistory",
        "value.startsWith('Заявка отправлена Ивану')",
        "notification: 'disabled'",
        "notification: 'partial_failure'",
        "data-status-tone",
        "[data-request-fallback]",
    ),
    DOC: (
        "Тоны статуса формы заявки",
        "data-status-tone",
        "`info`",
        "`success`",
        "`warning`",
        "`error`",
        'aria-live="polite"',
        'aria-atomic="true"',
        "только в публичные страницы, содержащие `id=\"request-form\"`",
        "не читает контакт",
        "не вызывает `fetch`",
        "не пишет в `dataLayer`",
        "check_request_status_tones.py",
    ),
    HISTORY_DOC: (
        "История статуса подробной заявки",
        "`/zayavka/`",
        "`window.parket36LastLeadDelivery`",
        "`notification: sent`",
        "`notification: disabled`",
        "`notification: partial_failure`",
        "заменяется до записи в DOM",
        "не вызывает `fetch`",
        "assessment-status-history.spec.mjs",
        "check_request_status_tones.py",
    ),
    RUNNER: (
        '"Validate request status tones", ["tools/check_request_status_tones.py"]',
    ),
    QUALITY_CHECKER: (
        '["tools/check_request_status_tones.py"]',
    ),
}

FORBIDDEN_SCRIPT_MARKERS = (
    "fetch(",
    "window.fetch",
    "LEAD_ENDPOINT",
    "navigator.clipboard",
    "#request-contact",
    "request-contact",
    "window.dataLayer",
    "window.ym",
    "parket36MetrikaId",
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

    script = texts.get(STATUS_SCRIPT, "")
    for marker in FORBIDDEN_SCRIPT_MARKERS:
        if marker in script:
            findings.append(f"status-tone module must remain presentation-only: {marker}")

    if "window.parket36LastLeadDelivery =" in script:
        findings.append("status-tone module may read but must not overwrite lead delivery state")

    guard_position = script.find("installAssessmentStatusGuard();")
    observer_position = script.find("new MutationObserver(syncToneFromText)")
    if min(guard_position, observer_position) < 0 or guard_position > observer_position:
        findings.append("assessment status guard must be installed before the tone observer")

    for tone in ("info", "success", "warning", "error"):
        selector = f'.form-status[data-status-tone="{tone}"]:not(:empty)'
        if texts.get(CSS, "").count(selector) != 1:
            findings.append(f"CSS must define exactly one selector for status tone: {tone}")

    build = texts.get(BUILD, "")
    feedback_position = build.find("replacement.append(LEAD_NOTIFICATION_FEEDBACK_SCRIPT)")
    status_position = build.find("replacement.append(REQUEST_STATUS_TONE_SCRIPT)")
    if min(feedback_position, status_position) < 0 or feedback_position > status_position:
        findings.append("request status tone script must be appended after lead notification feedback")

    form_guard_position = build.find("if 'id=\"request-form\"' not in text")
    status_need_position = build.find("needs_status_tone = REQUEST_STATUS_TONE_SCRIPT not in text")
    if min(form_guard_position, status_need_position) < 0 or form_guard_position > status_need_position:
        findings.append("request status tone injection must remain inside the request-form page guard")

    runner = texts.get(RUNNER, "")
    feedback_check_position = runner.find(
        '"Validate lead notification feedback", ["tools/check_lead_notification_feedback.py"]'
    )
    tone_check_position = runner.find(
        '"Validate request status tones", ["tools/check_request_status_tones.py"]'
    )
    payload_check_position = runner.find(
        '"Validate lead payload shape", ["tools/check_payload_shape.py"]'
    )
    if min(feedback_check_position, tone_check_position, payload_check_position) < 0 or not (
        feedback_check_position < tone_check_position < payload_check_position
    ):
        findings.append("status-tone check must run after notification feedback and before payload shape")

    if findings:
        print("Request status tone findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Request status tone contract passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
