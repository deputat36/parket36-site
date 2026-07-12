import { createClient } from "npm:@supabase/supabase-js@2";
import { evaluateOriginPolicy } from "./origin-policy.ts";
import { firstOversizedLeadField } from "./field-limits.ts";
import { validateLeadPayload } from "./payload-shape.ts";

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
const RATE_LIMIT_MAX_ATTEMPTS = 30;
const RATE_LIMIT_MAX_ACCEPTED = 6;
const NOTIFICATION_TIMEOUT_MS = 4_000;
const HEALTHCHECK_HEADER = "x-parket-health-token";

const LEADS_TABLE = "parket_leads";
const AUDIT_TABLE = "parket_public_lead_audit";
const RESEND_API_URL = "https://api.resend.com/emails";

type LeadPayload = Record<string, unknown>;
type LeadRecord = Record<string, unknown>;
type SupabaseClient = ReturnType<typeof createClient<any, "public", "public">>;
type NotificationChannel = "telegram" | "email";
type NotificationResult = {
  channel: NotificationChannel;
  configured: boolean;
  ok: boolean;
  detail: string;
};

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

function corsHeadersFor(req: Request) {
  const origin = requestOrigin(req);
  const origins = allowedOrigins();
  const allowOrigin = origin && origins.includes(origin) ? origin : origins[0];
  return {
    "Access-Control-Allow-Origin": allowOrigin,
    "Access-Control-Allow-Headers": `authorization, x-client-info, apikey, content-type, ${HEALTHCHECK_HEADER}`,
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

function envText(name: string, max = 1000) {
  return cleanText(Deno.env.get(name), max);
}

function envFlag(name: string) {
  return ["1", "true", "yes"].includes((Deno.env.get(name) || "").trim().toLowerCase());
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

function getIpHashSalt() {
  return envText("PARKET_IP_HASH_SALT", 500);
}

function getHealthcheckToken() {
  return envText("PARKET_HEALTHCHECK_TOKEN", 500);
}

function healthcheckTokenAuthorized(req: Request) {
  const expectedToken = getHealthcheckToken();
  const providedToken = cleanText(req.headers.get(HEALTHCHECK_HEADER), 500);
  return Boolean(expectedToken && safeEqual(expectedToken, providedToken));
}

function emailRecipients() {
  return (Deno.env.get("PARKET_EMAIL_TO") || "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean)
    .slice(0, 20);
}

function safeEqual(left: string, right: string) {
  if (!left || !right || left.length !== right.length) return false;
  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }
  return difference === 0;
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

async function ipHashFor(req: Request, salt: string) {
  const ip = clientIp(req);
  if (!ip) return "";
  const bytes = new TextEncoder().encode(`${salt}:${ip}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return bytesToHex(new Uint8Array(digest));
}

async function writeAudit(
  supabase: SupabaseClient,
  row: Record<string, unknown>,
) {
  const { error } = await supabase.from(AUDIT_TABLE).insert(row);
  if (error) {
    console.error("parket_public_lead_audit_failed", {
      request_id: row.request_id || null,
      reason: row.reason || null,
      code: error.code || null,
      message: error.message,
    });
  }
}

async function recentAuditCount(
  supabase: SupabaseClient,
  ipHash: string,
  since: string,
  accepted: boolean | null,
  requestId: string,
  scope: string,
) {
  let query = supabase
    .from(AUDIT_TABLE)
    .select("id", { count: "exact", head: true })
    .eq("ip_hash", ipHash)
    .gte("created_at", since);

  if (accepted !== null) query = query.eq("accepted", accepted);

  const { count, error } = await query;
  if (error) {
    console.error("parket_public_lead_rate_check_failed", {
      request_id: requestId,
      scope,
      code: error.code || null,
      message: error.message,
    });
    return null;
  }

  return count || 0;
}

async function tableHealth(supabase: SupabaseClient, table: string) {
  const { count, error } = await supabase
    .from(table)
    .select("id", { count: "exact", head: true });

  if (error) {
    return {
      ok: false,
      detail: `${error.code || "db_error"}: ${error.message}`,
    };
  }

  return {
    ok: true,
    detail: `readable; rows=${count || 0}`,
  };
}

function optionalConfigHealth(values: string[], label: string) {
  const present = values.filter(Boolean).length;
  if (present === 0) return { ok: true, detail: "disabled" };
  if (present === values.length) return { ok: true, detail: "configured" };
  return {
    ok: false,
    detail: `${label} is partially configured: ${present}/${values.length}`,
  };
}

function notificationConfigHealth() {
  const telegram = optionalConfigHealth(
    [envText("PARKET_TELEGRAM_BOT_TOKEN", 500), envText("PARKET_TELEGRAM_CHAT_ID", 200)],
    "Telegram",
  );
  const email = optionalConfigHealth(
    [
      envText("PARKET_RESEND_API_KEY", 500),
      envText("PARKET_EMAIL_FROM", 320),
      emailRecipients().join(","),
    ],
    "Email",
  );

  return { telegram, email };
}

async function runHealthcheck(req: Request, supabase: SupabaseClient, salt: string) {
  const expectedToken = getHealthcheckToken();
  if (!expectedToken) {
    return json(req, 503, { ok: false, test_mode: true, error: "healthcheck_not_configured" });
  }

  const providedToken = cleanText(req.headers.get(HEALTHCHECK_HEADER), 500);
  if (!safeEqual(expectedToken, providedToken)) {
    return json(req, 403, { ok: false, test_mode: true, error: "healthcheck_forbidden" });
  }

  const leads = await tableHealth(supabase, LEADS_TABLE);
  const audit = await tableHealth(supabase, AUDIT_TABLE);
  const notifications = notificationConfigHealth();
  const checks = {
    service_role: { ok: true, detail: "configured" },
    ip_hash_salt: { ok: Boolean(salt), detail: salt ? "configured" : "local override enabled" },
    parket_leads: leads,
    parket_public_lead_audit: audit,
    telegram_notification: notifications.telegram,
    email_notification: notifications.email,
  };
  const ok = Object.values(checks).every((check) => check.ok);

  return json(req, ok ? 200 : 503, {
    ok,
    test_mode: true,
    checks,
  });
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

function leadNotificationText(lead: LeadRecord, leadId: string, requestId: string) {
  const rows = [
    "Новая заявка Паркет36",
    `ID: ${leadId || requestId}`,
    `Контакт: ${cleanText(lead.contact, 240)}`,
    `Услуга: ${cleanText(lead.service, 160) || "не указана"}`,
    `Где: ${cleanText(lead.location, 160) || "не указано"}`,
    `Площадь: ${cleanText(lead.area, 80) || "не указана"}`,
    `Когда позвонить: ${cleanText(lead.callback_time, 160) || "не указано"}`,
    `Задача: ${cleanMultiline(lead.task, 1800)}`,
    `Страница: ${cleanText(lead.page, 500) || "не указана"}`,
  ];

  return rows.join("\n").slice(0, 3900);
}

async function postJson(
  url: string,
  body: unknown,
  headers: Record<string, string> = {},
) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), NOTIFICATION_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...headers,
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    const responseText = await response.text();
    let responseBody: Record<string, unknown> = {};

    if (responseText) {
      try {
        responseBody = JSON.parse(responseText);
      } catch (_) {
        responseBody = { raw: responseText.slice(0, 500) };
      }
    }

    if (!response.ok) {
      const description = cleanText(responseBody.description || responseBody.message, 300);
      throw new Error(`HTTP ${response.status}${description ? `: ${description}` : ""}`);
    }

    return responseBody;
  } finally {
    clearTimeout(timeout);
  }
}

async function sendTelegramNotification(
  lead: LeadRecord,
  leadId: string,
  requestId: string,
): Promise<NotificationResult> {
  const token = envText("PARKET_TELEGRAM_BOT_TOKEN", 500);
  const chatId = envText("PARKET_TELEGRAM_CHAT_ID", 200);
  if (!token && !chatId) {
    return { channel: "telegram", configured: false, ok: true, detail: "disabled" };
  }
  if (!token || !chatId) {
    return { channel: "telegram", configured: true, ok: false, detail: "partial configuration" };
  }

  try {
    const response = await postJson(
      `https://api.telegram.org/bot${token}/sendMessage`,
      {
        chat_id: chatId,
        text: leadNotificationText(lead, leadId, requestId),
      },
    );
    if (response.ok !== true) {
      throw new Error(cleanText(response.description, 300) || "Telegram returned ok=false");
    }
    return { channel: "telegram", configured: true, ok: true, detail: "sent" };
  } catch (error) {
    return {
      channel: "telegram",
      configured: true,
      ok: false,
      detail: error instanceof Error ? error.message : "telegram_send_failed",
    };
  }
}

async function sendEmailNotification(
  lead: LeadRecord,
  leadId: string,
  requestId: string,
): Promise<NotificationResult> {
  const apiKey = envText("PARKET_RESEND_API_KEY", 500);
  const from = envText("PARKET_EMAIL_FROM", 320);
  const to = emailRecipients();
  if (!apiKey && !from && to.length === 0) {
    return { channel: "email", configured: false, ok: true, detail: "disabled" };
  }
  if (!apiKey || !from || to.length === 0) {
    return { channel: "email", configured: true, ok: false, detail: "partial configuration" };
  }

  const subject = envText("PARKET_EMAIL_SUBJECT", 200) || "Новая заявка Паркет36";

  try {
    await postJson(
      RESEND_API_URL,
      {
        from,
        to,
        subject,
        text: leadNotificationText(lead, leadId, requestId),
      },
      { Authorization: `Bearer ${apiKey}` },
    );
    return { channel: "email", configured: true, ok: true, detail: "sent" };
  } catch (error) {
    return {
      channel: "email",
      configured: true,
      ok: false,
      detail: error instanceof Error ? error.message : "email_send_failed",
    };
  }
}

async function sendLeadNotifications(
  lead: LeadRecord,
  leadId: string,
  requestId: string,
) {
  return Promise.all([
    sendTelegramNotification(lead, leadId, requestId),
    sendEmailNotification(lead, leadId, requestId),
  ]);
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeadersFor(req) });
  if (req.method !== "POST") return json(req, 405, { ok: false, error: "method_not_allowed" });
  const originDecision = evaluateOriginPolicy(
    requestOrigin(req),
    allowedOrigins(),
    healthcheckTokenAuthorized(req),
  );
  if (!originDecision.allowed) {
    return json(req, 403, { ok: false, error: originDecision.error });
  }

  const contentType = req.headers.get("content-type") || "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return json(req, 415, { ok: false, error: "json_required" });
  }

  const bodyText = await req.text();
  if (new TextEncoder().encode(bodyText).length > MAX_BODY_BYTES) {
    return json(req, 413, { ok: false, error: "payload_too_large" });
  }

  let parsedBody: unknown;
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

  const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
  const serviceKey = getServiceKey();
  if (!supabaseUrl || !serviceKey) {
    return json(req, 500, { ok: false, error: "server_not_configured" });
  }

  const salt = getIpHashSalt();
  const allowUnsalted = envFlag("PARKET_ALLOW_UNSALTED_IP_HASH");
  if (!salt && !allowUnsalted) {
    return json(req, 503, { ok: false, error: "ip_hash_salt_required" });
  }

  const supabase = createClient(supabaseUrl, serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  if (body.test_mode === true) {
    return runHealthcheck(req, supabase, salt);
  }

  const requestId = requestIdFromBody(body);
  const ipHash = await ipHashFor(req, salt);
  const userAgent = cleanText(req.headers.get("user-agent"), 500);
  const origin = requestOrigin(req);
  const summary = payloadSummary(body);

  const auditBase = {
    request_id: requestId,
    origin,
    ip_hash: ipHash || null,
    user_agent: userAgent,
    payload_summary: summary,
  };

  const since = new Date(Date.now() - RATE_LIMIT_WINDOW_MS).toISOString();
  if (ipHash) {
    const attemptCount = await recentAuditCount(
      supabase,
      ipHash,
      since,
      null,
      requestId,
      "all_attempts",
    );
    if (attemptCount !== null && attemptCount >= RATE_LIMIT_MAX_ATTEMPTS) {
      return json(req, 429, { ok: false, error: "rate_limited", request_id: requestId });
    }
  }

  if (cleanText(body.website, 200) || cleanText(body.company, 200)) {
    await writeAudit(supabase, { ...auditBase, accepted: false, reason: "honeypot_filled" });
    return json(req, 200, { ok: true, request_id: requestId });
  }

  const oversizedField = firstOversizedLeadField(body);
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

  const task = cleanMultiline(body.task, 3000);
  const contact = cleanText(body.contact, 240);
  if (task.length < 8 || contact.length < 3) {
    await writeAudit(supabase, { ...auditBase, accepted: false, reason: "task_or_contact_required" });
    return json(req, 400, { ok: false, error: "task_or_contact_required", request_id: requestId });
  }

  if (ipHash) {
    const acceptedCount = await recentAuditCount(
      supabase,
      ipHash,
      since,
      true,
      requestId,
      "accepted_attempts",
    );
    if (acceptedCount !== null && acceptedCount >= RATE_LIMIT_MAX_ACCEPTED) {
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
    .from(LEADS_TABLE)
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

  const leadId = cleanText(data?.id, 120);
  const notificationResults = await sendLeadNotifications(lead, leadId, requestId);
  const configuredNotifications = notificationResults.filter((result) => result.configured);
  const failedNotifications = configuredNotifications.filter((result) => !result.ok);
  const notificationState = configuredNotifications.length === 0
    ? "disabled"
    : failedNotifications.length === 0
    ? "sent"
    : "partial_failure";

  if (failedNotifications.length > 0) {
    console.error("parket_public_lead_notification_failed", {
      request_id: requestId,
      channels: failedNotifications.map((result) => ({
        channel: result.channel,
        detail: result.detail,
      })),
    });
  }

  await writeAudit(supabase, {
    ...auditBase,
    accepted: true,
    reason: notificationState === "sent"
      ? "accepted_notified"
      : notificationState === "disabled"
      ? "accepted_notification_disabled"
      : "accepted_notification_failed",
    payload_summary: {
      ...summary,
      notification: {
        state: notificationState,
        channels: notificationResults.map((result) => ({
          channel: result.channel,
          configured: result.configured,
          ok: result.ok,
        })),
      },
    },
  });

  return json(req, 200, {
    ok: true,
    request_id: requestId,
    lead_id: data?.id,
    notification: notificationState,
  });
});
