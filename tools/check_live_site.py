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
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from site_settings import load_config

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "Parket36-Live-Health/1.0"
TIMEOUT_SECONDS = 20
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


def fetch_text(url: str) -> tuple[int, str, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    context = ssl.create_default_context()
    with urlopen(request, timeout=TIMEOUT_SECONDS, context=context) as response:
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


def http_check(name: str, url: str) -> tuple[CheckResult, str]:
    try:
        status, final_url, text = fetch_text(url)
    except HTTPError as exc:
        return CheckResult(name, False, f"HTTP {exc.code}: {exc.reason}"), ""
    except (URLError, TimeoutError, ssl.SSLError, ValueError) as exc:
        return CheckResult(name, False, str(exc)), ""

    if status != 200:
        return CheckResult(name, False, f"HTTP {status}, final URL: {final_url}"), text
    return CheckResult(name, True, f"HTTP 200, final URL: {final_url}"), text


def www_redirect_check(www_url: str, expected_domain: str) -> CheckResult:
    try:
        status, final_url, _ = fetch_text(www_url)
    except HTTPError as exc:
        return CheckResult("www HTTPS redirect", False, f"HTTP {exc.code}: {exc.reason}")
    except (URLError, TimeoutError, ssl.SSLError, ValueError) as exc:
        return CheckResult("www HTTPS redirect", False, str(exc))

    final = urlsplit(final_url)
    expected = urlsplit(expected_domain)
    correct_origin = final.scheme == "https" and final.hostname == expected.hostname
    correct_path = (final.path or "/") == "/"
    ok = status == 200 and correct_origin and correct_path
    detail = f"HTTP {status}, final URL: {final_url}"
    if not correct_origin:
        detail += f"; expected HTTPS host {expected.hostname}"
    if not correct_path:
        detail += "; expected root path /"
    return CheckResult("www HTTPS redirect", ok, detail)


def write_report(path: Path, domain: str, results: list[CheckResult]) -> None:
    generated = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Parket36 live health report",
        "",
        f"Generated: `{generated}`",
        f"Domain: `{domain}`",
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

    findings: list[str] = []
    if not passing_apex.ok:
        findings.append("complete GitHub Pages apex records must pass")
    if not passing_www.ok:
        findings.append("a www host resolving to GitHub Pages must pass")
    if missing_apex.ok or "missing GitHub Pages IPv4" not in missing_apex.detail:
        findings.append("an incomplete apex record set must fail with missing-address detail")
    if wrong_host.ok or "unexpected addresses" not in wrong_host.detail:
        findings.append("an old-hosting address must fail with unexpected-address detail")

    with TemporaryDirectory() as temporary:
        report = Path(temporary) / "report.md"
        write_report(report, "https://example.test", results)
        text = report.read_text(encoding="utf-8")

    required = [
        "# Parket36 live health report",
        "Domain: `https://example.test`",
        "| DNS apex GitHub Pages | PASS |",
        "| DNS www GitHub Pages | PASS |",
        "| Missing apex record | FAIL |",
        "| Old hosting | FAIL |",
        "| Escaping | FAIL | line one\\|line two line three |",
    ]
    findings.extend(f"missing report marker: {marker}" for marker in required if marker not in text)

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
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    config = load_config()
    domain = str(config["domain"]).rstrip("/")
    parsed = urlsplit(domain)
    host = parsed.hostname or ""
    phone_display = str(config["phone_display"])

    results: list[CheckResult] = []
    if parsed.scheme != "https" or not host:
        results.append(CheckResult("Domain config", False, f"invalid HTTPS domain: {domain}"))
        write_report(ROOT / args.report, domain, results)
        return 1

    www_host = f"www.{host}"
    results.append(dns_check("DNS apex GitHub Pages", host, require_all_ipv4=True))
    results.append(dns_check("DNS www GitHub Pages", www_host, require_all_ipv4=False))

    home_result, home = http_check("Homepage HTTPS", domain + "/")
    results.append(home_result)
    if home_result.ok:
        required_markers = ["Паркет36", phone_display, "Оценка по фото"]
        missing = [marker for marker in required_markers if marker not in home]
        results.append(
            CheckResult(
                "Homepage markers",
                not missing,
                "all markers found" if not missing else "missing: " + ", ".join(missing),
            )
        )
        forbidden = [marker for marker in ("WhatsApp", "wa.me") if marker in home]
        results.append(
            CheckResult(
                "Legacy WhatsApp",
                not forbidden,
                "not present" if not forbidden else "found: " + ", ".join(forbidden),
            )
        )

    results.append(www_redirect_check(f"https://{www_host}/", domain))

    robots_url = domain + "/robots.txt"
    robots_result, robots = http_check("robots.txt", robots_url)
    results.append(robots_result)
    if robots_result.ok:
        expected_sitemap = f"Sitemap: {domain}/sitemap.xml"
        expected_host = f"Host: {host}"
        missing = [marker for marker in (expected_sitemap, expected_host) if marker not in robots]
        results.append(
            CheckResult(
                "robots.txt markers",
                not missing,
                "all markers found" if not missing else "missing: " + ", ".join(missing),
            )
        )

    sitemap_url = domain + "/sitemap.xml"
    sitemap_result, sitemap = http_check("sitemap.xml", sitemap_url)
    results.append(sitemap_result)
    if sitemap_result.ok:
        try:
            root = ET.fromstring(sitemap)
            namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            locations = [
                (node.text or "").strip()
                for node in root.findall("sm:url/sm:loc", namespace)
            ]
            bad_domains = [url for url in locations if not url.startswith(domain + "/")]
            sitemap_ok = len(locations) >= MIN_SITEMAP_URLS and not bad_domains
            detail_parts = [f"URLs: {len(locations)}"]
            if bad_domains:
                detail_parts.append(f"wrong domain URLs: {len(bad_domains)}")
            if len(locations) < MIN_SITEMAP_URLS:
                detail_parts.append(f"minimum expected: {MIN_SITEMAP_URLS}")
            results.append(CheckResult("Sitemap content", sitemap_ok, "; ".join(detail_parts)))
        except ET.ParseError as exc:
            results.append(CheckResult("Sitemap content", False, f"invalid XML: {exc}"))

    report_path = ROOT / args.report
    write_report(report_path, domain, results)

    for result in results:
        state = "PASS" if result.ok else "FAIL"
        print(f"[{state}] {result.name}: {result.detail}")
    print(f"Report: {report_path.relative_to(ROOT)}")

    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
