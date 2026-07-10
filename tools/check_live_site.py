#!/usr/bin/env python3
"""Check the public Parket36 domain, HTTPS, robots and sitemap."""

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


def dns_check(host: str) -> CheckResult:
    try:
        records = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        return CheckResult("DNS", False, str(exc))

    addresses = sorted({record[4][0] for record in records})
    if not addresses:
        return CheckResult("DNS", False, "no addresses returned")
    return CheckResult("DNS", True, ", ".join(addresses))


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
    results = [
        CheckResult("Passing check", True, "ok"),
        CheckResult("Failing check", False, "line one|line two\nline three"),
    ]

    with TemporaryDirectory() as temporary:
        report = Path(temporary) / "report.md"
        write_report(report, "https://example.test", results)
        text = report.read_text(encoding="utf-8")

    required = [
        "# Parket36 live health report",
        "Domain: `https://example.test`",
        "| Passing check | PASS | ok |",
        "| Failing check | FAIL | line one\\|line two line three |",
    ]
    missing = [marker for marker in required if marker not in text]
    if missing:
        print("Live health self-test failed:")
        for marker in missing:
            print(f"  - missing report marker: {marker}")
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

    results.append(dns_check(host))

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
