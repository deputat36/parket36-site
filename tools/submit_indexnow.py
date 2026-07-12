#!/usr/bin/env python3
"""Validate and submit Parket36 sitemap URLs through IndexNow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
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


def verify_live_key(domain: str, config: dict[str, str], timeout: float) -> None:
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


def submit_urls(domain: str, config: dict[str, str], urls: list[str], timeout: float) -> int:
    payload = {
        "host": urlsplit(domain).netloc,
        "key": config["key"],
        "keyLocation": key_location(domain, config),
        "urlList": urls,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
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
            response.read(4096)
    except HTTPError as exc:
        detail = exc.read(4096).decode("utf-8", errors="replace").strip()
        raise ValueError(f"IndexNow returned HTTP {exc.code}: {detail or exc.reason}") from exc
    except (URLError, TimeoutError) as exc:
        raise ValueError(f"IndexNow request failed: {exc}") from exc

    if status not in {200, 202}:
        raise ValueError(f"IndexNow returned unexpected HTTP {status}")
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="validate config, key file and sitemap")
    action.add_argument("--verify-live-key", action="store_true", help="check the deployed key file")
    action.add_argument("--submit", action="store_true", help="verify ownership and submit sitemap URLs")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        domain, config, urls = validate_static_contract()
        if args.verify_live_key:
            verify_live_key(domain, config, args.timeout)
            print(f"Live IndexNow key verified: {key_location(domain, config)}")
            return 0
        if args.submit:
            verify_live_key(domain, config, args.timeout)
            status = submit_urls(domain, config, urls, args.timeout)
            print(f"IndexNow accepted {len(urls)} URLs with HTTP {status}")
            return 0

        print(
            "IndexNow check passed: "
            f"{len(urls)} sitemap URLs, key file {config['key_file']}, endpoint {config['endpoint']}"
        )
        return 0
    except ValueError as exc:
        print(f"IndexNow check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
