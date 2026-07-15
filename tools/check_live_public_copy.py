#!/usr/bin/env python3
"""Check that the live homepage exposes client-ready copy, not editor placeholders."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import ssl
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from site_settings import load_config

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "Parket36-Live-Public-Copy/1.1"
MAX_RESPONSE_BYTES = 2_000_000

FORBIDDEN = (
    "Фото вместо иллюстрации",
    "Место под реальное фото",
    "Место под фото",
    "Место для фото",
    "Сюда нужен реальный кадр",
    "Места под будущие реальные фотографии",
    "будущие кейсы",
    "после съёмки по ТЗ",
)

REQUIRED = (
    "Как подготовить фотографии пола для предварительной оценки",
    "Оценка по фото",
    "Общий вид комнаты",
    "Дефект крупно",
    "Проблемное место",
    "Короткое видео",
    "Скрип или движение",
    "Для первого ориентира достаточно фото пола и короткого описания задачи.",
)


@dataclass(frozen=True)
class Result:
    ok: bool
    detail: str


def evaluate(text: str) -> Result:
    forbidden = [phrase for phrase in FORBIDDEN if phrase in text]
    missing = [phrase for phrase in REQUIRED if phrase not in text]
    details: list[str] = []
    if forbidden:
        details.append("forbidden: " + ", ".join(forbidden))
    if missing:
        details.append("missing: " + ", ".join(missing))
    return Result(not details, "client-ready markers found" if not details else "; ".join(details))


def request_url(domain: str, attempt: int, nonce: int | None = None) -> str:
    token = time.time_ns() if nonce is None else nonce
    query = urlencode({"verify_public_copy": str(token), "attempt": str(attempt)})
    return domain.rstrip("/") + "/?" + query


def fetch_homepage(url: str, timeout: float) -> tuple[int, str, str]:
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


def run_once(domain: str, timeout: float, attempt: int) -> Result:
    url = request_url(domain, attempt)
    try:
        status, final_url, text = fetch_homepage(url, timeout)
    except HTTPError as exc:
        return Result(False, f"HTTP {exc.code}: {exc.reason}; cache_bust_attempt={attempt}")
    except (URLError, TimeoutError, ssl.SSLError, ValueError) as exc:
        return Result(False, f"{exc}; cache_bust_attempt={attempt}")

    if status != 200:
        return Result(False, f"HTTP {status}, final URL: {final_url}; cache_bust_attempt={attempt}")
    copy_result = evaluate(text)
    return Result(
        copy_result.ok,
        f"HTTP 200, final URL: {final_url}; {copy_result.detail}; cache_bust_attempt={attempt}",
    )


def run_with_retries(domain: str, timeout: float, attempts: int, retry_delay: float) -> tuple[Result, int]:
    result = Result(False, "not checked")
    for attempt in range(1, attempts + 1):
        result = run_once(domain, timeout, attempt)
        if result.ok:
            return result, attempt
        if attempt < attempts and retry_delay:
            time.sleep(retry_delay)
    return result, attempts


def append_report(path: Path, domain: str, result: Result, attempts_used: int) -> None:
    generated = datetime.now(timezone.utc).isoformat()
    state = "PASS" if result.ok else "FAIL"
    detail = result.detail.replace("|", "\\|").replace("\n", " ")
    block = "\n".join(
        (
            "",
            "## Live homepage public copy",
            "",
            f"Generated: `{generated}`",
            f"Domain: `{domain}`",
            f"Attempts used: `{attempts_used}`",
            "",
            "| Check | Result | Detail |",
            "| --- | --- | --- |",
            f"| Homepage client-ready copy | {state} | {detail} |",
            "",
        )
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    prefix = path.read_text(encoding="utf-8") if path.exists() else "# Parket36 live health report\n"
    path.write_text(prefix.rstrip() + "\n" + block, encoding="utf-8")


def validate_args(timeout: float, attempts: int, retry_delay: float) -> None:
    if timeout <= 0 or timeout > 120:
        raise ValueError("timeout must be greater than 0 and no more than 120 seconds")
    if attempts < 1 or attempts > 20:
        raise ValueError("attempts must be between 1 and 20")
    if retry_delay < 0 or retry_delay > 120:
        raise ValueError("retry-delay must be between 0 and 120 seconds")


def self_test() -> int:
    good = " ".join(REQUIRED)
    passing = evaluate(good)
    forbidden = evaluate(good + " Фото вместо иллюстрации")
    missing = evaluate("Оценка по фото")
    cache_busted = request_url("https://example.test", 3, nonce=123456)
    findings: list[str] = []
    if not passing.ok:
        findings.append("complete client-ready copy must pass")
    if forbidden.ok or "Фото вместо иллюстрации" not in forbidden.detail:
        findings.append("forbidden editor copy must fail with detail")
    if missing.ok or "missing:" not in missing.detail:
        findings.append("incomplete client-ready copy must fail")
    for marker in ("https://example.test/?", "verify_public_copy=123456", "attempt=3"):
        if marker not in cache_busted:
            findings.append(f"cache-busted homepage URL missing marker: {marker}")

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

    if findings:
        print("Live public-copy self-test findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("Live public-copy self-test passed")
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
        domain = str(load_config()["domain"]).rstrip("/")
    except (OSError, ValueError, KeyError) as exc:
        print(f"Live public-copy check failed: {exc}", file=sys.stderr)
        return 1

    result, attempts_used = run_with_retries(domain, args.timeout, args.attempts, args.retry_delay)
    append_report(ROOT / args.report, domain, result, attempts_used)
    state = "PASS" if result.ok else "FAIL"
    print(f"[{state}] Homepage client-ready copy: {result.detail}")
    print(f"Report: {args.report}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
