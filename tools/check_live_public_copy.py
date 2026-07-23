#!/usr/bin/env python3
"""Check that live commercial pages expose client-ready and honest lead copy."""

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
USER_AGENT = "Parket36-Live-Public-Copy/1.2"
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

REQUEST_FORBIDDEN = (
    "заявка уйдёт Ивану",
    "сайт отправит заявку Ивану",
    "Форма отправит заявку Ивану через защищённую форму",
    "заявка передаётся Ивану через защищённую форму",
    "Заявка отправляется Ивану через защищённую форму",
    "Иван получит заявку через ту же защищённую систему",
)

REQUEST_REQUIRED = (
    "сервис попробует сохранить заявку",
    "Заполните форму — получите понятный следующий шаг",
    "Если автоматическое уведомление не подтвердится",
    "Форма попробует сохранить заявку в защищённой системе",
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


def evaluate_request(text: str) -> Result:
    forbidden = [phrase for phrase in REQUEST_FORBIDDEN if phrase in text]
    missing = [phrase for phrase in REQUEST_REQUIRED if phrase not in text]
    details: list[str] = []
    if forbidden:
        details.append("forbidden: " + ", ".join(forbidden))
    if missing:
        details.append("missing: " + ", ".join(missing))
    return Result(not details, "honest lead markers found" if not details else "; ".join(details))


def request_url(
    domain: str,
    attempt: int,
    nonce: int | None = None,
    path: str = "/",
) -> str:
    token = time.time_ns() if nonce is None else nonce
    query = urlencode({"verify_public_copy": str(token), "attempt": str(attempt)})
    normalized_path = "/" if path.strip("/") == "" else "/" + path.strip("/") + "/"
    return domain.rstrip("/") + normalized_path + "?" + query


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


def fetch_and_evaluate(
    label: str,
    url: str,
    timeout: float,
    evaluator,
    attempt: int,
) -> Result:
    try:
        status, final_url, text = fetch_homepage(url, timeout)
    except HTTPError as exc:
        return Result(False, f"{label}: HTTP {exc.code}: {exc.reason}; cache_bust_attempt={attempt}")
    except (URLError, TimeoutError, ssl.SSLError, ValueError) as exc:
        return Result(False, f"{label}: {exc}; cache_bust_attempt={attempt}")

    if status != 200:
        return Result(
            False,
            f"{label}: HTTP {status}, final URL: {final_url}; cache_bust_attempt={attempt}",
        )

    copy_result = evaluator(text)
    return Result(
        copy_result.ok,
        f"{label}: HTTP 200, final URL: {final_url}; {copy_result.detail}; "
        f"cache_bust_attempt={attempt}",
    )


def run_once(domain: str, timeout: float, attempt: int) -> Result:
    checks = (
        (
            "Homepage client-ready copy",
            request_url(domain, attempt),
            evaluate,
        ),
        (
            "Request page honest lead copy",
            request_url(domain, attempt, path="/zayavka/"),
            evaluate_request,
        ),
    )
    details: list[str] = []
    for label, url, evaluator in checks:
        result = fetch_and_evaluate(label, url, timeout, evaluator, attempt)
        details.append(result.detail)
        if not result.ok:
            return Result(False, "; ".join(details))
    return Result(True, "; ".join(details))


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
            f"| Homepage client-ready copy and request page honest lead copy | {state} | {detail} |",
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
    good_homepage = " ".join(REQUIRED)
    good_request = " ".join(REQUEST_REQUIRED)
    passing_homepage = evaluate(good_homepage)
    forbidden_homepage = evaluate(good_homepage + " Фото вместо иллюстрации")
    missing_homepage = evaluate("Оценка по фото")
    passing_request = evaluate_request(good_request)
    forbidden_request = evaluate_request(good_request + " заявка уйдёт Ивану")
    missing_request = evaluate_request("сервис попробует сохранить заявку")
    cache_busted = request_url("https://example.test", 3, nonce=123456)
    request_cache_busted = request_url(
        "https://example.test",
        4,
        nonce=654321,
        path="/zayavka/",
    )
    findings: list[str] = []

    if not passing_homepage.ok:
        findings.append("complete client-ready homepage copy must pass")
    if forbidden_homepage.ok or "Фото вместо иллюстрации" not in forbidden_homepage.detail:
        findings.append("forbidden editor copy must fail with detail")
    if missing_homepage.ok or "missing:" not in missing_homepage.detail:
        findings.append("incomplete client-ready homepage copy must fail")
    if not passing_request.ok:
        findings.append("complete honest request copy must pass")
    if forbidden_request.ok or "заявка уйдёт Ивану" not in forbidden_request.detail:
        findings.append("unconditional request-delivery claim must fail with detail")
    if missing_request.ok or "missing:" not in missing_request.detail:
        findings.append("incomplete request-page copy must fail")

    for marker in ("https://example.test/?", "verify_public_copy=123456", "attempt=3"):
        if marker not in cache_busted:
            findings.append(f"cache-busted homepage URL missing marker: {marker}")
    for marker in (
        "https://example.test/zayavka/?",
        "verify_public_copy=654321",
        "attempt=4",
    ):
        if marker not in request_cache_busted:
            findings.append(f"cache-busted request URL missing marker: {marker}")

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
    print(f"[{state}] Homepage client-ready copy and request page honest lead copy: {result.detail}")
    print(f"Report: {args.report}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
