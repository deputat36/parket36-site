#!/usr/bin/env python3
"""Validate that analytics signals cannot contain customer form data."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MAIN_JS = ROOT / "js" / "main.js"
CALLBACK_JS = ROOT / "js" / "callback-form.js"
NOTIFICATION_JS = ROOT / "js" / "lead-notification-feedback.js"
E2E_SPEC = ROOT / "tests" / "e2e" / "analytics-privacy.spec.mjs"
DOC = ROOT / "docs" / "analytics-privacy-contract.md"
RUNNER = ROOT / "tools" / "run_quality_checks.py"
QUALITY_CHECKER = ROOT / "tools" / "check_quality_runner.py"

REQUIRED_MARKERS = {
    E2E_SPEC: (
        "PRIVATE-LOCATION-улица-Тестовая-17",
        "PRIVATE-TASK-проверить-дефект-у-двери",
        "PRIVATE-CALLBACK-сегодня-после-19-00",
        "Клиент Privacy, +7 900 111-22-33",
        "parket36:lead",
        "parket36:phone-click",
        "parket36:lead-notification",
        "parket36:callback-open",
        "parket36:callback-request",
        "window.dataLayer",
        "window.ym",
        "expectNoPrivateData",
        "contact: PRIVATE.contact",
        "location: PRIVATE.location",
        "task: PRIVATE.task",
        "callback_time: PRIVATE.callback",
        "полная заявка не передаёт контакт",
        "callback-заявка не передаёт контакт",
    ),
    DOC: (
        "Privacy-контракт аналитики Паркет36",
        "Что запрещено передавать",
        "поле `contact`",
        "поля `location`",
        "поля `task`",
        "`callback_time`",
        "CustomEvent",
        "window.dataLayer",
        "window.ym",
        "tests/e2e/analytics-privacy.spec.mjs",
        "tools/check_analytics_privacy.py",
        "не заменяет юридическую проверку",
    ),
    RUNNER: (
        '"Validate analytics privacy", ["tools/check_analytics_privacy.py"]',
    ),
    QUALITY_CHECKER: (
        '["tools/check_analytics_privacy.py"]',
    ),
}

FORBIDDEN_EVENT_IDENTIFIERS = (
    "contact",
    "task",
    "locationValue",
    "callback_time",
    "callbackTime",
    "text,",
)

FORBIDDEN_NOTIFICATION_FIELDS = (
    "contact:",
    "task:",
    "location:",
    "callback_time:",
    "callbackTime:",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def block(text: str, start: str, end: str) -> str:
    start_position = text.find(start)
    if start_position < 0:
        return ""
    end_position = text.find(end, start_position + len(start))
    if end_position < 0:
        return ""
    return text[start_position:end_position]


def main() -> int:
    findings: list[str] = []
    texts: dict[Path, str] = {}

    for path in (MAIN_JS, CALLBACK_JS, NOTIFICATION_JS, *REQUIRED_MARKERS):
        if path in texts:
            continue
        if not path.is_file():
            findings.append(f"missing required file: {path.relative_to(ROOT)}")
            texts[path] = ""
            continue
        texts[path] = read(path)

    for path, markers in REQUIRED_MARKERS.items():
        text = texts.get(path, "")
        for marker in markers:
            if marker not in text:
                findings.append(f"{path.relative_to(ROOT)}: missing marker: {marker}")

    spec = texts.get(E2E_SPEC, "")
    if spec.count("expectNoPrivateData(analytics)") < 2:
        findings.append("analytics privacy spec must verify both assessment and callback signals")
    if spec.count("expect(lead.getPayload()).toMatchObject") < 2:
        findings.append("analytics privacy spec must prove private values still reach both protected lead payloads")
    for marker in ("9001112233", "+79001112233"):
        if marker not in spec:
            findings.append(f"analytics privacy spec must reject normalized phone marker: {marker}")

    main_js = texts.get(MAIN_JS, "")
    assessment_event = block(
        main_js,
        "emitLead({\n        type: leadSaved ? 'request-submit' : 'request-copy'",
        "\n      });",
    )
    if not assessment_event:
        findings.append("could not isolate assessment analytics event payload")
    else:
        for identifier in FORBIDDEN_EVENT_IDENTIFIERS:
            if identifier in assessment_event:
                findings.append(f"assessment analytics event contains private identifier: {identifier}")

    notification_js = texts.get(NOTIFICATION_JS, "")
    notification_detail = block(
        notification_js,
        "const notificationDetail = {",
        "\n    };",
    )
    if not notification_detail:
        findings.append("could not isolate lead notification analytics payload")
    else:
        for field in FORBIDDEN_NOTIFICATION_FIELDS:
            if field in notification_detail:
                findings.append(f"lead notification analytics payload contains private field: {field}")

    callback_js = texts.get(CALLBACK_JS, "")
    callback_datalayer = block(
        callback_js,
        "event: 'parket36_callback_request'",
        "\n      });",
    )
    if not callback_datalayer:
        findings.append("could not isolate callback dataLayer payload")
    else:
        for field in FORBIDDEN_NOTIFICATION_FIELDS:
            if field in callback_datalayer:
                findings.append(f"callback dataLayer payload contains private field: {field}")

    for path in (MAIN_JS, CALLBACK_JS, NOTIFICATION_JS):
        text = texts.get(path, "")
        for direct_leak in (
            "window.ym(contact",
            "window.ym(task",
            "dataLayer.push({ contact",
            "dataLayer.push({ task",
        ):
            if direct_leak in text:
                findings.append(f"{path.relative_to(ROOT)} contains direct analytics leak marker: {direct_leak}")

    if findings:
        print("Analytics privacy findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Analytics privacy contract passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
