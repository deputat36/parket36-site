#!/usr/bin/env python3
"""Validate runtime lead payload shape checks and their CI coverage."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "supabase/functions/parket-public-lead/payload-shape.ts"
TEST = ROOT / "supabase/functions/parket-public-lead/payload-shape_test.ts"
EDGE = ROOT / "supabase/functions/parket-public-lead/index.ts"
SITE_QUALITY = ROOT / ".github/workflows/site-quality.yml"
PAGES = ROOT / ".github/workflows/pages.yml"
DENO_TEST = "deno test supabase/functions/parket-public-lead/payload-shape_test.ts"

REQUIRED = {
    MODULE: [
        "LEAD_STRING_FIELDS = Object.freeze",
        "validateLeadPayload",
        'error: "invalid_payload"',
        'error: "invalid_field_type"',
        'expected: "object"',
        'expected: "string"',
        'expected: "boolean"',
        '"test_mode" in body',
    ],
    TEST: [
        'Deno.test("validateLeadPayload accepts the public form contract"',
        'Deno.test("validateLeadPayload accepts protected test mode"',
        'Deno.test("validateLeadPayload rejects null, arrays and scalar JSON"',
        'Deno.test("validateLeadPayload rejects non-string lead fields"',
        'Deno.test("validateLeadPayload rejects non-boolean test mode"',
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
    SITE_QUALITY: [DENO_TEST],
    PAGES: [DENO_TEST],
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
            findings.append("Edge Function: payload shape must be validated before Supabase and test_mode access")
        if "let body: LeadPayload;" in text:
            findings.append("Edge Function: JSON must first be parsed as unknown")

    if findings:
        print("Payload shape findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Payload shape check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
