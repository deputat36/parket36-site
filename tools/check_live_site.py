#!/usr/bin/env python3
"""Check Parket36 DNS, GitHub Pages routing, HTTPS, robots and sitemap."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import socket
import ssl
import sys
from tempfile import TemporaryDirectory
import time
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from site_settings import load_config

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "Parket36-Live-Health/1.1"
DEFAULT_TIMEOUT = 20.0
MAX_RESPONSE_BYTES = 2_000_000
MIN_SITEMAP_URLS = 20
GITHUB_PAGES_IPV4 = frozenset(
    {
        "185.199.108.153",
        "185.199.109.153",
        "185.199.110.153",
        "185.199.111.153",
    }
)
GITHUB_PAGES_IPV6 = frozenset(
    {
        "2606:50c0:8000::153",
        "2606:50c0:8001::153",
        "2606:50c0:8002::153",
        "2606:50c0:8003::153",
    }
)
GITHUB_PAGES_ADDRESSES = GITHUB_PAGES_IPV4 | GITHUB_PAGES_IPV6


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def request_url(url: str, check: str, attempt: int, nonce: int | None = None) -> str:
    """Return a unique request URL while preserving the public resource path."""
    token = time.time_ns() if nonce is None else nonce
    parsed = urlsplit(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update(
        {
            "verify_live_health": str(token),
            "check": check,
            "attempt": str(attempt),
        }
    )
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))


def public_url(url: str) -> str:
    """Remove cache-busting query data from diagnostic output."""
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def fetch_text(url: str, timeout: float) -> tuple[int, str, str]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Cache-Control": "no-cache, no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )
    context = ssl.create_default_context()
    with urlopen(request, timeout=timeout, context=context) as response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError(f"response is larger than {MAX_RESPONSE_BYTES} bytes")
        return response.status, response.geturl(), body.decode("utf-8", errors="replace")


def normalize_address(value: str) -> str:
    return value.split("%", 1)[0].lower()


def evaluate_github_pages_dns(
    name: str,
    addresses: set[str],
    *,
    require_all_ipv4: bool,
) -> CheckResult:
    normalized = {normalize_address(address) for address in addresses if address}
    if not normalized:
        return CheckResult(name, False, "no addresses returned")

    unexpected = normalized - GITHUB_PAGES_ADDRESSES
    known = normalized & GITHUB_PAGES_ADDRESSES
    missing_ipv4 = GITHUB_PAGES_IPV4 - normalized if require_all_ipv4 else set()

    findings: list[str] = ["resolved: " + ", ".join(sorted(normalized))]
    if missing_ipv4:
        findings.append("missing GitHub Pages IPv4: " + ", ".join(sorted(missing_ipv4)))
    if unexpected:
        findings.append("unexpected addresses: " + ", ".join(sorted(unexpected)))
    if not known:
        findings.append("no GitHub Pages address found")

    ok = bool(known) and not missing_ipv4 and not unexpected
    return CheckResult(name, ok, "; ".join(findings))


def resolve_addresses(host: str) -> set[str]:
    records = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    return {record[4][0] for record in records}


def dns_check(name: str, host: str, *, require_all_ipv4: bool) -> CheckResult:
    try:
        addresses = resolve_addresses(host)
    except socket.gaierror as exc:
        return CheckResult(name, False, str(exc))
    return evaluate_github_pages_dns(name, addresses, require_all_ipv4=require_all_ipv4)


def http_check(name: str, url: str, timeout: float, attempt: int) -> tuple[CheckResult, str]:
    try:
        status, final_url, text = fetch_text(url, timeout)
    except HTTPError as exc:
        return CheckResult(name, False, f"HTTP {exc.code}: {exc.reason}; cache_bust_attempt={attempt}"), ""
    except (URLError, TimeoutError, ssl.SSLError, ValueError) as exc:
        return CheckResult(name, False, f"{exc}; cache_bust_attempt={attempt}"), ""

    detail = f"HTTP {status}, final URL: {public_url(final_url)}; cache_bust_attempt={attempt}"
    if status != 200:
        return CheckResult(name, False, detail), text
    return CheckResult(name, True, detail), text


def www_redirect_check(www_url: str, expected_domain: str, timeout: float, attempt: int) -> CheckResult:
    try:
        status, final_url, _ = fetch_text(www_url, timeout)
    except HTTPError as exc:
        return CheckResult(
            "www HTTPS redirect",
            False,
            f"HTTP {exc.code}: {exc.reason}; cache_bust_attempt={attempt}",
        )
    except (URLError, TimeoutError, ssl.SSLError, ValueError) as exc:
        return CheckResult("www HTTPS redirect", False, f"{exc}; cache_bust_attempt={attempt}")

    final = urlsplit(final_url)
    expected = urlsplit(expected_domain)
    correct_origin = final.scheme == "https" and final.hostname == expected.hostname
    correct_path = (final.path or "/") == "/"
    ok = status == 200 and correct_origin and correct_path
    detail = f"HTTP {status}, final URL: {public_url(final_url)}; cache_bust_attempt={attempt}"
    if not correct_origin:
        detail += f"; expected HTTPS host {expected.hostname}"
    if not correct_path:
        detail += "; expected root path /"
    return CheckResult("www HTTPS redirect", ok, detail)


def homepage_content_results(home: str, phone_display: str) -> list[CheckResult]:
    required_markers = ["Паркет36", phone_display, "Оценка по фото"]
    missing = [marker for marker in required_markers if marker not in home]
    forbidden = [marker for marker in ("WhatsApp", "wa.me") if marker in home]
    return [
        CheckResult(
            "Homepage markers",
            not missing,
            "all markers found" if not missing else "missing: " + ", ".join(missing),
        ),
        CheckResult(
            "Legacy WhatsApp",
            not forbidden,
            "not present" if not forbidden else "found: " + ", ".join(forbidden),
        ),
    ]


def robots_content_result(robots: str, domain: str, host: str) -> CheckResult:
    expected_sitemap = f"Sitemap: {domain}/sitemap.xml"
    expected_host = f"Host: {host}"
    missing = [marker for marker in (expected_sitemap, expected_host) if marker not in robots]
    return CheckResult(
        "robots.txt markers",
        not missing,
        "all markers found" if not missing else "missing: " + ", ".join(missing),
    )


def sitemap_content_result(sitemap: str, domain: str) -> CheckResult:
    try:
        root = ET.fromstring(sitemap)
    except ET.ParseError as exc:
        return CheckResult("Sitemap content", False, f"invalid XML: {exc}")

    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = [(node.text or "").strip() for node in root.findall("sm:url/sm:loc", namespace)]
    bad_domains = [url for url in locations if not url.startswith(domain + "/")]
    sitemap_ok = len(locations) >= MIN_SITEMAP_URLS and not bad_domains
    detail_parts = [f"URLs: {len(locations)}"]
    if bad_domains:
        detail_parts.append(f"wrong domain URLs: {len(bad_domains)}")
    if len(locations) < MIN_SITEMAP_URLS:
        detail_parts.append(f"minimum expected: {MIN_SITEMAP_URLS}")
    return CheckResult("Sitemap content", sitemap_ok, "; ".join(detail_parts))


def run_http_once(
    domain: str,
    host: str,
    phone_display: str,
    timeout: float,
    attempt: int,
) -> list[CheckResult]:
    results: list[CheckResult] = []

    home_url = request_url(domain + "/", "homepage", attempt)
    home_result, home = http_check("Homepage HTTPS", home_url, timeout, attempt)
    results.append(home_result)
    if home_result.ok:
        results.extend(homepage_content_results(home, phone_display))

    www_url = request_url(f"https://www.{host}/", "www_redirect", attempt)
    results.append(www_redirect_check(www_url, domain, timeout, attempt))

    robots_url = request_url(domain + "/robots.txt", "robots", attempt)
    robots_result, robots = http_check("robots.txt", robots_url, timeout, attempt)
    results.append(robots_result)
    if robots_result.ok:
        results.append(robots_content_result(robots, domain, host))

    sitemap_url = request_url(domain + "/sitemap.xml", "sitemap", attempt)
    sitemap_result, sitemap = http_check("sitemap.xml", sitemap_url, timeout, attempt)
    results.append(sitemap_result)
    if sitemap_result.ok:
        results.append(sitemap_content_result(sitemap, domain))

    return results


def run_http_with_retries(
    domain: str,
    host: str,
    phone_display: str,
    timeout: float,
    attempts: int,
    retry_delay: float,
) -> tuple[list[CheckResult], int]:
    results: list[CheckResult] = []
    for attempt in range(1, attempts + 1):
        results = run_http_once(domain, host, phone_display, timeout, attempt)
        if results and all(result.ok for result in results):
            return results, attempt
        if attempt < attempts and retry_delay:
            time.sleep(retry_delay)
    return results, attempts


def write_report(path: Path, domain: str, results: list[CheckResult], attempts_used: int) -> None:
    generated = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Parket36 live health report",
        "",
        f"Generated: `{generated}`",
        f"Domain: `{domain}`",
        f"HTTP attempts used: `{attempts_used}`",
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
    path.write_text("\n".join(lines), encoding="utf-8")


def validate_args(timeout: float, attempts: int, retry_delay: float) -> None:
    if timeout <= 0 or timeout > 120:
        raise ValueError("timeout must be greater than 0 and no more than 120 seconds")
    if attempts < 1 or attempts > 20:
        raise ValueError("attempts must be between 1 and 20")
    if retry_delay < 0 or retry_delay > 120:
        raise ValueError("retry-delay must be between 0 and 120 seconds")


def self_test() -> int:
    passing_apex = evaluate_github_pages_dns(
        "DNS apex GitHub Pages",
        set(GITHUB_PAGES_IPV4) | {"2606:50c0:8000::153"},
        require_all_ipv4=True,
    )
    passing_www = evaluate_github_pages_dns(
        "DNS www GitHub Pages",
        {"185.199.108.153"},
        require_all_ipv4=False,
    )
    missing_apex = evaluate_github_pages_dns(
        "Missing apex record",
        set(GITHUB_PAGES_IPV4) - {"185.199.111.153"},
        require_all_ipv4=True,
    )
    wrong_host = evaluate_github_pages_dns(
        "Old hosting",
        {"203.0.113.10"},
        require_all_ipv4=False,
    )
    escaped = CheckResult("Escaping", False, "line one|line two\nline three")
    results = [passing_apex, passing_www, missing_apex, wrong_host, escaped]

    cache_busted = request_url("https://example.test/robots.txt", "robots", 3, nonce=123456)
    findings: list[str] = []
    for marker in (
        "https://example.test/robots.txt?",
        "verify_live_health=123456",
        "check=robots",
        "attempt=3",
    ):
        if marker not in cache_busted:
            findings.append(f"cache-busted URL missing marker: {marker}")
    if public_url(cache_busted) != "https://example.test/robots.txt":
        findings.append("public URL must omit cache-busting query data")

    if not passing_apex.ok:
        findings.append("complete GitHub Pages apex records must pass")
    if not passing_www.ok:
        findings.append("a www host resolving to GitHub Pages must pass")
    if missing_apex.ok or "missing GitHub Pages IPv4" not in missing_apex.detail:
        findings.append("an incomplete apex record set must fail with missing-address detail")
    if wrong_host.ok or "unexpected addresses" not in wrong_host.detail:
        findings.append("an old-hosting address must fail with unexpected-address detail")

    for valid in ((20, 1, 0), (20, 6, 10)):
        try:
            validate_args(*valid)
        except ValueError as exc:
            findings.append(f"valid arguments rejected: {valid}: {exc}")
    for invalid in ((0, 1, 0), (20, 0, 0), (20, 1, -1)):
        try:
            validate_args(*invalid)
        except ValueError:
            continue
        findings.append(f"invalid arguments accepted: {invalid}")

    with TemporaryDirectory() as temporary:
        report = Path(temporary) / "report.md"
        write_report(report, "https://example.test", results, attempts_used=3)
        text = report.read_text(encoding="utf-8")

    required = [
        "# Parket36 live health report",
        "Domain: `https://example.test`",
        "HTTP attempts used: `3`",
        "| DNS apex GitHub Pages | PASS |",
        "| DNS www GitHub Pages | PASS |",
        "| Missing apex record | FAIL |",
        "| Old hosting | FAIL |",
        "| Escaping | FAIL | line one\\|line two line three |",
    ]
    findings.extend(f"missing report marker: {marker}" for marker in required if marker not in text)
    if "verify_live_health" in text or "123456" in text:
        findings.append("report must not expose cache-busting query data")

    if findings:
        print("Live health self-test failed:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Live health self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="live-health-report.md")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--retry-delay", type=float, default=10.0)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    try:
        validate_args(args.timeout, args.attempts, args.retry_delay)
        config = load_config()
        domain = str(config["domain"]).rstrip("/")
        phone_display = str(config["phone_display"])
    except (OSError, ValueError, KeyError) as exc:
        print(f"Live health check failed: {exc}", file=sys.stderr)
        return 1

    parsed = urlsplit(domain)
    host = parsed.hostname or ""
    results: list[CheckResult] = []
    if parsed.scheme != "https" or not host:
        results.append(CheckResult("Domain config", False, f"invalid HTTPS domain: {domain}"))
        write_report(ROOT / args.report, domain, results, attempts_used=0)
        return 1

    www_host = f"www.{host}"
    results.append(dns_check("DNS apex GitHub Pages", host, require_all_ipv4=True))
    results.append(dns_check("DNS www GitHub Pages", www_host, require_all_ipv4=False))

    http_results, attempts_used = run_http_with_retries(
        domain,
        host,
        phone_display,
        args.timeout,
        args.attempts,
        args.retry_delay,
    )
    results.extend(http_results)

    report_path = ROOT / args.report
    write_report(report_path, domain, results, attempts_used)

    for result in results:
        state = "PASS" if result.ok else "FAIL"
        print(f"[{state}] {result.name}: {result.detail}")
    print(f"HTTP attempts used: {attempts_used}")
    print(f"Report: {report_path.relative_to(ROOT)}")

    return 0 if results and all(result.ok for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
