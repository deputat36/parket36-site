#!/usr/bin/env python3
"""Validate the request-readiness UI, privacy boundary, build wiring and browser contract."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "js" / "request-readiness.js"
CSS = ROOT / "css" / "request-readiness.css"
CSS_BUNDLE = ROOT / "tools" / "css_bundle.py"
BUILD = ROOT / "tools" / "build_pages.py"
E2E = ROOT / "tests" / "e2e" / "request-readiness.spec.mjs"
DOC = ROOT / "docs" / "request-readiness.md"
RUNNER = ROOT / "tools" / "run_quality_checks.py"
QUALITY_CHECKER = ROOT / "tools" / "check_quality_runner.py"
OPERATIONS_INDEX = ROOT / "docs" / "operations-index.md"

REQUIRED_MARKERS = {
    SCRIPT: (
        "const form = document.getElementById('request-form')",
        "form.dataset.formKind === 'callback'",
        "const PHONE_DIGITS_MIN = 10",
        "const PHONE_DIGITS_MAX = 15",
        "const TASK_MIN_LENGTH = 35",
        "key: 'location'",
        "key: 'area'",
        "key: 'photos'",
        "key: 'task'",
        "key: 'contact'",
        "key: 'callback_time'",
        "panel.dataset.requestReadiness = 'true'",
        "role', 'progressbar'",
        "aria-valuenow",
        "aria-live', 'polite'",
        "form.dataset.requestReadinessState",
        "type: 'request-readiness'",
        "parket36:request-readiness",
        "parket36_request_readiness",
        "completed_count",
        "total_count",
        "missing_keys",
        "request-readiness",
        "form.addEventListener('submit', () => emitReadiness(update()), true)",
    ),
    CSS: (
        ".request-readiness {",
        ".request-readiness.is-ready",
        ".request-readiness__progress",
        ".request-readiness__progress-bar",
        ".request-readiness__list li.is-complete",
        "var(--p36-color-semantic-status-success)",
        "@media (max-width: 640px)",
        "@media (prefers-reduced-motion: reduce)",
    ),
    CSS_BUNDLE: (
        '"request-readiness.css"',
    ),
    BUILD: (
        "REQUEST_READINESS_SCRIPT",
        '<script src="/js/request-readiness.js" defer></script>',
        'DEST / "js" / "request-readiness.js"',
        '"request readiness"',
        "needs_readiness = REQUEST_READINESS_SCRIPT not in text",
        "replacement.append(REQUEST_READINESS_SCRIPT)",
    ),
    E2E: (
        "подробная форма показывает пять безопасных критериев готовности",
        "подробная форма становится готовой после заполнения полезных данных",
        "короткая форма использует три критерия обратного звонка",
        "при отправке аналитика получает только счётчики и ключи, без значений полей",
        "data-request-readiness",
        "aria-valuenow",
        "parket36:request-readiness",
        "parket36_request_readiness",
        "missing: ['photos']",
        "not.toContain('Воронеж')",
        "not.toContain('Алексей')",
    ),
    DOC: (
        "Готовность обращения",
        "не превращает рекомендации в обязательные поля",
        "не менее 35 символов",
        "от 10 до 15 цифр",
        'role="progressbar"',
        'aria-live="polite"',
        "форма остаётся доступной для отправки",
        "не хранит значения полей",
        "parket36:request-readiness",
        "parket36_request_readiness",
        "Не передаются имя, телефон",
        "check_request_readiness.py",
    ),
    RUNNER: (
        '"Validate request readiness", ["tools/check_request_readiness.py"]',
    ),
    QUALITY_CHECKER: (
        '["tools/check_request_readiness.py"]',
    ),
    OPERATIONS_INDEX: (
        "docs/request-readiness.md",
    ),
}

FORBIDDEN_SCRIPT_MARKERS = (
    "localStorage",
    "sessionStorage",
    "fetch(",
    "window.fetch",
    "navigator.clipboard",
    "request_id",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term",
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

    script = texts.get(SCRIPT, "")
    for marker in FORBIDDEN_SCRIPT_MARKERS:
        if marker in script:
            findings.append(f"request readiness must not store or transmit form values: {marker}")
    if "form.dataset.requestReadiness =" in script:
        findings.append("form state must not reuse the panel data-request-readiness selector")

    if script.count("window.dataLayer.push({") != 1:
        findings.append("request readiness must emit exactly one bounded dataLayer event")
    if script.count("window.dispatchEvent(new CustomEvent('parket36:request-readiness'") != 1:
        findings.append("request readiness must emit exactly one custom readiness event")
    if script.count("form.addEventListener('submit'") != 1:
        findings.append("request readiness analytics must run exactly once per submit attempt")

    detail_start = script.find("const detail = {")
    detail_end = script.find("};", detail_start)
    detail_block = script[detail_start:detail_end] if detail_start >= 0 and detail_end >= 0 else ""
    for forbidden in ("value(", "phoneDigits(", "attribution", "contact", "locationValue", "task"):
        if forbidden in detail_block:
            findings.append(f"readiness event detail contains possible form value: {forbidden}")

    build = texts.get(BUILD, "")
    status_position = build.find("replacement.append(REQUEST_STATUS_TONE_SCRIPT)")
    readiness_position = build.find("replacement.append(REQUEST_READINESS_SCRIPT)")
    if min(status_position, readiness_position) < 0 or status_position > readiness_position:
        findings.append("request readiness script must load after request status tone")

    runner = texts.get(RUNNER, "")
    tone_position = runner.find('"Validate request status tones", ["tools/check_request_status_tones.py"]')
    readiness_check_position = runner.find('"Validate request readiness", ["tools/check_request_readiness.py"]')
    payload_position = runner.find('"Validate lead payload shape", ["tools/check_payload_shape.py"]')
    if min(tone_position, readiness_check_position, payload_position) < 0 or not (
        tone_position < readiness_check_position < payload_position
    ):
        findings.append("request readiness check must run after status tones and before payload shape")

    if findings:
        print("Request readiness findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Request readiness contract passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
