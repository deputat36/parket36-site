#!/usr/bin/env python3
from pathlib import Path

path = Path("supabase/functions/parket-public-lead/index.ts")
text = path.read_text(encoding="utf-8")

import_line = 'import { evaluateOriginPolicy } from "./origin-policy.ts";'
if import_line not in text:
    anchor = 'import { createClient } from "npm:@supabase/supabase-js@2";\n'
    if text.count(anchor) != 1:
        raise SystemExit("unexpected createClient import anchor")
    text = text.replace(anchor, anchor + import_line + "\n", 1)

legacy = '''function isAllowedOrigin(req: Request) {
  const origin = requestOrigin(req);
  if (!origin) return true;
  return allowedOrigins().includes(origin);
}

'''
if legacy in text:
    text = text.replace(legacy, "", 1)

helper = '''function healthcheckTokenAuthorized(req: Request) {
  const expectedToken = getHealthcheckToken();
  const providedToken = cleanText(req.headers.get(HEALTHCHECK_HEADER), 500);
  return Boolean(expectedToken && safeEqual(expectedToken, providedToken));
}

'''
if helper not in text:
    anchor = '''function getHealthcheckToken() {
  return envText("PARKET_HEALTHCHECK_TOKEN", 500);
}

'''
    if text.count(anchor) != 1:
        raise SystemExit("unexpected healthcheck token anchor")
    text = text.replace(anchor, anchor + helper, 1)

old_guard = '  if (!isAllowedOrigin(req)) return json(req, 403, { ok: false, error: "origin_not_allowed" });\n'
new_guard = '''  const originDecision = evaluateOriginPolicy(
    requestOrigin(req),
    allowedOrigins(),
    healthcheckTokenAuthorized(req),
  );
  if (!originDecision.allowed) {
    return json(req, 403, { ok: false, error: originDecision.error });
  }
'''
if old_guard in text:
    text = text.replace(old_guard, new_guard, 1)
elif new_guard not in text:
    raise SystemExit("unexpected origin guard anchor")

path.write_text(text, encoding="utf-8")
