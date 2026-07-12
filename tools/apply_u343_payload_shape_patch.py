#!/usr/bin/env python3
from pathlib import Path

path = Path("supabase/functions/parket-public-lead/index.ts")
text = path.read_text(encoding="utf-8")

import_line = 'import { validateLeadPayload } from "./payload-shape.ts";'
if import_line not in text:
    anchor = 'import { firstOversizedLeadField } from "./field-limits.ts";\n'
    if text.count(anchor) != 1:
        raise SystemExit("unexpected field-limits import anchor")
    text = text.replace(anchor, anchor + import_line + "\n", 1)

old_block = '''  let body: LeadPayload;
  try {
    body = JSON.parse(bodyText);
  } catch (_) {
    return json(req, 400, { ok: false, error: "bad_json" });
  }

'''
new_block = '''  let parsedBody: unknown;
  try {
    parsedBody = JSON.parse(bodyText);
  } catch (_) {
    return json(req, 400, { ok: false, error: "bad_json" });
  }

  const payloadShape = validateLeadPayload(parsedBody);
  if (!payloadShape.ok) {
    return json(req, payloadShape.status, {
      ok: false,
      error: payloadShape.error,
      field: payloadShape.field,
      expected: payloadShape.expected,
      received: payloadShape.received,
    });
  }
  const body: LeadPayload = payloadShape.body;

'''

if old_block in text:
    text = text.replace(old_block, new_block, 1)
elif new_block not in text:
    raise SystemExit("unexpected JSON parsing anchor")

path.write_text(text, encoding="utf-8")
