#!/usr/bin/env python3
"""Check live call conversion markers and the deployed IndexNow ownership key."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import ssl
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from site_settings import load_config
from submit_indexnow import key_location, load_indexnow_config

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "Parket36-Live-Conversion/1.0"
MAX_RESPONSE_BYTES = 2_000_000


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def fetch_text(url: str, timeout: float) -> tuple[int, str, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    context = ssl.create_default_context()
    with urlopen(request, timeout=timeout, context=context) as response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError(f"response is larger than {MAX_RESPONSE_BYTES} bytes")
        return response.status, response.geturl(), body.decode("utf-8", errors="replace")


def marker_result(name: str, text: str, required: tuple[str, ...]) -> CheckResult:
    missing = [marker for marker in required if marker not in text]
    return CheckResult(
        name,
        not missing,
        "all markers found" if not missing else "missing: " + ", ".join(missing),
    )


def exact_result(name: str, actual: str, expected: str) -> CheckResult:
    normalized = actual.strip()
    return CheckResult(
        name,
        normalized == expected,
        "exact content matched" if normalized == expected else f"content mismatch; received {len(normalized)} characters",
    )


def request_result(name: str, url: str, timeout: float) -> tuple[CheckResult, str]:
    try:
        status, final_url, body = fetch_text(url, timeout)
    except HTTPError as exc:
        return CheckResult(name, False, f"HTTP {exc.code}: {exc.reason}"), ""
    except (URLError, TimeoutError, ssl.SSLError, ValueError) as exc:
        return CheckResult(name, False, str(exc)), ""

    return (
        CheckResult(name, status == 200, f"HTTP {status}, final URL: {final_url}"),
        body,
    )


def run_once(timeout: float) -> tuple[str, list[CheckResult]]:
    site = load_config()
    indexnow = load_indexnow_config()
    domain = str(site["domain"]).rstrip("/")
    phone_e164 = str(site["phone_e164"])
    phone_display = str(site["phone_display"])

    results: list[CheckResult] = []
    home_result, home = request_result("Homepage conversion HTTP", domain + "/", timeout)
    results.append(home_result)
    if home_result.ok:
        results.append(
            marker_result(
                "Homepage call route",
                home,
                (
                    f'href="tel:{phone_e164}"',
                    phone_display,
                    "Позвонить Ивану",
                    "Оценка по фото",
                ),
            )
        )

    live_key_url = key_location(domain, indexnow)
    key_http, key_body = request_result("IndexNow key HTTP", live_key_url, timeout)
    results.append(key_http)
    if key_http.ok:
        results.append(exact_result("IndexNow key content", key_body, indexnow["key"]))

    return domain, results


def run_with_retries(timeout: float, attempts: int, retry_delay: float) -> tuple[str, list[CheckResult], int]:
    domain = ""
    results: list[CheckResult] = []
    for attempt in range(1, attempts + 1):
        try:
            domain, results = run_once(timeout)
        except (OSError, ValueError) as exc:
            results = [CheckResult("Live conversion config", False, str(exc))]
        if results and all(result.ok for result in results):
            return domain, results, attempt
        if attempt < attempts and retry_delay:
            time.sleep(retry_delay)
    return domain, results, attempts


def append_report(path: Path, domain: str, results: list[CheckResult], attempts_used: int) -> None:
    generated = datetime.now(timezone.utc).isoformat()
    lines = [
        "",
        "## Live call and IndexNow checks",
        "",
        f"Generated: `{generated}`",
        f"Domain: `{domain or 'unavailable'}`",
        f"Attempts used: `{attempts_used}`",
        "",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
    ]
    for result in results:
        state = "PASS" if result.ok else "FAIL"
        detail = result.detail.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {result.name} | {state} | {detail} |")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    prefix = path.read_text(encoding="utf-8") if path.exists() else "# Parket36 live health report\n"
    path.write_text(prefix.rstrip() + "\n" + "\n".join(lines), encoding="utf-8")


def validate_args(timeout: float, attempts: int, retry_delay: float) -> None:
    if timeout <= 0 or timeout > 120:
        raise ValueError("timeout must be greater than 0 and no more than 120 seconds")
    if attempts < 1 or attempts > 20:
        raise ValueError("attempts must be between 1 and 20")
    if retry_delay < 0 or retry_delay > 120:
        raise ValueError("retry-delay must be between 0 and 120 seconds")


def self_test() -> int:
    passing = marker_result(
        "Homepage call route",
        '<a href="tel:+79009267929">Позвонить Ивану</a><span>8 (900) 926-79-29</span><span>Оценка по фото</span>',
        ('href="tel:+79009267929"', "8 (900) 926-79-29", "Позвонить Ивану", "Оценка по фото"),
    )
    missing = marker_result("Homepage call route", "Позвонить Ивану", ('href="tel:+79009267929"',))
    key_ok = exact_result("IndexNow key content", "abc12345\n", "abc12345")
    key_bad = exact_result("IndexNow key content", "wrong", "abc12345")
    findings: list[str] = []

    if not passing.ok:
        findings.append("complete homepage call markers must pass")
    if missing.ok or 'href="tel:+79009267929"' not in missing.detail:
        findings.append("missing tel href must fail with marker detail")
    if not key_ok.ok or key_bad.ok:
        findings.append("IndexNow key must require exact content")

    try:
        validate_args(20, 6, 10)
    except ValueError as exc:
        findings.append(f"valid runtime arguments were rejected: {exc}")
    for invalid in ((0, 6, 10), (20, 0, 10), (20, 6, -1)):
        try:
            validate_args(*invalid)
        except ValueError:
            continue
        findings.append(f"invalid runtime arguments were accepted: {invalid}")

    if findings:
        print("Live conversion self-test findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("Live conversion self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="live-health-report.md")
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--retry-delay", type=float, default=10.0)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    try:
        validate_args(args.timeout, args.attempts, args.retry_delay)
    except ValueError as exc:
        print(f"Live conversion check failed: {exc}", file=sys.stderr)
        return 1

    domain, results, attempts_used = run_with_retries(args.timeout, args.attempts, args.retry_delay)
    append_report(ROOT / args.report, domain, results, attempts_used)

    for result in results:
        state = "PASS" if result.ok else "FAIL"
        print(f"[{state}] {result.name}: {result.detail}")
    print(f"Report: {args.report}")
    return 0 if results and all(result.ok for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
