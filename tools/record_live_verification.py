#!/usr/bin/env python3
"""Create or update one durable roadmap comment for the latest verified Pages deploy."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import re
import sys
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ISSUE_NUMBER = 308
EXPECTED_TITLE = "Автономная дорожная карта улучшения Паркет36"
COMMENT_MARKER = "<!-- parket36-live-verification -->"
API_VERSION = "2022-11-28"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
MAX_COMMENT_PAGES = 50


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
            "User-Agent": "Parket36-Live-Verification-Ledger/1.0",
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


def validated_context(environment: Mapping[str, str]) -> tuple[str, str, str, str, str, str]:
    repository = environment.get("GITHUB_REPOSITORY", "").strip()
    token = environment.get("GITHUB_TOKEN", "").strip()
    event_name = environment.get("GITHUB_EVENT_NAME", "").strip()
    verification_run_id = environment.get("GITHUB_RUN_ID", "").strip()
    deploy_sha = environment.get("PAGES_DEPLOY_SHA", "").strip().lower()
    deploy_run_id = environment.get("PAGES_DEPLOY_RUN_ID", "").strip()
    server = environment.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")

    missing = [
        name
        for name, value in (
            ("GITHUB_REPOSITORY", repository),
            ("GITHUB_TOKEN", token),
            ("GITHUB_EVENT_NAME", event_name),
            ("GITHUB_RUN_ID", verification_run_id),
            ("PAGES_DEPLOY_SHA", deploy_sha),
            ("PAGES_DEPLOY_RUN_ID", deploy_run_id),
        )
        if not value
    ]
    if missing:
        raise RuntimeError("missing GitHub Actions environment: " + ", ".join(missing))
    if event_name != "workflow_run":
        raise RuntimeError("live verification ledger may only be updated from workflow_run")
    if repository.count("/") != 1 or any(not part for part in repository.split("/")):
        raise RuntimeError(f"invalid GITHUB_REPOSITORY: {repository!r}")
    if not SHA_PATTERN.fullmatch(deploy_sha):
        raise RuntimeError("PAGES_DEPLOY_SHA must be a full lowercase 40-character commit SHA")
    if not verification_run_id.isdigit() or not deploy_run_id.isdigit():
        raise RuntimeError("workflow run IDs must contain digits only")
    if not server.startswith("https://"):
        raise RuntimeError("GITHUB_SERVER_URL must use HTTPS")

    return repository, token, verification_run_id, deploy_sha, deploy_run_id, server


def github_context() -> tuple[str, str, str, str, str, str]:
    return validated_context(os.environ)


def issue_api_base(repository: str) -> str:
    return f"https://api.github.com/repos/{repository}"


def verification_comment(
    repository: str,
    server: str,
    verification_run_id: str,
    deploy_sha: str,
    deploy_run_id: str,
    *,
    generated: str | None = None,
) -> str:
    checked = generated or datetime.now(timezone.utc).isoformat()
    repository_url = f"{server}/{repository}"
    return "\n".join(
        [
            COMMENT_MARKER,
            "## Последняя подтверждённая публикация parket36.ru",
            "",
            "Эта служебная запись обновляется на месте только после успешной post-deploy проверки конкретной GitHub Pages публикации.",
            "",
            f"Проверено: `{checked}`",
            f"Опубликованный commit: `{deploy_sha}`",
            f"Pages deploy: {repository_url}/actions/runs/{deploy_run_id}",
            f"Live verification: {repository_url}/actions/runs/{verification_run_id}",
            "",
            "Подтверждено одновременно:",
            "",
            "- DNS и HTTPS корневого домена и `www`;",
            "- главная, `robots.txt` и `sitemap.xml` без повторного CDN-кэша;",
            "- рабочий телефонный маршрут и публичный IndexNow-ключ;",
            "- клиентский текст главной без редакторских заглушек;",
            "- `/deployment.json` из Actions artifact `_site`;",
            "- точное совпадение live SHA и run ID с завершившимся Pages deploy.",
            "",
            "Плановый и ручной monitoring эту запись не обновляют. Artifact `live-health-report` остаётся подробным источником диагностики на 30 дней.",
        ]
    )


def find_ledger_comment(comments: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [comment for comment in comments if COMMENT_MARKER in str(comment.get("body") or "")]
    if len(matches) > 1:
        ids = ", ".join(str(comment.get("id")) for comment in matches)
        raise RuntimeError(f"multiple live verification ledger comments found: {ids}")
    return matches[0] if matches else None


def load_all_comments(base: str, token: str) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    for page in range(1, MAX_COMMENT_PAGES + 1):
        payload = api_request(
            "GET",
            f"{base}/issues/{ISSUE_NUMBER}/comments?per_page=100&page={page}",
            token,
        )
        if not isinstance(payload, list):
            raise RuntimeError("GitHub comments response is not a list")
        comments.extend(item for item in payload if isinstance(item, dict))
        if len(payload) < 100:
            return comments
    raise RuntimeError(f"issue #{ISSUE_NUMBER} comments exceed the supported pagination limit")


def record_verification() -> int:
    repository, token, verification_run_id, deploy_sha, deploy_run_id, server = github_context()
    base = issue_api_base(repository)
    issue = api_request("GET", f"{base}/issues/{ISSUE_NUMBER}", token)

    if not isinstance(issue, dict) or "pull_request" in issue:
        raise RuntimeError(f"issue #{ISSUE_NUMBER} is unavailable or is a pull request")
    if issue.get("title") != EXPECTED_TITLE:
        raise RuntimeError(
            f"issue #{ISSUE_NUMBER} title changed: {issue.get('title')!r}; expected {EXPECTED_TITLE!r}"
        )
    if issue.get("state") != "open":
        raise RuntimeError(f"issue #{ISSUE_NUMBER} must remain open while the roadmap is active")

    body = verification_comment(
        repository,
        server,
        verification_run_id,
        deploy_sha,
        deploy_run_id,
    )
    existing = find_ledger_comment(load_all_comments(base, token))
    if existing:
        comment_id = existing.get("id")
        if not isinstance(comment_id, int):
            raise RuntimeError("existing ledger comment has no numeric id")
        api_request("PATCH", f"{base}/issues/comments/{comment_id}", token, {"body": body})
        print(f"Updated live verification ledger comment {comment_id} on issue #{ISSUE_NUMBER}")
    else:
        created = api_request(
            "POST",
            f"{base}/issues/{ISSUE_NUMBER}/comments",
            token,
            {"body": body},
        )
        comment_id = created.get("id") if isinstance(created, dict) else None
        print(f"Created live verification ledger comment {comment_id} on issue #{ISSUE_NUMBER}")
    return 0


def self_test() -> int:
    findings: list[str] = []
    sha = "a" * 40
    body = verification_comment(
        "owner/repo",
        "https://github.example",
        "222",
        sha,
        "111",
        generated="2026-07-16T12:00:00+00:00",
    )
    required = (
        COMMENT_MARKER,
        "Последняя подтверждённая публикация parket36.ru",
        f"Опубликованный commit: `{sha}`",
        "github.example/owner/repo/actions/runs/111",
        "github.example/owner/repo/actions/runs/222",
        "точное совпадение live SHA и run ID",
        "Плановый и ручной monitoring эту запись не обновляют",
    )
    for marker in required:
        if marker not in body:
            findings.append(f"verification comment missing marker: {marker}")
    if body.count(COMMENT_MARKER) != 1:
        findings.append("verification comment must contain exactly one hidden marker")

    sample = [{"id": 1, "body": "ordinary"}, {"id": 2, "body": COMMENT_MARKER}]
    selected = find_ledger_comment(sample)
    if not selected or selected.get("id") != 2:
        findings.append("ledger selector did not return the marked comment")
    if find_ledger_comment([{"id": 1, "body": "ordinary"}]) is not None:
        findings.append("ledger selector must return None when the marker is absent")
    try:
        find_ledger_comment([{"id": 1, "body": COMMENT_MARKER}, {"id": 2, "body": COMMENT_MARKER}])
    except RuntimeError:
        pass
    else:
        findings.append("duplicate ledger comments must fail closed")

    valid_environment = {
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_TOKEN": "token",
        "GITHUB_EVENT_NAME": "workflow_run",
        "GITHUB_RUN_ID": "222",
        "PAGES_DEPLOY_SHA": sha,
        "PAGES_DEPLOY_RUN_ID": "111",
        "GITHUB_SERVER_URL": "https://github.example",
    }
    try:
        validated_context(valid_environment)
    except RuntimeError as exc:
        findings.append(f"valid workflow context rejected: {exc}")

    invalid_contexts = (
        {**valid_environment, "GITHUB_EVENT_NAME": "workflow_dispatch"},
        {**valid_environment, "PAGES_DEPLOY_SHA": "abc123"},
        {**valid_environment, "PAGES_DEPLOY_RUN_ID": "run-111"},
        {**valid_environment, "GITHUB_SERVER_URL": "http://github.example"},
    )
    for context in invalid_contexts:
        try:
            validated_context(context)
        except RuntimeError:
            continue
        findings.append(f"invalid workflow context accepted: {context}")

    if ISSUE_NUMBER != 308 or EXPECTED_TITLE != "Автономная дорожная карта улучшения Паркет36":
        findings.append("roadmap issue guard changed")

    if findings:
        print("Live verification ledger self-test failed:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("Live verification ledger self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    return record_verification()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print(f"Live verification ledger error: {exc}", file=sys.stderr)
        sys.exit(1)
