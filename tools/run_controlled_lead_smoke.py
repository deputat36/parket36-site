#!/usr/bin/env python3
"""Send one controlled production lead and verify its lead/audit rows without exposing contact data."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import uuid
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from site_settings import load_config

DEFAULT_REPORT = Path("controlled-lead-smoke.md")
HEALTH_HEADER = "x-parket-health-token"
ALLOWED_NOTIFICATION_STATES = {"sent", "disabled", "partial_failure"}


def verifier_endpoint(lead_endpoint: str) -> str:
    suffix = "/functions/v1/parket-public-lead"
    if not lead_endpoint.endswith(suffix):
        raise ValueError("lead endpoint must end with /functions/v1/parket-public-lead")
    return lead_endpoint[: -len(suffix)] + "/functions/v1/parket-lead-verify"


def request_json(
    url: str,
    *,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
) -> tuple[int, dict[str, Any]]:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Parket36-Controlled-Lead-Smoke/1.0",
            **headers,
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            raw = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        status = int(exc.code)
        raw = exc.read().decode("utf-8", errors="replace")
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"request failed: {exc}") from exc

    try:
        parsed = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        parsed = {"raw": raw[:500]}
    return status, parsed if isinstance(parsed, dict) else {"value": parsed}


def new_request_id() -> str:
    run_id = re.sub(r"[^0-9]", "", os.environ.get("GITHUB_RUN_ID", ""))[-20:] or "local"
    attempt = re.sub(r"[^0-9]", "", os.environ.get("GITHUB_RUN_ATTEMPT", ""))[-4:] or "1"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"smoke-{stamp}-{run_id}-{attempt}-{uuid.uuid4().hex[:8]}"[:120]


def validate_lead_response(
    *,
    status: int,
    payload: dict[str, Any],
    request_id: str,
    expected_notification: str,
) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    findings: list[str] = []

    def record(name: str, ok: bool, detail: str) -> None:
        rows.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        if not ok:
            findings.append(f"{name}: {detail}")

    record("lead_http_status", status == 200, f"received {status}; expected 200")
    record("lead_ok", payload.get("ok") is True, f"received {payload.get('ok')!r}; expected true")
    record(
        "request_id",
        payload.get("request_id") == request_id,
        f"received {payload.get('request_id')!r}; expected {request_id}",
    )
    lead_id = str(payload.get("lead_id") or "").strip()
    record("lead_id", bool(lead_id), "present" if lead_id else "missing")
    record("not_duplicate", payload.get("duplicate") is not True, f"duplicate={payload.get('duplicate')!r}")

    notification = str(payload.get("notification") or "unknown")
    valid_state = notification in ALLOWED_NOTIFICATION_STATES
    record("notification_state", valid_state, f"received {notification}")
    if expected_notification == "sent":
        record("notification_expected", notification == "sent", f"received {notification}; expected sent")
    elif expected_notification == "disabled":
        record("notification_expected", notification == "disabled", f"received {notification}; expected disabled")
    else:
        record(
            "notification_expected",
            notification in {"sent", "disabled"},
            f"received {notification}; expected sent or disabled",
        )

    return rows, findings


def validate_verification_response(
    *,
    status: int,
    payload: dict[str, Any],
    request_id: str,
) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    findings: list[str] = []

    def record(name: str, ok: bool, detail: str) -> None:
        rows.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        if not ok:
            findings.append(f"{name}: {detail}")

    record("verify_http_status", status == 200, f"received {status}; expected 200")
    record("verify_ok", payload.get("ok") is True, f"received {payload.get('ok')!r}; expected true")
    record(
        "verify_request_id",
        payload.get("request_id") == request_id,
        f"received {payload.get('request_id')!r}; expected {request_id}",
    )

    checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
    for name in ("parket_leads", "parket_public_lead_audit"):
        check = checks.get(name) if isinstance(checks, dict) else None
        ok = isinstance(check, dict) and check.get("ok") is True
        detail = str(check.get("detail") if isinstance(check, dict) else "missing")[:300]
        record(f"verify_{name}", ok, detail)

    return rows, findings


def render_report(
    *,
    request_id: str,
    expected_notification: str,
    notification: str,
    contact_digits: int,
    rows: list[dict[str, str]],
    findings: list[str],
) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    result = "PASS" if not findings else "FAIL"
    lines = [
        "# Controlled production lead smoke",
        "",
        f"Generated: `{generated}`",
        f"Request ID: `{request_id}`",
        f"Expected notification: `{expected_notification}`",
        f"Received notification: `{notification}`",
        f"Contact digit count: `{contact_digits}`",
        f"Result: **{result}**",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for row in rows:
        detail = row["detail"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{row['check']}` | {row['status']} | {detail} |")
    if findings:
        lines.extend(["", "## Findings", ""])
        lines.extend(f"- {finding}" for finding in findings)
    lines.extend([
        "",
        "The report never contains the contact value or health token.",
        "A PASS confirms the public response plus matching rows in parket_leads and parket_public_lead_audit.",
        "Human confirmation that Ivan actually received the Telegram/email notification is still required.",
        "",
    ])
    return "\n".join(lines)


def run_smoke(report_path: Path, timeout: float, expected_notification: str) -> int:
    contact = os.environ.get("PARKET_SMOKE_CONTACT", "").strip()
    health_token = os.environ.get("PARKET_HEALTHCHECK_TOKEN", "").strip()
    digits = len(re.findall(r"\d", contact))
    if digits < 10 or digits > 15:
        print("PARKET_SMOKE_CONTACT must contain 10-15 digits", file=sys.stderr)
        return 1
    if not health_token:
        print("PARKET_HEALTHCHECK_TOKEN is not configured", file=sys.stderr)
        return 1

    config = load_config()
    endpoint = str(config["lead_endpoint"])
    origin = str(config["domain"])
    verify_endpoint = verifier_endpoint(endpoint)
    request_id = new_request_id()

    lead_payload = {
        "request_id": request_id,
        "service": "Контролируемая проверка production",
        "location": "Воронеж",
        "area": "",
        "photos": "",
        "video": "",
        "task": "Контролируемая проверка production-контура. Не обрабатывать как клиентскую заявку.",
        "callback_time": "Не перезванивать — техническая проверка",
        "contact": contact,
        "page": "/zayavka/",
        "utm_source": "github",
        "utm_medium": "controlled_smoke",
        "utm_campaign": "production_lead_verification",
        "utm_content": "manual_workflow",
        "utm_term": "",
        "website": "",
        "company": "",
    }

    all_rows: list[dict[str, str]] = []
    all_findings: list[str] = []
    notification = "unknown"

    try:
        lead_status, lead_response = request_json(
            endpoint,
            payload=lead_payload,
            headers={
                "Origin": origin,
                "Referer": origin + "/zayavka/",
            },
            timeout=timeout,
        )
        notification = str(lead_response.get("notification") or "unknown")
        rows, findings = validate_lead_response(
            status=lead_status,
            payload=lead_response,
            request_id=request_id,
            expected_notification=expected_notification,
        )
        all_rows.extend(rows)
        all_findings.extend(findings)

        verify_status, verify_response = request_json(
            verify_endpoint,
            payload={"request_id": request_id},
            headers={
                "Origin": origin,
                HEALTH_HEADER: health_token,
            },
            timeout=timeout,
        )
        rows, findings = validate_verification_response(
            status=verify_status,
            payload=verify_response,
            request_id=request_id,
        )
        all_rows.extend(rows)
        all_findings.extend(findings)
    except (RuntimeError, OSError, ValueError) as exc:
        all_findings.append(str(exc))

    report_path.write_text(
        render_report(
            request_id=request_id,
            expected_notification=expected_notification,
            notification=notification,
            contact_digits=digits,
            rows=all_rows,
            findings=all_findings,
        ),
        encoding="utf-8",
    )

    if all_findings:
        print("Controlled lead smoke findings:")
        for finding in all_findings:
            print(f"  - {finding}")
        return 1
    print(f"Controlled lead smoke passed for {request_id}")
    return 0


def self_test() -> int:
    failures: list[str] = []
    request_id = "smoke-20260714120000-local-1-12345678"
    lead_payload = {
        "ok": True,
        "request_id": request_id,
        "lead_id": "lead-123",
        "notification": "sent",
    }
    rows, findings = validate_lead_response(
        status=200,
        payload=lead_payload,
        request_id=request_id,
        expected_notification="sent",
    )
    if findings or len(rows) < 6:
        failures.append("healthy lead response was rejected")

    verify_payload = {
        "ok": True,
        "request_id": request_id,
        "checks": {
            "parket_leads": {"ok": True, "detail": "found"},
            "parket_public_lead_audit": {"ok": True, "detail": "found"},
        },
    }
    verify_rows, verify_findings = validate_verification_response(
        status=200,
        payload=verify_payload,
        request_id=request_id,
    )
    if verify_findings or len(verify_rows) != 5:
        failures.append("healthy verification response was rejected")

    report = render_report(
        request_id=request_id,
        expected_notification="sent",
        notification="sent",
        contact_digits=11,
        rows=rows + verify_rows,
        findings=[],
    )
    secret_contact = "+7 900 000-00-00"
    secret_token = "super-secret-health-token"
    if secret_contact in report or secret_token in report:
        failures.append("report can expose contact or health token")
    for marker in ("parket_leads", "parket_public_lead_audit", "Human confirmation"):
        if marker not in report:
            failures.append(f"report missing marker: {marker}")

    if verifier_endpoint("https://example.supabase.co/functions/v1/parket-public-lead") != (
        "https://example.supabase.co/functions/v1/parket-lead-verify"
    ):
        failures.append("verifier endpoint derivation failed")

    if failures:
        print("Controlled lead smoke self-test failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Controlled lead smoke self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--timeout", type=float, default=25.0)
    parser.add_argument(
        "--expected-notification",
        choices=("sent", "disabled", "any"),
        default="sent",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.timeout <= 0 or args.timeout > 120:
        parser.error("--timeout must be greater than 0 and no more than 120 seconds")
    return run_smoke(Path(args.report), args.timeout, args.expected_notification)


if __name__ == "__main__":
    sys.exit(main())
