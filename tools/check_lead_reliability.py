#!/usr/bin/env python3
"""Validate public lead timeout, anti-spam, secrets, notifications and healthchecks."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EDGE_FUNCTION = "supabase/functions/parket-public-lead/index.ts"

FILES = {
    "js/lead-reliability.js": {
        "LEAD_TIMEOUT_MS = 12_000": "lead request timeout",
        "LEAD_MAX_ATTEMPTS = 2": "single retry limit",
        "new AbortController()": "abortable lead request",
        "payload.website": "website honeypot payload",
        "payload.company": "company honeypot payload",
        "response.status < 500": "retry decision for server failures",
        "window.fetch = async": "lead fetch wrapper",
        "data-lead-honeypot": "hidden honeypot fields",
    },
    "tools/build_pages.py": {
        'LEAD_RELIABILITY_SCRIPT = \'<script src="/js/lead-reliability.js" defer></script>\'': "build script tag",
        "inject_lead_reliability(errors)": "build injection call",
        'if \'id="request-form"\' not in text': "form-only injection guard",
    },
    EDGE_FUNCTION: {
        "cleanText(body.website": "backend website honeypot",
        "cleanText(body.company": "backend company honeypot",
        'reason: "honeypot_filled"': "honeypot audit reason",
        "RATE_LIMIT_MAX_ATTEMPTS = 30": "all-attempt rate limit",
        "RATE_LIMIT_MAX_ACCEPTED = 6": "accepted-lead rate limit",
        "recentAuditCount(": "shared audit rate counter",
        '"all_attempts"': "all-attempt rate scope",
        '"accepted_attempts"': "accepted rate scope",
        "attemptCount >= RATE_LIMIT_MAX_ATTEMPTS": "all-attempt rejection guard",
        'HEALTHCHECK_HEADER = "x-parket-health-token"': "protected healthcheck header",
        'Deno.env.get("PARKET_IP_HASH_SALT")': "IP hash salt environment variable",
        'envFlag("PARKET_ALLOW_UNSALTED_IP_HASH")': "explicit local unsalted override",
        'error: "ip_hash_salt_required"': "missing salt rejection",
        'Deno.env.get("PARKET_HEALTHCHECK_TOKEN")': "healthcheck token environment variable",
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
            if min(insert_position, notify_position, success_position) == -1:
                findings.append("Edge Function: cannot verify insert-notify-success order")
            elif not (insert_position < notify_position < success_position):
                findings.append("Edge Function: lead must be stored before notification and success response")

    if findings:
        print("Lead reliability findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Lead reliability check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
