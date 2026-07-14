import { createClient } from "npm:@supabase/supabase-js@2";
import { validateRequestId } from "./request-id.ts";

const HEALTHCHECK_HEADER = "x-parket-health-token";
const LEADS_TABLE = "parket_leads";
const AUDIT_TABLE = "parket_public_lead_audit";
const ALLOWED_ORIGINS = new Set([
  "https://parket36.ru",
  "https://www.parket36.ru",
]);

type SupabaseClient = ReturnType<typeof createClient<any, "public", "public">>;

type VerificationCheck = {
  ok: boolean;
  detail: string;
};

function cleanText(value: unknown, max = 500) {
  return String(value ?? "").replace(/\s+/g, " ").trim().slice(0, max);
}

function requestOrigin(req: Request) {
  return req.headers.get("origin") || "";
}

function corsHeaders(req: Request) {
  const origin = requestOrigin(req);
  const allowOrigin = ALLOWED_ORIGINS.has(origin) ? origin : "https://parket36.ru";
  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Headers": `content-type, ${HEALTHCHECK_HEADER}`,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Content-Type": "application/json; charset=utf-8",
    "Vary": "Origin",
  };
}

function json(req: Request, status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: corsHeaders(req),
  });
}

function safeEqual(left: string, right: string) {
  if (!left || !right || left.length !== right.length) return false;
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
}

function parseEnvKeyMap(raw: string | undefined) {
  if (!raw) return "";
  try {
    const parsed = JSON.parse(raw);
    const mapped = typeof parsed?.default === "string" ? parsed.default : "";
    if (!mapped) return "";
    return Deno.env.get(mapped) || mapped;
  } catch (_) {
    return raw;
  }
}

function getServiceKey() {
  return (
    parseEnvKeyMap(Deno.env.get("SUPABASE_SECRET_KEYS")) ||
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ||
    Deno.env.get("SERVICE_ROLE_KEY") ||
    ""
  );
}

function authorized(req: Request) {
  const expected = cleanText(Deno.env.get("PARKET_HEALTHCHECK_TOKEN"), 500);
  const provided = cleanText(req.headers.get(HEALTHCHECK_HEADER), 500);
  return Boolean(expected && safeEqual(expected, provided));
}

async function rowExists(
  supabase: SupabaseClient,
  table: string,
  requestId: string,
  accepted: boolean | null,
): Promise<VerificationCheck> {
  let query = supabase
    .from(table)
    .select("id", { count: "exact", head: true })
    .eq("request_id", requestId);

  if (accepted !== null) query = query.eq("accepted", accepted);

  const { count, error } = await query;
  if (error) {
    return {
      ok: false,
      detail: `${error.code || "db_error"}: ${cleanText(error.message, 300)}`,
    };
  }

  return {
    ok: (count || 0) > 0,
    detail: (count || 0) > 0 ? "found" : "missing",
  };
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders(req) });
  }

  if (req.method !== "POST") {
    return json(req, 405, { ok: false, error: "method_not_allowed" });
  }

  const origin = requestOrigin(req);
  if (!ALLOWED_ORIGINS.has(origin)) {
    return json(req, 403, { ok: false, error: "origin_not_allowed" });
  }

  if (!authorized(req)) {
    return json(req, 403, { ok: false, error: "verification_forbidden" });
  }

  const contentType = req.headers.get("content-type") || "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return json(req, 415, { ok: false, error: "json_required" });
  }

  let body: Record<string, unknown>;
  try {
    const parsed = await req.json();
    if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
      return json(req, 400, { ok: false, error: "invalid_payload" });
    }
    body = parsed as Record<string, unknown>;
  } catch (_) {
    return json(req, 400, { ok: false, error: "bad_json" });
  }

  const requestId = validateRequestId(body.request_id);
  if (!requestId.ok) {
    return json(req, 422, { ok: false, error: requestId.error });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
  const serviceKey = getServiceKey();
  if (!supabaseUrl || !serviceKey) {
    return json(req, 500, { ok: false, error: "server_not_configured" });
  }

  const supabase = createClient(supabaseUrl, serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  const [lead, audit] = await Promise.all([
    rowExists(supabase, LEADS_TABLE, requestId.value, null),
    rowExists(supabase, AUDIT_TABLE, requestId.value, true),
  ]);

  const checks = {
    parket_leads: lead,
    parket_public_lead_audit: audit,
  };
  const ok = Object.values(checks).every((check) => check.ok);

  return json(req, ok ? 200 : 404, {
    ok,
    request_id: requestId.value,
    checks,
  });
});
