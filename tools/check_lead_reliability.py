#!/usr/bin/env python3
"""Validate public lead timeout, anti-spam, form state, limits, origin policy, secrets, notifications and healthchecks."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EDGE_FUNCTION = "supabase/functions/parket-public-lead/index.ts"
FIELD_LIMITS = "supabase/functions/parket-public-lead/field-limits.ts"
FIELD_LIMITS_TEST = "supabase/functions/parket-public-lead/field-limits_test.ts"
ORIGIN_POLICY = "supabase/functions/parket-public-lead/origin-policy.ts"
ORIGIN_POLICY_TEST = "supabase/functions/parket-public-lead/origin-policy_test.ts"
DENO_FIELD_TEST = "deno test supabase/functions/parket-public-lead/field-limits_test.ts"
DENO_ORIGIN_TEST = "deno test supabase/functions/parket-public-lead/origin-policy_test.ts"

FILES = {
    "js/lead-reliability.js": {
        "LEAD_TIMEOUT_MS = 12_000": "lead request timeout",
        "LEAD_MAX_ATTEMPTS = 2": "single retry limit",
        "SUBMISSION_STATE_TIMEOUT_MS": "submission state safety timeout",
        "LEAD_FIELD_LIMITS = Object.freeze": "client field limit map",
        "LEAD_FIELD_LABELS = Object.freeze": "server field label map",
        "LEAD_FIELD_SELECTORS = Object.freeze": "server field selector map",
        "'request-location': 160": "location length limit",
        "'request-area': 80": "area length limit",
        "'request-task': 3000": "task length limit",
        "'request-callback': 160": "callback length limit",
        "'request-contact': 240": "contact length limit",
        "setupLeadFieldLimits": "lead field limit initializer",
        "data-lead-character-counter": "task character counter",
        "aria-describedby": "task counter relationship",
        "leadErrorMessage": "specific lead error messages",
        "readLeadError": "structured response error parser",
        "response.clone().json()": "non-destructive response parsing",
        "parket36:lead-error": "lead error browser event",
        "field_too_long": "oversized field feedback",
        "rate_limited": "rate limit feedback",
        "Подождите 15 минут": "rate limit wait guidance",
        "dispatchLeadError": "lead error dispatcher",
        "network_error": "network failure feedback",
        "new AbortController()": "abortable lead request",
        "payload.website": "website honeypot payload",
        "payload.company": "company honeypot payload",
        "response.status < 500": "retry decision for server failures",
        "window.fetch = async": "lead fetch wrapper",
        "data-lead-honeypot": "hidden honeypot fields",
        "setupLeadFormState": "lead form state initializer",
        "submissionInFlight": "duplicate submission guard",
        "event.stopImmediatePropagation()": "duplicate submit event stop",
        "aria-busy": "form busy state",
        "aria-live": "polite form status announcements",
        "aria-atomic": "atomic form status announcements",
        "aria-invalid": "invalid field state",
        "MutationObserver": "submission completion observer",
    },
    "tests/e2e/site-smoke.spec.mjs": {
        "422 показывает конкретное поле без повторной отправки": "oversized field browser scenario",
        "429 предлагает подождать без повторной отправки": "rate limit browser scenario",
        "error: 'field_too_long'": "oversized field response fixture",
        "error: 'rate_limited'": "rate limit response fixture",
        "expect(attempts).toBe(1)": "non-retry assertion for client errors",
    },
    "tools/build_pages.py": {
        'LEAD_RELIABILITY_SCRIPT = \'<script src="/js/lead-reliability.js" defer></script>\'': "build script tag",
        "inject_lead_reliability(errors)": "build injection call",
        'if \'id="request-form"\' not in text': "form-only injection guard",
    },
    FIELD_LIMITS: {
        "LEAD_FIELD_LIMITS = Object.freeze": "server field limit map",
        "location: 160": "server location limit",
        "area: 80": "server area limit",
        "task: 3000": "server task limit",
        "callback_time: 160": "server callback limit",
        "contact: 240": "server contact limit",
        "firstOversizedLeadField": "server oversized field detector",
        "received > limit": "server length comparison",
    },
    FIELD_LIMITS_TEST: {
        'Deno.test("lead field limits match public form contract"': "field limit contract test",
        'Deno.test("firstOversizedLeadField accepts exact limits"': "exact limit test",
        'Deno.test("firstOversizedLeadField reports field, limit and received length"': "oversized field test",
        'task: "т".repeat(3001)': "task overflow fixture",
    },
    ORIGIN_POLICY: {
        "evaluateOriginPolicy": "pure origin policy evaluator",
        'error: "origin_required"': "missing origin decision",
        'error: "origin_not_allowed"': "unknown origin decision",
        'reason: "healthcheck_token"': "token-authorized healthcheck decision",
        "allowedOrigins.includes(normalizedOrigin)": "configured origin allow-list",
    },
    ORIGIN_POLICY_TEST: {
        'Deno.test("origin policy accepts configured browser origin"': "allowed origin test",
        'Deno.test("origin policy rejects unknown browser origin"': "unknown origin test",
        'Deno.test("origin policy rejects missing origin for normal requests"': "missing origin test",
        'Deno.test("origin policy permits token-authorized healthcheck without origin"': "healthcheck exception test",
    },
    ".github/workflows/site-quality.yml": {
        DENO_FIELD_TEST: "field limit unit test in pull request CI",
        DENO_ORIGIN_TEST: "origin policy unit test in pull request CI",
    },
    ".github/workflows/pages.yml": {
        DENO_FIELD_TEST: "field limit unit test before deploy",
        DENO_ORIGIN_TEST: "origin policy unit test before deploy",
    },
    EDGE_FUNCTION: {
        'import { evaluateOriginPolicy } from "./origin-policy.ts";': "origin policy import",
        "healthcheckTokenAuthorized(req)": "protected no-origin healthcheck exception",
        "const originDecision = evaluateOriginPolicy(": "origin policy evaluation",
        "error: originDecision.error": "specific origin rejection response",
        'import { firstOversizedLeadField } from "./field-limits.ts";': "field limit validator import",
        "const oversizedField = firstOversizedLeadField(body)": "server length validation call",
        'reason: "field_too_long"': "field length audit reason",
        'error: "field_too_long"': "field length response error",
        "return json(req, 422": "unprocessable field length response",
        "cleanText(body.website": "backend website honeypot",
        "cleanText(body.company": "backend company honeypot",
        'reason: "honeypot_filled"': "honeypot audit reason",
        "cleanText(body.location, 160)": "backend location length limit",
        "cleanText(body.area, 80)": "backend area length limit",
        "cleanMultiline(body.task, 3000)": "backend task length limit",
        "cleanText(body.callback_time, 160)": "backend callback length limit",
        "cleanText(body.contact, 240)": "backend contact length limit",
        "RATE_LIMIT_MAX_ATTEMPTS = 30": "all-attempt rate limit",
        "RATE_LIMIT_MAX_ACCEPTED = 6": "accepted-lead rate limit",
        "recentAuditCount(": "shared audit rate counter",
        '"all_attempts"': "all-attempt rate scope",
        '"accepted_attempts"': "accepted rate scope",
        "attemptCount >= RATE_LIMIT_MAX_ATTEMPTS": "all-attempt rejection guard",
        'HEALTHCHECK_HEADER = "x-parket-health-token"': "protected healthcheck header",
        'envText("PARKET_IP_HASH_SALT"': "IP hash salt environment variable",
        'envFlag("PARKET_ALLOW_UNSALTED_IP_HASH")': "explicit local unsalted override",
        'error: "ip_hash_salt_required"': "missing salt rejection",
        'envText("PARKET_HEALTHCHECK_TOKEN"': "healthcheck token environment variable",
        'body.test_mode === true': "non-writing test mode",
        "runHealthcheck(req, supabase, salt)": "healthcheck execution",
        'error: "healthcheck_forbidden"': "invalid healthcheck token rejection",
        '.select("id", { count: "exact", head: true })': "read-only table health query",
        "NOTIFICATION_TIMEOUT_MS = 4_000": "notification timeout",
        'envText("PARKET_TELEGRAM_BOT_TOKEN"': "Telegram bot token environment variable",
        'envText("PARKET_TELEGRAM_CHAT_ID"': "Telegram chat environment variable",
        'envText("PARKET_RESEND_API_KEY"': "Resend API key environment variable",
        'envText("PARKET_EMAIL_FROM"': "email sender environment variable",
        'Deno.env.get("PARKET_EMAIL_TO")': "email recipient environment variable",
        "notificationConfigHealth()": "notification configuration healthcheck",
        "sendTelegramNotification(": "Telegram notification adapter",
        "sendEmailNotification(": "email notification adapter",
        "sendLeadNotifications(": "combined notification dispatcher",
        "Promise.all([": "parallel notification delivery",
        'reason: notificationState === "sent"': "notification-aware audit status",
        '"accepted_notification_failed"': "notification failure audit reason",
        'notification: notificationState': "client-safe notification status",
        "parket_public_lead_notification_failed": "notification failure logging",
    },
}

FORBIDDEN_MARKERS = {
    EDGE_FUNCTION: {
        'if (!origin) return true;': "allowing normal requests without Origin",
        "function isAllowedOrigin": "legacy permissive origin helper",
        'const salt = Deno.env.get("PARKET_IP_HASH_SALT") || "";': "silent empty salt fallback",
        "PARKET_TELEGRAM_BOT_TOKEN =": "hard-coded Telegram token",
        "PARKET_RESEND_API_KEY =": "hard-coded email API key",
    },
}


def main() -> int:
    findings: list[str] = []

    for relative, markers in FILES.items():
        path = ROOT / relative
        if not path.exists():
            findings.append(f"missing file: {relative}")
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker, label in markers.items():
            if marker not in text:
                findings.append(f"{relative}: missing {label}: {marker}")

        for marker, label in FORBIDDEN_MARKERS.get(relative, {}).items():
            if marker in text:
                findings.append(f"{relative}: forbidden {label}: {marker}")

        if relative == EDGE_FUNCTION:
            insert_position = text.find(".insert(lead)")
            notify_position = text.find("const notificationResults = await sendLeadNotifications(")
            success_position = text.rfind("return json(req, 200")
            length_position = text.find("const oversizedField = firstOversizedLeadField(body)")
            task_position = text.find("const task = cleanMultiline(body.task, 3000)")
            origin_position = text.find("const originDecision = evaluateOriginPolicy(")
            body_position = text.find("const bodyText = await req.text()")
            if min(insert_position, notify_position, success_position) == -1:
                findings.append("Edge Function: cannot verify insert-notify-success order")
            elif not (insert_position < notify_position < success_position):
                findings.append("Edge Function: lead must be stored before notification and success response")
            if min(length_position, task_position) == -1 or length_position >= task_position:
                findings.append("Edge Function: field length validation must run before truncating cleaners")
            if min(origin_position, body_position) == -1 or origin_position >= body_position:
                findings.append("Edge Function: origin policy must run before reading the request body")

    if findings:
        print("Lead reliability findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Lead reliability check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())