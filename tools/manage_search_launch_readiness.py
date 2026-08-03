#!/usr/bin/env python3
"""Maintain one safe search launch readiness snapshot comment on issue 308."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_VERSION = "2022-11-28"
ISSUE_NUMBER = 308
COMMENT_MARKER = "<!-- parket36-search-launch-readiness -->"
DEFAULT_REPORT = Path("search-launch-readiness.md")
MAX_REPORT_CHARS = 12_000
REQUIRED_REPORT_MARKERS = (
    "# Search launch readiness — Паркет36",
    "Source commit:",
    "Readiness level:",
    "Отчёт не проверяет данные внутри поисковых кабинетов",
    "PASS подтверждает техническую готовность",
)
FORBIDDEN_REPORT_MARKERS = (
    "Authorization: Bearer",
    "SUPABASE_ACCESS_TOKEN",
    "PARKET_HEALTHCHECK_TOKEN",
    "PARKET_IP_HASH_SALT",
    "PARKET_SMOKE_CONTACT",
)


def api_request(
    method: str,
    url: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Parket36-Search-Launch-Readiness/1.0",
            "X-GitHub-Api-Version": API_VERSION,
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1_000]
        raise RuntimeError(f"GitHub API HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"GitHub API request failed: {exc}") from exc
    return json.loads(raw) if raw else None


def github_context() -> tuple[str, str, str, str]:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    missing = [
        name
        for name, value in (
            ("GITHUB_REPOSITORY", repository),
            ("GITHUB_TOKEN", token),
            ("GITHUB_RUN_ID", run_id),
        )
        if not value
    ]
    if missing:
        raise RuntimeError("missing GitHub Actions environment: " + ", ".join(missing))
    return repository, token, run_id, server


def api_base(repository: str) -> str:
    return f"https://api.github.com/repos/{repository}"


def run_url(server: str, repository: str, run_id: str) -> str:
    return f"{server}/{repository}/actions/runs/{run_id}"


def validate_safe_report(text: str) -> None:
    missing = [marker for marker in REQUIRED_REPORT_MARKERS if marker not in text]
    if missing:
        raise ValueError("search readiness summary is missing safety markers: " + ", ".join(missing))
    forbidden = [marker for marker in FORBIDDEN_REPORT_MARKERS if marker in text]
    if forbidden:
        raise ValueError("refusing to publish protected configuration markers: " + ", ".join(forbidden))


def report_excerpt(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"search readiness summary was not created: {path}")
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    validate_safe_report(text)
    if len(text) <= MAX_REPORT_CHARS:
        return text
    return text[:MAX_REPORT_CHARS].rstrip() + "\n\n_Сводка сокращена; полный отчёт сохранён в Actions artifact._"


def render_comment(report: str, run_link: str) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    return "\n".join(
        [
            COMMENT_MARKER,
            "## Последняя готовность поискового запуска",
            "",
            f"Обновлено: `{generated}`",
            f"Workflow run: {run_link}",
            "",
            report,
            "",
            "Этот комментарий автоматически обновляется после успешной публикации сайта или ручного запуска workflow.",
            "Он подтверждает только техническую готовность и не доказывает права в поисковых кабинетах, индексацию или позиции.",
            "Полные component reports остаются в Actions artifact `search-launch-readiness`.",
        ]
    )


def find_managed_comment(comments: list[dict[str, Any]]) -> dict[str, Any] | None:
    for comment in comments:
        body = str(comment.get("body") or "")
        if COMMENT_MARKER in body:
            return comment
    return None


def list_issue_comments(repository: str, token: str) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    for page in range(1, 11):
        payload = api_request(
            "GET",
            api_base(repository) + f"/issues/{ISSUE_NUMBER}/comments?per_page=100&page={page}",
            token,
        )
        batch = payload or []
        comments.extend(batch)
        if len(batch) < 100:
            break
    return comments


def publish_snapshot(report_path: Path) -> int:
    repository, token, run_id, server = github_context()
    report = report_excerpt(report_path)
    body = render_comment(report, run_url(server, repository, run_id))
    existing = find_managed_comment(list_issue_comments(repository, token))

    if existing:
        comment_id = int(existing["id"])
        api_request(
            "PATCH",
            api_base(repository) + f"/issues/comments/{comment_id}",
            token,
            {"body": body},
        )
        print(f"Updated search launch readiness comment {comment_id} on issue #{ISSUE_NUMBER}")
        return 0

    created = api_request(
        "POST",
        api_base(repository) + f"/issues/{ISSUE_NUMBER}/comments",
        token,
        {"body": body},
    )
    print(f"Created search launch readiness comment {created['id']} on issue #{ISSUE_NUMBER}")
    return 0


def self_test() -> int:
    failures: list[str] = []
    safe_report = "\n".join(
        [
            "# Search launch readiness — Паркет36",
            "",
            "Source commit: `" + "a" * 40 + "`",
            "Readiness level: **TECHNICAL_READY_ANALYTICS_PENDING**",
            "",
            "- Отчёт не проверяет данные внутри поисковых кабинетов и не получает к ним доступ.",
            "- PASS подтверждает техническую готовность, но не гарантирует индексацию или позиции.",
        ]
    )

    try:
        validate_safe_report(safe_report)
    except ValueError as exc:
        failures.append(f"safe summary was rejected: {exc}")

    for unsafe in (
        safe_report + "\nSUPABASE_ACCESS_TOKEN=value",
        safe_report + "\nPARKET_IP_HASH_SALT=value",
        "# Search launch readiness — Паркет36\nReadiness level: **BLOCKED**",
    ):
        try:
            validate_safe_report(unsafe)
        except ValueError:
            pass
        else:
            failures.append("unsafe or incomplete report was accepted")

    comment = render_comment(safe_report, "https://example.test/actions/runs/123")
    for marker in (
        COMMENT_MARKER,
        "Последняя готовность поискового запуска",
        "TECHNICAL_READY_ANALYTICS_PENDING",
        "не доказывает права",
        "component reports остаются",
    ):
        if marker not in comment:
            failures.append(f"managed comment is missing marker: {marker}")

    comments = [
        {"id": 1, "body": "ordinary comment"},
        {"id": 2, "body": COMMENT_MARKER + "\nmanaged"},
    ]
    found = find_managed_comment(comments)
    if not found or found.get("id") != 2:
        failures.append("managed search readiness comment was not found by marker")
    if find_managed_comment([comments[0]]) is not None:
        failures.append("ordinary comment was incorrectly treated as managed")

    if failures:
        print("Search launch readiness issue manager self-test failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Search launch readiness issue manager self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    return publish_snapshot(Path(args.report))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"Search launch readiness issue manager error: {exc}", file=sys.stderr)
        sys.exit(1)
