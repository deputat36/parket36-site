#!/usr/bin/env python3
"""Validate fail-closed request forms for no-JS and partial-JS failures."""

from __future__ import annotations

from pathlib import Path
import sys

from form_fail_closed import self_test as form_safety_self_test

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "js" / "form-fail-closed.js"
BUILDER = ROOT / "tools" / "form_fail_closed.py"
JS_ASSETS = ROOT / "tools" / "js_assets.py"
E2E = ROOT / "tests" / "e2e" / "form-fail-closed.spec.mjs"
NO_JS_E2E = ROOT / "tests" / "e2e" / "no-js-accessibility.spec.mjs"
DOC = ROOT / "docs" / "form-fail-closed.md"
RUNNER = ROOT / "tools" / "run_quality_checks.py"
QUALITY_CHECKER = ROOT / "tools" / "check_quality_runner.py"
OPERATIONS_INDEX = ROOT / "docs" / "operations-index.md"

REQUIRED_MARKERS = {
    SCRIPT: (
        "const form = document.getElementById('request-form')",
        "[data-form-safety-submit=\"true\"]",
        "event.preventDefault()",
        "form.addEventListener('submit'",
        "data-form-safety-actions",
        "Форма загрузилась не полностью",
        "Данные не отправлены и остались в полях",
        "form.removeAttribute('aria-busy')",
        "submitButton.disabled = true",
        "submitButton.disabled = false",
        "form.dataset.formSafety = 'active'",
    ),
    BUILDER: (
        "prepare_fail_closed_forms",
        'data-form-safety="pending"',
        'data-form-safety-submit="true"',
        'data-form-no-script="true"',
        'disabled',
        'aria-disabled="true"',
        "JavaScript отключён, поэтому данные не отправлены",
        'tel:+79009267929',
        'FORM_SAFETY_SCRIPT = \'<script src="/js/form-fail-closed.js" defer></script>\'',
        'updated.replace(MAIN_SCRIPT, FORM_SAFETY_SCRIPT + "\\n" + MAIN_SCRIPT, 1)',
        "request contact must not be part of native form submission",
        "fail-closed hardening is not idempotent",
    ),
    JS_ASSETS: (
        "from form_fail_closed import prepare_fail_closed_forms",
        "prepare_fail_closed_forms(destination, errors)",
        "Normalize lead copy, harden forms, fingerprint JS",
    ),
    E2E: (
        "подробная форма сохраняет введённые данные при неполной загрузке",
        "callback-форма не перезагружает страницу без основного обработчика",
        "**/js/main.*.js",
        "data-form-safety-actions",
        "Данные не отправлены и остались в полях",
        "expect(page.url()).toBe(beforeUrl)",
    ),
    NO_JS_E2E: (
        "подробная форма без JavaScript не имитирует отправку и не стирает поля",
        "callback-форма без JavaScript оставляет только безопасный звонок",
        "javaScriptEnabled: false",
        "data-form-no-script",
        "toBeDisabled()",
        "press('Enter')",
        "expect(page.url()).toBe(beforeUrl)",
    ),
    DOC: (
        "Fail-closed формы",
        "Полностью отключённый JavaScript",
        "Частично загрузившийся JavaScript",
        "данные не отправлены",
        "не сохраняет значения полей",
        "не вызывает `fetch`",
        "не передаёт контакт в URL",
        "form-fail-closed.spec.mjs",
        "check_form_fail_closed.py",
    ),
    RUNNER: (
        '"Validate fail-closed forms", ["tools/check_form_fail_closed.py"]',
    ),
    QUALITY_CHECKER: (
        '["tools/check_form_fail_closed.py"]',
    ),
    OPERATIONS_INDEX: (
        "docs/form-fail-closed.md",
    ),
}

FORBIDDEN_SCRIPT_MARKERS = (
    "fetch(",
    "window.fetch",
    "localStorage",
    "sessionStorage",
    "navigator.clipboard",
    "window.dataLayer",
    "window.ym",
    "request-contact",
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def main() -> int:
    findings: list[str] = []
    texts: dict[Path, str] = {}

    if form_safety_self_test() != 0:
        findings.append("form fail-closed builder self-test failed")

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
            findings.append(f"form fail-closed module must remain transport- and storage-free: {marker}")

    if script.count("form.addEventListener('submit'") != 1:
        findings.append("form fail-closed module must install exactly one submit guard")
    prevent_position = script.find("event.preventDefault()")
    timeout_position = script.find("window.setTimeout")
    if min(prevent_position, timeout_position) < 0 or prevent_position > timeout_position:
        findings.append("native submit must be prevented before incomplete-load detection")

    builder = texts.get(BUILDER, "")
    if builder.count("FORM_SAFETY_SCRIPT") < 4:
        findings.append("form builder must define, inject and validate the safety script")

    js_assets = texts.get(JS_ASSETS, "")
    copy_position = js_assets.find("normalize_lead_copy(destination, errors)")
    safety_position = js_assets.find("prepare_fail_closed_forms(destination, errors)")
    mapping_position = js_assets.find("mapping = build_mapping(js_dir, errors)")
    if min(copy_position, safety_position, mapping_position) < 0 or not (
        copy_position < safety_position < mapping_position
    ):
        findings.append("forms must be hardened after copy normalization and before JS fingerprinting")

    runner = texts.get(RUNNER, "")
    reliability_position = runner.find('"Validate lead reliability", ["tools/check_lead_reliability.py"]')
    safety_check_position = runner.find('"Validate fail-closed forms", ["tools/check_form_fail_closed.py"]')
    feedback_position = runner.find('"Validate lead notification feedback", ["tools/check_lead_notification_feedback.py"]')
    if min(reliability_position, safety_check_position, feedback_position) < 0 or not (
        reliability_position < safety_check_position < feedback_position
    ):
        findings.append("fail-closed form check must run after lead reliability and before notification feedback")

    if findings:
        print("Form fail-closed findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Form fail-closed contract passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
