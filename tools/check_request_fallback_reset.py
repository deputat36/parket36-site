#!/usr/bin/env python3
"""Validate stale request fallback cleanup before a new form submission."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "js" / "lead-notification-feedback.js"
E2E = ROOT / "tests" / "e2e" / "request-fallback-reset.spec.mjs"
DOC = ROOT / "docs" / "request-fallback-reset.md"
RUNNER = ROOT / "tools" / "run_quality_checks.py"
QUALITY_CHECKER = ROOT / "tools" / "check_quality_runner.py"

REQUIRED_MARKERS = {
    FRONTEND: (
        "const clearFallbackText = form =>",
        "form?.querySelector('[data-request-fallback]')?.remove()",
        "clearFallbackActions(event.target)",
        "clearFallbackText(event.target)",
        "const fallbackVisible = Boolean(form?.querySelector('[data-request-fallback]'))",
    ),
    E2E: (
        "успешное повторное копирование удаляет старый текстовый fallback",
        "window.__parketRejectClipboard = true",
        "window.__parketRejectClipboard = false",
        "clipboard_denied",
        "data-request-fallback",
        "toHaveCount(0)",
        "Текст скопирован",
        "not.toContainText('Скопируйте готовый текст ниже')",
        "data-lead-fallback-actions",
    ),
    DOC: (
        "Очистка старого текстового fallback",
        "data-request-fallback",
        "новом событии `submit`",
        "Текстовый fallback, созданный текущей попыткой",
        "Текст скопирован",
        "request-fallback-reset.spec.mjs",
        "check_request_fallback_reset.py",
        "не меняет payload",
    ),
    RUNNER: (
        '"Validate request fallback reset", ["tools/check_request_fallback_reset.py"]',
    ),
    QUALITY_CHECKER: (
        '["tools/check_request_fallback_reset.py"]',
    ),
}

FORBIDDEN_FRONTEND_MARKERS = (
    "fallback.value = ''",
    "fallback.textContent = ''",
    "document.querySelector('[data-request-fallback]').value",
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

    frontend = texts.get(FRONTEND, "")
    for marker in FORBIDDEN_FRONTEND_MARKERS:
        if marker in frontend:
            findings.append(f"frontend must remove stale fallback without reading or rewriting it: {marker}")

    if frontend.count("const clearFallbackText = form =>") != 1:
        findings.append("frontend must define exactly one stale fallback cleanup helper")
    if frontend.count("clearFallbackText(event.target)") != 1:
        findings.append("frontend must clear stale text exactly once at the start of submit")

    submit_listener = frontend.find("document.addEventListener('submit', event =>")
    reset_delivery = frontend.find("publishDelivery(null)", submit_listener)
    clear_actions = frontend.find("clearFallbackActions(event.target)", reset_delivery)
    clear_text = frontend.find("clearFallbackText(event.target)", clear_actions)
    warning_text = frontend.find("const warningText =", clear_text)
    if min(submit_listener, reset_delivery, clear_actions, clear_text, warning_text) < 0 or not (
        submit_listener < reset_delivery < clear_actions < clear_text < warning_text
    ):
        findings.append("submit must reset delivery, actions and stale text before feedback processing")

    fallback_visibility = frontend.find(
        "const fallbackVisible = Boolean(form?.querySelector('[data-request-fallback]'))"
    )
    if fallback_visibility < clear_text:
        findings.append("fallback visibility must be measured only after stale text cleanup")

    if findings:
        print("Request fallback reset findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Request fallback reset passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
