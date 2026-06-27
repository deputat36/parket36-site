import { createClient } from "npm:@supabase/supabase-js@2";

const DEFAULT_ALLOWED_ORIGINS = [
  "https://parket36.ru",
  "https://www.parket36.ru",
  "https://deputat36.github.io",
  "http://localhost:3000",
  "http://localhost:8000",
  "http://127.0.0.1:5500",
];
const MAX_BODY_BYTES = 25_000;
const RATE_LIMIT_WINDOW_MS = 15 * 60 * 1000;
const RATE_LIMIT_MAX_ACCEPTED = 6;

type LeadPayload = Record<string, unknown>;

function allowedOrigins() {
  const configured = Deno.env.get("PARKET_PUBLIC_ALLOWED_ORIGINS");
  if (!configured) return DEFAULT_ALLOWED_ORIGINS;
  return configured
    .split(",")
    .map((origin) => origin.trim())
    .filter(Boolean);
}

function requestOrigin(req: Request) {
  return req.headers.get("origin") || "";
}

function isAllowedOrigin(req: Request) {
  const origin = requestOrigin(req);
  if (!origin) return true;
  return allowedOrigins().includes(origin);
}

function corsHeadersFor(req: Request) {
  const origin = requestOrigin(req);
  const origins = allowedOrigins();
  const allowOrigin = origin && origins.includes(origin) ? origin : origins[0];
  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Content-Type": "application/json; charset=utf-8",
    "Vary": "Origin",
  };
}

function json(req: Request, status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: corsHeadersFor(req),
  });
}

function cleanText(value: unknown, max = 1000) {
  return String(value ?? "").replace(/\s+/g, " ").trim().slice(0, max);
}

