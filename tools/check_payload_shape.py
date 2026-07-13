#!/usr/bin/env python3
"""Validate runtime lead payload and contact-phone checks with CI coverage."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD_MODULE = ROOT / "supabase/functions/parket-public-lead/payload-shape.ts"
PAYLOAD_TEST = ROOT / "supabase/functions/parket-public-lead/payload-shape_test.ts"
CONTACT_MODULE = ROOT / "supabase/functions/parket-public-lead/contact-validation.ts"
CONTACT_TEST = ROOT / "supabase/functions/parket-public-lead/contact-validation_test.ts"
EDGE = ROOT / "supabase/functions/parket-public-lead/index.ts"
CLIENT_VALIDATION = ROOT / "js/contact-validation.js"
BROWSER_TEST = ROOT / "tests/e2e/contact-validation.spec.mjs"
SITE_QUALITY = ROOT / ".github/workflows/site-quality.yml"
PAGES = ROOT / ".github/workflows/pages.yml"
PAYLOAD_DENO_TEST = "deno test supabase/functions/parket-public-lead/payload-shape_test.ts"
CONTACT_DENO_TEST = "deno test supabase/functions/parket-public-lead/contact-validation_test.ts"

REQUIRED = {
    PAYLOAD_MODULE: [
        'import { validateContactPhone } from "./contact-validation.ts";',
        "LEAD_STRING_FIELDS = Object.freeze",
        "validateLeadPayload",
        'error: "invalid_payload"',
        'error: "invalid_field_type"',
        'error: "contact_phone_invalid"',
        'expected: "object"',
        'expected: "string"',
        'expected: "boolean"',
        'expected: "10-15 digits"',
        "validateContactPhone(body.contact)",
        'field: "contact"',
        '"test_mode" in body',
    ],
    PAYLOAD_TEST: [
        'Deno.test("validateLeadPayload accepts the public form contract"',
        'Deno.test("validateLeadPayload accepts protected test mode"',
        'Deno.test("validateLeadPayload rejects null, arrays and scalar JSON"',
        'Deno.test("validateLeadPayload rejects non-string lead fields"',
        'Deno.test("validateLeadPayload rejects contact without a usable phone"',
        'Deno.test("validateLeadPayload leaves empty contact to required-field validation"',
        'Deno.test("validateLeadPayload rejects non-boolean test mode"',
        'result.error === "contact_phone_invalid"',
        'result.expected === "10-15 digits"',
    ],
    CONTACT_MODULE: [
        "CONTACT_PHONE_MIN_DIGITS = 10",
        "CONTACT_PHONE_MAX_DIGITS = 15",
        "contactPhoneDigitCount",
        "validateContactPhone",
        "digits >= CONTACT_PHONE_MIN_DIGITS",
        "digits <= CONTACT_PHONE_MAX_DIGITS",
    ],
    CONTACT_TEST: [
        'Deno.test("contact phone contract matches the public form"',
        'Deno.test("contactPhoneDigitCount ignores names and punctuation"',
        'Deno.test("validateContactPhone accepts 10 to 15 digits"',
        'Deno.test("validateContactPhone rejects text, short and oversized numbers"',
        '"Иван, +7 (900) 123-45-67"',
    ],
    EDGE: [
        'import { validateLeadPayload } from "./payload-shape.ts";',
        "let parsedBody: unknown",
        "const payloadShape = validateLeadPayload(parsedBody)",
        "const body: LeadPayload = payloadShape.body",
        "error: payloadShape.error",
        "expected: payloadShape.expected",
        "received: payloadShape.received",
    ],
    CLIENT_VALIDATION: [
        "MIN_PHONE_DIGITS = 10",
        "MAX_PHONE_DIGITS = 15",
        "parket36:lead-error",
        "contact_phone_invalid",
        "serverPhoneErrorPending",
        "Проверьте номер и отправьте заявку ещё раз.",
    ],
    BROWSER_TEST: [
        "форма не отправляет заявку без пригодного номера",
        "форма принимает распространённый формат российского телефона",
        "серверная ошибка телефона возвращает фокус в контактное поле",
        "contact_phone_invalid",
        "toHaveAttribute('aria-invalid', 'true')",
        "toBeFocused()",
    ],
    SITE_QUALITY: [PAYLOAD_DENO_TEST, CONTACT_DENO_TEST],
    PAGES: [PAYLOAD_DENO_TEST, CONTACT_DENO_TEST],
}


def main() -> int:
    findings: list[str] = []

    for path, markers in REQUIRED.items():
        if not path.exists():
            findings.append(f"missing file: {path.relative_to(ROOT).as_posix()}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in markers:
            if marker not in text:
                findings.append(f"{path.relative_to(ROOT).as_posix()}: missing marker: {marker}")

    if EDGE.exists():
        text = EDGE.read_text(encoding="utf-8", errors="ignore")
        shape_position = text.find("const payloadShape = validateLeadPayload(parsedBody)")
        config_position = text.find('const supabaseUrl = Deno.env.get("SUPABASE_URL")')
        health_position = text.find("if (body.test_mode === true)")
        if min(shape_position, config_position, health_position) == -1:
            findings.append("Edge Function: cannot verify payload-validation order")
        elif not (shape_position < config_position < health_position):
            findings.append("Edge Function: payload and phone must be validated before Supabase and test_mode access")
        if "let body: LeadPayload;" in text:
            findings.append("Edge Function: JSON must first be parsed as unknown")

    if PAYLOAD_MODULE.exists():
        text = PAYLOAD_MODULE.read_text(encoding="utf-8", errors="ignore")
        type_check_position = text.find("for (const field of LEAD_STRING_FIELDS)")
        phone_check_position = text.find("validateContactPhone(body.contact)")
        test_mode_position = text.find('"test_mode" in body')
        if min(type_check_position, phone_check_position, test_mode_position) == -1:
            findings.append("Payload validator: cannot verify type, phone and test_mode order")
        elif not (type_check_position < phone_check_position < test_mode_position):
            findings.append("Payload validator: contact type must be checked before phone digits and test_mode")

    if findings:
        print("Payload and phone validation findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Payload and phone validation check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
