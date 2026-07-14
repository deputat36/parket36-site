#!/usr/bin/env python3
"""Check the public CORS preflight of the production lead endpoint without secrets or leads."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from site_settings import load_config

DEFAULT_REPORT = Path("lead-endpoint-preflight.md")
REQUIRED_METHODS = {"POST", "OPTIONS"}
REQUIRED_HEADERS = {"content-type", "x-parket-health-token"}


def split_header_values(value: str) -> set[str]:
    return {item.strip().lower() for item in value.split(",") if item.strip()}


def request_preflight(endpoint: str, origin: str, timeout: float) -> tuple[int, dict[str, str], str]:
    request = Request(
        endpoint,
        method="OPTIONS",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type, x-parket-health-token",
            "User-Agent": "Parket36-Public-Lead-Preflight/1.1",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            headers = {key.lower(): value for key, value in response.headers.items()}
            body = response.read().decode("utf-8", errors="replace")[:500]
    except HTTPError as exc:
        status = int(exc.code)
        headers = {key.lower(): value for key, value in exc.headers.items()}
        body = exc.read().decode("utf-8", errors="replace")[:500]
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"preflight request failed: {exc}") from exc
    return status, headers, body


def validate_preflight(
    *,
    status: int,
    headers: Mapping[str, str],
    origin: str,
) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    findings: list[str] = []

    def record(name: str, ok: bool, detail: str) -> None:
        rows.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        if not ok:
            findings.append(f"{name}: {detail}")

    record("http_status", status in {200, 204}, f"received {status}; expected 200 or 204")

    allow_origin = headers.get("access-control-allow-origin", "").strip()
    record(
        "allow_origin",
        allow_origin == origin,
        f"received {allow_origin or 'missing'}; expected {origin}",
    )

    methods = {value.upper() for value in split_header_values(headers.get("access-control-allow-methods", ""))}
    missing_methods = sorted(REQUIRED_METHODS - methods)
    record(
        "allow_methods",
        not missing_methods,
        "configured: " + (", ".join(sorted(methods)) if methods else "missing")
        + (f"; missing: {', '.join(missing_methods)}" if missing_methods else ""),
    )

    allowed_headers = split_header_values(headers.get("access-control-allow-headers", ""))
    missing_headers = sorted(REQUIRED_HEADERS - allowed_headers)
    record(
        "allow_headers",
        not missing_headers,
        "configured: " + (", ".join(sorted(allowed_headers)) if allowed_headers else "missing")
        + (f"; missing: {', '.join(missing_headers)}" if missing_headers else ""),
    )

    vary = split_header_values(headers.get("vary", ""))
    record("vary_origin", "origin" in vary, f"received {headers.get('vary', 'missing')}")

    return rows, findings


def markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_report(
    *,
    endpoint: str,
    origin: str,
    result: str,
    http_status: int | None,
    rows: list[dict[str, str]],
    findings: list[str],
) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Public lead endpoint preflight",
        "",
        f"Generated: `{generated}`",
        f"Endpoint: `{endpoint}`",
        f"Origin: `{origin}`",
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
        "The request uses HTTP OPTIONS only. It does not send form data, create a lead or require a secret.",
        "A PASS confirms public routing, the browser CORS contract and the health-token header advertised by the current GitHub function source.",
        "It does not confirm database or notification readiness.",
        "",
    ])
    return "\n".join(lines)


def write_report(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_check(report_path: Path, timeout: float) -> int:
    try:
        config = load_config()
        endpoint = str(config["lead_endpoint"])
        origin = str(config["domain"])
    except (OSError, ValueError) as exc:
        write_report(
            report_path,
            render_report(
                endpoint="unknown",
                origin="unknown",
                result="FAIL",
                http_status=None,
                rows=[],
                findings=[str(exc)],
            ),
        )
        print(f"Public lead preflight findings: {exc}")
        return 1

    try:
        status, headers, _ = request_preflight(endpoint, origin, timeout)
    except RuntimeError as exc:
        write_report(
            report_path,
            render_report(
                endpoint=endpoint,
                origin=origin,
                result="FAIL",
                http_status=None,
                rows=[],
                findings=[str(exc)],
            ),
        )
        print(f"Public lead preflight findings: {exc}")
        return 1

    rows, findings = validate_preflight(status=status, headers=headers, origin=origin)
    result = "PASS" if not findings else "FAIL"
    write_report(
        report_path,
        render_report(
            endpoint=endpoint,
            origin=origin,
            result=result,
            http_status=status,
            rows=rows,
            findings=findings,
        ),
    )
    if findings:
        print("Public lead preflight findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("Public lead endpoint preflight passed")
    return 0


def self_test() -> int:
    failures: list[str] = []
    origin = "https://parket36.ru"
    healthy_headers = {
        "access-control-allow-origin": origin,
        "access-control-allow-methods": "POST, OPTIONS",
        "access-control-allow-headers": "authorization, content-type, x-parket-health-token",
        "vary": "Origin",
    }
    rows, findings = validate_preflight(status=200, headers=healthy_headers, origin=origin)
    if findings or len(rows) != 5:
        failures.append("healthy preflight validation failed")

    broken_headers = dict(healthy_headers)
    broken_headers["access-control-allow-origin"] = "https://example.test"
    broken_headers["access-control-allow-methods"] = "OPTIONS"
    broken_headers["access-control-allow-headers"] = "authorization, content-type"
    _, broken_findings = validate_preflight(status=200, headers=broken_headers, origin=origin)
    if not any("allow_origin" in finding for finding in broken_findings):
        failures.append("wrong origin was not detected")
    if not any("allow_methods" in finding for finding in broken_findings):
        failures.append("missing POST method was not detected")
    if not any("x-parket-health-token" in finding for finding in broken_findings):
        failures.append("stale function contract was not detected")

    report = render_report(
        endpoint="https://example.supabase.co/functions/v1/parket-public-lead",
        origin=origin,
        result="PASS",
        http_status=200,
        rows=rows,
        findings=[],
    )
    for marker in ("HTTP OPTIONS only", "does not send form data", "current GitHub function source"):
        if marker not in report:
            failures.append(f"report missing marker: {marker}")

    if failures:
        print("Public lead preflight self-test failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Public lead preflight self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.timeout <= 0 or args.timeout > 120:
        parser.error("--timeout must be greater than 0 and no more than 120 seconds")
    return run_check(Path(args.report), args.timeout)


if __name__ == "__main__":
    sys.exit(main())
