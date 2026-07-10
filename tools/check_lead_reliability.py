#!/usr/bin/env python3
"""Validate timeout, retry, honeypot and rate-limit protection for public lead forms."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

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
    "supabase/functions/parket-public-lead/index.ts": {
        "cleanText(body.website": "backend website honeypot",
        "cleanText(body.company": "backend company honeypot",
        'reason: "honeypot_filled"': "honeypot audit reason",
        "RATE_LIMIT_MAX_ATTEMPTS = 30": "all-attempt rate limit",
        "RATE_LIMIT_MAX_ACCEPTED = 6": "accepted-lead rate limit",
        "recentAuditCount(": "shared audit rate counter",
        '"all_attempts"': "all-attempt rate scope",
        '"accepted_attempts"': "accepted rate scope",
        "attemptCount >= RATE_LIMIT_MAX_ATTEMPTS": "all-attempt rejection guard",
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

    if findings:
        print("Lead reliability findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Lead reliability check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
