#!/usr/bin/env python3
"""Harden public lead forms so partial or disabled JavaScript cannot cause a false submit."""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path

FORM_RE = re.compile(
    r"(?P<open><form\b(?=[^>]*\bid=[\"']request-form[\"'])[^>]*>)"
    r"(?P<body>.*?)"
    r"(?P<close></form>)",
    re.IGNORECASE | re.DOTALL,
)
SUBMIT_RE = re.compile(
    r"<button\b(?=[^>]*\btype=[\"']submit[\"'])[^>]*>",
    re.IGNORECASE,
)
MAIN_SCRIPT = '<script src="/js/main.js" defer></script>'
FORM_SAFETY_SCRIPT = '<script src="/js/form-fail-closed.js" defer></script>'
FORM_MARKER = 'data-form-safety="pending"'
BUTTON_MARKER = 'data-form-safety-submit="true"'
NOSCRIPT_MARKER = 'data-form-no-script="true"'
NOSCRIPT_BLOCK = (
    '<noscript><div class="request-note" data-form-no-script="true">'
    '<strong>Форма сейчас недоступна.</strong> JavaScript отключён, поэтому данные не отправлены. '
    'Позвоните Ивану: <a href="tel:+79009267929">8 (900) 926-79-29</a>.'
    '</div></noscript>'
)


def add_attribute(tag: str, attribute: str) -> str:
    if attribute.split("=", 1)[0] in tag:
        return tag
    return tag[:-1].rstrip() + " " + attribute + ">"


def harden_form(match: re.Match[str], errors: list[str], relative: str) -> str:
    opening = add_attribute(match.group("open"), FORM_MARKER)
    body = match.group("body")
    submit_buttons = SUBMIT_RE.findall(body)
    if len(submit_buttons) != 1:
        errors.append(f"{relative}: request form must contain exactly one submit button")
        return match.group(0)

    if BUTTON_MARKER not in body:
        original = submit_buttons[0]
        hardened = add_attribute(original, BUTTON_MARKER)
        hardened = add_attribute(hardened, "disabled")
        hardened = add_attribute(hardened, 'aria-disabled="true"')
        body = body.replace(original, hardened, 1)

    if NOSCRIPT_MARKER not in body:
        button_position = body.find("<button", max(0, body.find(BUTTON_MARKER) - 160))
        if button_position < 0:
            errors.append(f"{relative}: cannot place no-script fallback before submit button")
            return match.group(0)
        body = body[:button_position] + NOSCRIPT_BLOCK + body[button_position:]

    return opening + body + match.group("close")


def prepare_fail_closed_forms(destination: Path, errors: list[str]) -> int:
    script_path = destination / "js" / "form-fail-closed.js"
    if not script_path.is_file():
        errors.append("Public js/form-fail-closed.js is missing")
        return 0

    hardened_count = 0
    for html_file in sorted(destination.rglob("*.html")):
        text = html_file.read_text(encoding="utf-8")
        relative = html_file.relative_to(destination).as_posix()
        matches = list(FORM_RE.finditer(text))
        if not matches:
            continue

        def replace(match: re.Match[str]) -> str:
            nonlocal hardened_count
            hardened_count += 1
            return harden_form(match, errors, relative)

        updated = FORM_RE.sub(replace, text)
        if FORM_SAFETY_SCRIPT not in updated:
            if MAIN_SCRIPT not in updated:
                errors.append(f"{relative}: request form page is missing main.js")
            else:
                updated = updated.replace(MAIN_SCRIPT, FORM_SAFETY_SCRIPT + "\n" + MAIN_SCRIPT, 1)
        html_file.write_text(updated, encoding="utf-8")

        for match in FORM_RE.finditer(updated):
            block = match.group(0)
            for marker in (FORM_MARKER, BUTTON_MARKER, NOSCRIPT_MARKER, "disabled", 'aria-disabled="true"'):
                if marker not in block:
                    errors.append(f"{relative}: fail-closed form marker is missing: {marker}")
            named_contact = re.search(
                r"<(?:input|textarea|select)\b(?=[^>]*\bid=[\"']request-contact[\"'])[^>]*\bname=",
                block,
                re.IGNORECASE,
            )
            if named_contact:
                errors.append(f"{relative}: request contact must not be part of native form submission")
        if updated.count(FORM_SAFETY_SCRIPT) != 1:
            errors.append(f"{relative}: expected exactly one form fail-closed script")

    return hardened_count


def self_test() -> int:
    failures: list[str] = []
    fixture = (
        '<form class="request-form" id="request-form">'
        '<input id="request-contact" required>'
        '<button class="btn" type="submit">Отправить</button>'
        '<p id="request-status"></p>'
        '</form>'
        + MAIN_SCRIPT
    )
    with tempfile.TemporaryDirectory(prefix="parket36-form-safety-") as temp:
        root = Path(temp)
        (root / "js").mkdir()
        (root / "js" / "form-fail-closed.js").write_text("// safety\n", encoding="utf-8")
        page = root / "index.html"
        page.write_text(fixture, encoding="utf-8")
        errors: list[str] = []
        count = prepare_fail_closed_forms(root, errors)
        result = page.read_text(encoding="utf-8")
        if errors:
            failures.extend(errors)
        if count != 1:
            failures.append(f"expected one hardened form, found {count}")
        for marker in (FORM_MARKER, BUTTON_MARKER, NOSCRIPT_MARKER, "disabled", 'aria-disabled="true"', FORM_SAFETY_SCRIPT):
            if marker not in result:
                failures.append(f"missing hardened marker: {marker}")
        if result.find(FORM_SAFETY_SCRIPT) > result.find(MAIN_SCRIPT):
            failures.append("form safety script must load before main.js")
        second_errors: list[str] = []
        prepare_fail_closed_forms(root, second_errors)
        if second_errors:
            failures.extend(second_errors)
        if page.read_text(encoding="utf-8") != result:
            failures.append("fail-closed hardening is not idempotent")

    with tempfile.TemporaryDirectory(prefix="parket36-form-safety-name-") as temp:
        root = Path(temp)
        (root / "js").mkdir()
        (root / "js" / "form-fail-closed.js").write_text("// safety\n", encoding="utf-8")
        (root / "index.html").write_text(
            fixture.replace('id="request-contact"', 'id="request-contact" name="contact"'),
            encoding="utf-8",
        )
        errors = []
        prepare_fail_closed_forms(root, errors)
        if not any("native form submission" in error for error in errors):
            failures.append("named contact field was not rejected")

    if failures:
        print("Form fail-closed self-test failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Form fail-closed self-test passed")
    return 0


if __name__ == "__main__":
    sys.exit(self_test())
