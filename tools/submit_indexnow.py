#!/usr/bin/env python3
"""Validate and submit Parket36 sitemap URLs through IndexNow."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

from site_settings import load_config

ROOT = Path(__file__).resolve().parents[1]
INDEXNOW_CONFIG_PATH = ROOT / "data" / "indexnow.json"
SITEMAP_PATH = ROOT / "sitemap.xml"
KEY_PATTERN = re.compile(r"^[A-Za-z0-9-]{8,128}$")
MAX_URLS = 10_000
DEFAULT_TIMEOUT = 20.0
DEFAULT_ATTEMPTS = 6
DEFAULT_RETRY_DELAY = 10.0


@dataclass(frozen=True)
class IndexNowReport:
    action: str
    success: bool
    detail: str
    domain: str = ""
    endpoint: str = ""
    key_location: str = ""
    url_count: int = 0
    http_status: int | None = None
    live_key_attempts: int | None = None


def load_indexnow_config() -> dict[str, str]:
    try:
        raw = json.loads(INDEXNOW_CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError("data/indexnow.json is missing") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"data/indexnow.json is invalid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError("data/indexnow.json must contain an object")

    result: dict[str, str] = {}
    for field in ("key", "endpoint", "key_file"):
        value = raw.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"data/indexnow.json must contain non-empty {field}")
        result[field] = value.strip()

    if not KEY_PATTERN.fullmatch(result["key"]):
        raise ValueError("IndexNow key must be 8-128 letters, numbers or dashes")

    endpoint = urlsplit(result["endpoint"])
    if endpoint.scheme != "https" or not endpoint.netloc:
        raise ValueError("IndexNow endpoint must be an absolute HTTPS URL")

    key_file = Path(result["key_file"])
    if key_file.is_absolute() or len(key_file.parts) != 1 or key_file.suffix != ".txt":
        raise ValueError("IndexNow key_file must be one root-level .txt filename")

    return result


def load_site_domain() -> str:
    domain = str(load_config()["domain"]).rstrip("/")
    parsed = urlsplit(domain)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path:
        raise ValueError("site domain must be an origin-only HTTPS URL")
    return domain


def load_sitemap_urls(domain: str) -> list[str]:
    try:
        tree = ET.parse(SITEMAP_PATH)
    except FileNotFoundError as exc:
        raise ValueError("sitemap.xml is missing") from exc
    except ET.ParseError as exc:
        raise ValueError(f"sitemap.xml is invalid XML: {exc}") from exc

    expected_host = urlsplit(domain).netloc
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls: list[str] = []
    seen: set[str] = set()

    for node in tree.findall("sm:url/sm:loc", namespace):
        value = (node.text or "").strip()
        if not value:
            raise ValueError("sitemap.xml contains an empty loc")
        parsed = urlsplit(value)
        if parsed.scheme != "https" or parsed.netloc != expected_host:
            raise ValueError(f"sitemap URL belongs to an unexpected host: {value}")
        if value not in seen:
            seen.add(value)
            urls.append(value)

    if not urls:
        raise ValueError("sitemap.xml does not contain URLs")
    if len(urls) > MAX_URLS:
        raise ValueError(f"sitemap contains {len(urls)} URLs; IndexNow allows {MAX_URLS} per request")
    return urls


def key_file_path(config: dict[str, str]) -> Path:
    return ROOT / config["key_file"]


def key_location(domain: str, config: dict[str, str]) -> str:
    return f"{domain}/{config['key_file']}"


def validate_static_contract() -> tuple[str, dict[str, str], list[str]]:
    domain = load_site_domain()
    config = load_indexnow_config()
    urls = load_sitemap_urls(domain)

    path = key_file_path(config)
    if not path.exists():
        raise ValueError(f"{config['key_file']} is missing")
    actual_key = path.read_text(encoding="utf-8").strip()
    if actual_key != config["key"]:
        raise ValueError(f"{config['key_file']} must contain the configured IndexNow key")

    build_script = (ROOT / "tools" / "build_pages.py").read_text(encoding="utf-8")
    if f'"{config["key_file"]}"' not in build_script:
        raise ValueError(f"tools/build_pages.py must publish {config['key_file']}")

    return domain, config, urls


def verify_live_key_once(domain: str, config: dict[str, str], timeout: float) -> None:
    location = key_location(domain, config)
    request = Request(location, headers={"User-Agent": "Parket36-IndexNow/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            body = response.read(1024).decode("utf-8", errors="replace").strip()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise ValueError(f"live IndexNow key is unavailable at {location}: {exc}") from exc

    if status != 200:
        raise ValueError(f"live IndexNow key returned HTTP {status}: {location}")
    if body != config["key"]:
        raise ValueError(f"live IndexNow key does not match data/indexnow.json: {location}")


def verify_live_key(
    domain: str,
    config: dict[str, str],
    timeout: float,
    attempts: int,
    retry_delay: float,
) -> int:
    last_error: ValueError | None = None
    for attempt in range(1, attempts + 1):
        try:
            verify_live_key_once(domain, config, timeout)
            return attempt
        except ValueError as exc:
            last_error = exc
            if attempt < attempts and retry_delay:
                time.sleep(retry_delay)

    assert last_error is not None
    raise ValueError(f"live key verification failed after {attempts} attempts: {last_error}")


def build_payload(domain: str, config: dict[str, str], urls: list[str]) -> dict[str, object]:
    return {
        "host": urlsplit(domain).netloc,
        "key": config["key"],
        "keyLocation": key_location(domain, config),
        "urlList": urls,
    }


def submit_urls(domain: str, config: dict[str, str], urls: list[str], timeout: float) -> tuple[int, str]:
    data = json.dumps(build_payload(domain, config, urls), ensure_ascii=False).encode("utf-8")
    request = Request(
        config["endpoint"],
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Parket36-IndexNow/1.0",
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            detail = response.read(4096).decode("utf-8", errors="replace").strip()
    except HTTPError as exc:
        detail = exc.read(4096).decode("utf-8", errors="replace").strip()
        raise ValueError(f"IndexNow returned HTTP {exc.code}: {detail or exc.reason}") from exc
    except (URLError, TimeoutError) as exc:
        raise ValueError(f"IndexNow request failed: {exc}") from exc

    if status not in {200, 202}:
        raise ValueError(f"IndexNow returned unexpected HTTP {status}")
    return status, detail


def report_markdown(report: IndexNowReport) -> str:
    result = "PASS" if report.success else "FAIL"
    status = str(report.http_status) if report.http_status is not None else "not received"
    attempts = str(report.live_key_attempts) if report.live_key_attempts is not None else "not completed"
    detail = " ".join(report.detail.split())[:1000] or "No response body."
    generated = datetime.now(timezone.utc).isoformat()
    return "\n".join(
        [
            "# IndexNow submission report",
            "",
            f"Generated: `{generated}`",
            f"Action: `{report.action}`",
            f"Result: **{result}**",
            "",
            "## Contract",
            "",
            f"- Domain: `{report.domain or 'unavailable'}`",
            f"- Endpoint: `{report.endpoint or 'unavailable'}`",
            f"- Key location: `{report.key_location or 'unavailable'}`",
            f"- Sitemap URLs: `{report.url_count}`",
            f"- Live key attempts: `{attempts}`",
            f"- HTTP status: `{status}`",
            "",
            "## Detail",
            "",
            detail,
            "",
            "A successful IndexNow response confirms receipt of the URL notification. It does not guarantee crawling, ranking or inclusion in search results.",
            "",
        ]
    )


def write_report(path: str | None, report: IndexNowReport) -> None:
    if not path:
        return
    target = Path(path)
    if not target.is_absolute():
        target = ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report_markdown(report), encoding="utf-8")


def validate_runtime_args(timeout: float, attempts: int, retry_delay: float) -> None:
    if timeout <= 0 or timeout > 120:
        raise ValueError("timeout must be greater than 0 and no more than 120 seconds")
    if attempts < 1 or attempts > 20:
        raise ValueError("attempts must be between 1 and 20")
    if retry_delay < 0 or retry_delay > 120:
        raise ValueError("retry-delay must be between 0 and 120 seconds")


def run_self_test() -> int:
    config = {
        "key": "abcDEF12-3456",
        "endpoint": "https://api.indexnow.org/indexnow",
        "key_file": "indexnow-key.txt",
    }
    urls = ["https://parket36.ru/", "https://parket36.ru/uslugi/"]
    payload = build_payload("https://parket36.ru", config, urls)
    expected = {
        "host": "parket36.ru",
        "key": config["key"],
        "keyLocation": "https://parket36.ru/indexnow-key.txt",
        "urlList": urls,
    }
    findings: list[str] = []
    if payload != expected:
        findings.append(f"unexpected payload: {payload}")

    markdown = report_markdown(
        IndexNowReport(
            action="submit",
            success=True,
            detail="Accepted",
            domain="https://parket36.ru",
            endpoint=config["endpoint"],
            key_location=str(payload["keyLocation"]),
            url_count=len(urls),
            http_status=202,
            live_key_attempts=2,
        )
    )
    for marker in ("Result: **PASS**", "Sitemap URLs: `2`", "HTTP status: `202`", "Live key attempts: `2`"):
        if marker not in markdown:
            findings.append(f"report is missing marker: {marker}")

    try:
        validate_runtime_args(20, 6, 10)
    except ValueError as exc:
        findings.append(f"valid runtime arguments were rejected: {exc}")
    for invalid in ((0, 6, 10), (20, 0, 10), (20, 6, -1)):
        try:
            validate_runtime_args(*invalid)
        except ValueError:
            continue
        findings.append(f"invalid runtime arguments were accepted: {invalid}")

    if findings:
        print("IndexNow self-test findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("IndexNow self-test passed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="validate config, key file and sitemap")
    action.add_argument("--verify-live-key", action="store_true", help="check the deployed key file")
    action.add_argument("--submit", action="store_true", help="verify ownership and submit sitemap URLs")
    action.add_argument("--self-test", action="store_true", help="run offline payload and report tests")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS)
    parser.add_argument("--retry-delay", type=float, default=DEFAULT_RETRY_DELAY)
    parser.add_argument("--report", help="write a Markdown diagnostic report")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.self_test:
        return run_self_test()

    domain = ""
    config: dict[str, str] = {}
    urls: list[str] = []
    live_attempts: int | None = None
    action = "submit" if args.submit else "verify-live-key" if args.verify_live_key else "check"

    try:
        validate_runtime_args(args.timeout, args.attempts, args.retry_delay)
        domain, config, urls = validate_static_contract()
        if args.verify_live_key:
            live_attempts = verify_live_key(domain, config, args.timeout, args.attempts, args.retry_delay)
            detail = f"Live IndexNow key verified: {key_location(domain, config)}"
            write_report(
                args.report,
                IndexNowReport(
                    action=action,
                    success=True,
                    detail=detail,
                    domain=domain,
                    endpoint=config["endpoint"],
                    key_location=key_location(domain, config),
                    url_count=len(urls),
                    live_key_attempts=live_attempts,
                ),
            )
            print(detail)
            return 0
        if args.submit:
            live_attempts = verify_live_key(domain, config, args.timeout, args.attempts, args.retry_delay)
            status, response_detail = submit_urls(domain, config, urls, args.timeout)
            detail = response_detail or f"IndexNow accepted {len(urls)} URLs"
            write_report(
                args.report,
                IndexNowReport(
                    action=action,
                    success=True,
                    detail=detail,
                    domain=domain,
                    endpoint=config["endpoint"],
                    key_location=key_location(domain, config),
                    url_count=len(urls),
                    http_status=status,
                    live_key_attempts=live_attempts,
                ),
            )
            print(f"IndexNow accepted {len(urls)} URLs with HTTP {status}")
            return 0

        detail = (
            "IndexNow check passed: "
            f"{len(urls)} sitemap URLs, key file {config['key_file']}, endpoint {config['endpoint']}"
        )
        write_report(
            args.report,
            IndexNowReport(
                action=action,
                success=True,
                detail=detail,
                domain=domain,
                endpoint=config["endpoint"],
                key_location=key_location(domain, config),
                url_count=len(urls),
            ),
        )
        print(detail)
        return 0
    except ValueError as exc:
        endpoint = config.get("endpoint", "")
        location = key_location(domain, config) if domain and config.get("key_file") else ""
        write_report(
            args.report,
            IndexNowReport(
                action=action,
                success=False,
                detail=str(exc),
                domain=domain,
                endpoint=endpoint,
                key_location=location,
                url_count=len(urls),
                live_key_attempts=live_attempts,
            ),
        )
        print(f"IndexNow check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