function cleanMultiline(value: unknown, max = 3000) {
  return String(value ?? "").replace(/\r\n/g, "\n").trim().slice(0, max);
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

function requestIdFromBody(body: LeadPayload) {
  const incoming = cleanText(body.request_id, 120);
  if (/^[a-zA-Z0-9._:-]{8,120}$/.test(incoming)) return incoming;
  return "server-" + crypto.randomUUID();
}

function clientIp(req: Request) {
  const forwarded = req.headers.get("x-forwarded-for") || "";
  return (
    req.headers.get("cf-connecting-ip") ||
    req.headers.get("x-real-ip") ||
    forwarded.split(",")[0].trim() ||
    ""
  );
}

function bytesToHex(bytes: Uint8Array) {
  return Array.from(bytes)
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function ipHashFor(req: Request) {
  const ip = clientIp(req);
  if (!ip) return "";
  const salt = Deno.env.get("PARKET_IP_HASH_SALT") || "";
  const bytes = new TextEncoder().encode(`${salt}:${ip}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return bytesToHex(new Uint8Array(digest));
}

async function writeAudit(
  supabase: ReturnType<typeof createClient>,
  row: Record<string, unknown>,
) {
  const { error } = await supabase.from("parket_public_lead_audit").insert(row);
  if (error) {
    console.error("parket_public_lead_audit_failed", {
      request_id: row.request_id || null,
      reason: row.reason || null,
      code: error.code || null,
      message: error.message,
    });
  }
}

function payloadSummary(body: LeadPayload) {
  return {
    service: cleanText(body.service, 120),
    location: cleanText(body.location, 160),
    page: cleanText(body.page, 500),
    has_task: Boolean(cleanMultiline(body.task, 3000)),
    has_contact: Boolean(cleanText(body.contact, 240)),
  };
}

function attributionFromBody(body: LeadPayload, req: Request) {
  return {
    page: cleanText(body.page, 500),
    referrer: cleanText(req.headers.get("referer"), 1000),
    origin: requestOrigin(req),
    utm_source: cleanText(body.utm_source, 160),
    utm_medium: cleanText(body.utm_medium, 160),
    utm_campaign: cleanText(body.utm_campaign, 220),
    utm_content: cleanText(body.utm_content, 220),
    utm_term: cleanText(body.utm_term, 220),
  };
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeadersFor(req) });
  if (req.method !== "POST") return json(req, 405, { ok: false, error: "method_not_allowed" });
  if (!isAllowedOrigin(req)) return json(req, 403, { ok: false, error: "origin_not_allowed" });

  const contentType = req.headers.get("content-type") || "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return json(req, 415, { ok: false, error: "json_required" });
  }

  const bodyText = await req.text();
  if (new TextEncoder().encode(bodyText).length > MAX_BODY_BYTES) {
    return json(req, 413, { ok: false, error: "payload_too_large" });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
  const serviceKey = getServiceKey();
  if (!supabaseUrl || !serviceKey) return json(req, 500, { ok: false, error: "server_not_configured" });

  let body: LeadPayload;
  try {
    body = JSON.parse(bodyText);
  } catch (_) {
    return json(req, 400, { ok: false, error: "bad_json" });
  }

  const requestId = requestIdFromBody(body);
  const ipHash = await ipHashFor(req);
  const userAgent = cleanText(req.headers.get("user-agent"), 500);
  const origin = requestOrigin(req);
  const summary = payloadSummary(body);
  const supabase = createClient(supabaseUrl, serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  const auditBase = {
    request_id: requestId,
    origin,
    ip_hash: ipHash || null,
    user_agent: userAgent,
    payload_summary: summary,
  };

  if (cleanText(body.website, 200) || cleanText(body.company, 200)) {
    await writeAudit(supabase, { ...auditBase, accepted: false, reason: "honeypot_filled" });
    return json(req, 200, { ok: true, request_id: requestId });
  }

  const task = cleanMultiline(body.task, 3000);
  const contact = cleanText(body.contact, 240);
  if (task.length < 8 || contact.length < 3) {
    await writeAudit(supabase, { ...auditBase, accepted: false, reason: "task_or_contact_required" });
    return json(req, 400, { ok: false, error: "task_or_contact_required", request_id: requestId });
  }

  if (ipHash) {
    const since = new Date(Date.now() - RATE_LIMIT_WINDOW_MS).toISOString();
    const { count, error } = await supabase
      .from("parket_public_lead_audit")
      .select("id", { count: "exact", head: true })
      .eq("ip_hash", ipHash)
      .eq("accepted", true)
      .gte("created_at", since);

    if (error) {
      console.error("parket_public_lead_rate_check_failed", {
        request_id: requestId,
        code: error.code || null,
        message: error.message,
      });
    } else if ((count || 0) >= RATE_LIMIT_MAX_ACCEPTED) {
      await writeAudit(supabase, { ...auditBase, accepted: false, reason: "rate_limited" });
      return json(req, 429, { ok: false, error: "rate_limited", request_id: requestId });
    }
  }

  const lead = {
    request_id: requestId,
    service: cleanText(body.service, 160),
    location: cleanText(body.location, 160),
    area: cleanText(body.area, 80),
    photos: cleanText(body.photos, 500),
    video: cleanText(body.video, 500),
    task,
    callback_time: cleanText(body.callback_time, 160),
    contact,
    page: cleanText(body.page, 500),
    attribution: attributionFromBody(body, req),
    metadata: {
      form: "parket36_request_form_v1",
      submitted_at: new Date().toISOString(),
    },
    user_agent: userAgent,
  };

  const { data, error } = await supabase
    .from("parket_leads")
    .insert(lead)
    .select("id")
    .single();

  if (error) {
    if (error.code === "23505" || error.message.toLowerCase().includes("duplicate")) {
      await writeAudit(supabase, { ...auditBase, accepted: false, reason: "duplicate_request_id" });
      return json(req, 200, { ok: true, duplicate: true, request_id: requestId });
    }

    console.error("parket_public_lead_insert_failed", {
      request_id: requestId,
      code: error.code || null,
      message: error.message,
    });
    await writeAudit(supabase, { ...auditBase, accepted: false, reason: "insert_failed" });
    return json(req, 500, { ok: false, error: "temporary_error", request_id: requestId });
  }

  await writeAudit(supabase, { ...auditBase, accepted: true, reason: "accepted" });
  return json(req, 200, { ok: true, request_id: requestId, lead_id: data?.id });
});
