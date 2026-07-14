#!/usr/bin/env python3
"""Check the deployed lead Edge Function without creating a real lead."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
MAIN_JS = ROOT / "js" / "main.js"
DEFAULT_REPORT = Path("lead-endpoint-health.md")
ENDPOINT_PATTERN = re.compile(
    r"const\s+PARKET_LEAD_ENDPOINT\s*=\s*['\"](?P<url>https://[^'\"]+)['\"]"
)
REQUIRED_CHECKS = (
    "service_role",
    "ip_hash_salt",
    "parket_leads",
    "parket_public_lead_audit",
    "telegram_notification",
    "email_notification",
)


def extract_endpoint(text: str) -> str:
    match = ENDPOINT_PATTERN.search(text)
    if not match:
        raise ValueError("PARKET_LEAD_ENDPOINT is missing from js/main.js")
    endpoint = match.group("url").strip()
    if not endpoint.endswith("/functions/v1/parket-public-lead"):
        raise ValueError("PARKET_LEAD_ENDPOINT must target parket-public-lead")
    return endpoint


def endpoint_from_site() -> str:
    return extract_endpoint(MAIN_JS.read_text(encoding="utf-8"))


def normalize_checks(payload: Any) -> tuple[list[dict[str, str]], list[str]]:
    findings: list[str] = []
    rows: list[dict[str, str]] = []

    if not isinstance(payload, dict):
        return rows, ["response body must be a JSON object"]
    if payload.get("ok") is not True:
        findings.append(f"response ok must be true; received {payload.get('ok')!r}")
    if payload.get("test_mode") is not True:
        findings.append("response test_mode must be true")

    checks = payload.get("checks")
    if not isinstance(checks, dict):
        return rows, findings + ["response checks must be an object"]

    for name in REQUIRED_CHECKS:
        check = checks.get(name)
        if not isinstance(check, dict):
            findings.append(f"missing health check: {name}")
            rows.append({"name": name, "status": "FAIL", "detail": "missing"})
            continue
        ok = check.get("ok") is True
        detail = str(check.get("detail") or "").strip()[:500]
        rows.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        if not ok:
            findings.append(f"{name} is not healthy: {detail or 'no detail'}")

    return rows, findings


def request_health(endpoint: str, token: str, timeout: float) -> tuple[int, Any]:
    request = Request(
        endpoint,
        data=json.dumps({"test_mode": True}).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://parket36.ru",
            "User-Agent": "Parket36-Production-Lead-Health/1.0",
            "x-parket-health-token": token,
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
        raise RuntimeError(f"endpoint request failed: {exc}") from exc

    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {"raw": raw[:500]}
    return status, payload


def markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_report(
    *,
    endpoint: str,
    configured: bool,
    result: str,
    http_status: int | None,
    rows: list[dict[str, str]],
    findings: list[str],
) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Production lead endpoint health",
        "",
        f"Generated: `{generated}`",
        f"Endpoint: `{endpoint}`",
        f"Health token configured in this run: `{'yes' if configured else 'no'}`",
        f"Result: **{result}**",
        f"HTTP status: `{http_status if http_status is not None else 'not requested'}`",
        "",
    ]

    if rows:
        lines.extend([
            "## Checks",
            "",
            "| Check | Status | Detail |",
            "|---|---|---|",
        ])
        for row in rows:
            lines.append(
                f"| `{markdown_cell(row['name'])}` | {row['status']} | {markdown_cell(row['detail'])} |"
            )
        lines.append("")

    if findings:
        lines.extend(["## Findings", ""])
        lines.extend(f"- {finding}" for finding in findings)
        lines.append("")

    lines.extend([
        "The check uses `test_mode: true`. It does not create a lead or an audit row.",
        "The health token is never written to this report.",
        "",
    ])
    return "\n".join(lines)


def write_report(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_check(report_path: Path, timeout: float, require_token: bool) -> int:
    try:
        endpoint = endpoint_from_site()
    except (OSError, ValueError) as exc:
        write_report(
            report_path,
            render_report(
                endpoint="unknown",
                configured=False,
                result="FAIL",
                http_status=None,
                rows=[],
                findings=[str(exc)],
            ),
        )
        print(f"Production lead endpoint findings: {exc}")
        return 1

    token = os.environ.get("PARKET_HEALTHCHECK_TOKEN", "").strip()
    if not token:
        findings = [
            "PARKET_HEALTHCHECK_TOKEN is not available to this workflow run; protected healthcheck skipped."
        ]
        write_report(
            report_path,
            render_report(
                endpoint=endpoint,
                configured=False,
                result="NOT CONFIGURED",
                http_status=None,
                rows=[],
                findings=findings,
            ),
        )
        print("Production lead endpoint health skipped: PARKET_HEALTHCHECK_TOKEN is not configured")
        return 1 if require_token else 0

    try:
        status, payload = request_health(endpoint, token, timeout)
    except RuntimeError as exc:
        write_report(
            report_path,
            render_report(
                endpoint=endpoint,
                configured=True,
                result="FAIL",
                http_status=None,
                rows=[],
                findings=[str(exc)],
            ),
        )
        print(f"Production lead endpoint findings: {exc}")
        return 1

    rows, findings = normalize_checks(payload)
    if status != 200:
        error = payload.get("error") if isinstance(payload, dict) else None
        findings.insert(0, f"expected HTTP 200; received {status}" + (f" ({error})" if error else ""))

    result = "PASS" if not findings else "FAIL"
    write_report(
        report_path,
        render_report(
            endpoint=endpoint,
            configured=True,
            result=result,
            http_status=status,
            rows=rows,
            findings=findings,
        ),
    )

    if findings:
        print("Production lead endpoint findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Production lead endpoint health passed")
    return 0


def self_test() -> int:
    failures: list[str] = []
    sample_endpoint = "https://example.supabase.co/functions/v1/parket-public-lead"
    sample_js = f"const PARKET_LEAD_ENDPOINT = '{sample_endpoint}';"
    if extract_endpoint(sample_js) != sample_endpoint:
        failures.append("endpoint extraction failed")

    healthy_payload = {
        "ok": True,
        "test_mode": True,
        "checks": {
            name: {"ok": True, "detail": "configured"}
            for name in REQUIRED_CHECKS
        },
    }
    rows, findings = normalize_checks(healthy_payload)
    if findings or len(rows) != len(REQUIRED_CHECKS):
        failures.append("healthy response validation failed")

    broken_payload = json.loads(json.dumps(healthy_payload))
    broken_payload["checks"]["parket_leads"] = {"ok": False, "detail": "db_error"}
    _, broken_findings = normalize_checks(broken_payload)
    if not any("parket_leads" in finding for finding in broken_findings):
        failures.append("unhealthy table was not detected")

    secret = "super-secret-health-token-value"
    report = render_report(
        endpoint=sample_endpoint,
        configured=True,
        result="PASS",
        http_status=200,
        rows=rows,
        findings=[],
    )
    if secret in report or "x-parket-health-token" in report:
        failures.append("report can expose the health token")
    for marker in ("test_mode: true", "parket_leads", "parket_public_lead_audit"):
        if marker not in report:
            failures.append(f"report missing marker: {marker}")

    try:
        extract_endpoint("const OTHER = 'x';")
        failures.append("missing endpoint was accepted")
    except ValueError:
        pass

    if failures:
        print("Production lead endpoint self-test failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("Production lead endpoint self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--require-token", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.timeout <= 0 or args.timeout > 120:
        parser.error("--timeout must be greater than 0 and no more than 120 seconds")
    return run_check(Path(args.report), args.timeout, args.require_token)


if __name__ == "__main__":
    sys.exit(main())
