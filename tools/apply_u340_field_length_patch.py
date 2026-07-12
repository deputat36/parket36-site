#!/usr/bin/env python3
from pathlib import Path

path = Path("supabase/functions/parket-public-lead/index.ts")
text = path.read_text(encoding="utf-8")

import_line = 'import { firstOversizedLeadField } from "./field-limits.ts";'
if import_line not in text:
    anchor = 'import { createClient } from "npm:@supabase/supabase-js@2";\n'
    if text.count(anchor) != 1:
        raise SystemExit("unexpected createClient import anchor")
    text = text.replace(anchor, anchor + import_line + "\n", 1)

validation_marker = 'error: "field_too_long"'
if validation_marker not in text:
    anchor = '''  if (cleanText(body.website, 200) || cleanText(body.company, 200)) {
    await writeAudit(supabase, { ...auditBase, accepted: false, reason: "honeypot_filled" });
    return json(req, 200, { ok: true, request_id: requestId });
  }

'''
    if text.count(anchor) != 1:
        raise SystemExit("unexpected honeypot anchor")
    block = anchor + '''  const oversizedField = firstOversizedLeadField(body);
  if (oversizedField) {
    await writeAudit(supabase, {
      ...auditBase,
      accepted: false,
      reason: "field_too_long",
      payload_summary: { ...summary, ...oversizedField },
    });
    return json(req, 422, {
      ok: false,
      error: "field_too_long",
      request_id: requestId,
      ...oversizedField,
    });
  }

'''
    text = text.replace(anchor, block, 1)

path.write_text(text, encoding="utf-8")
