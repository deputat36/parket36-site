#!/usr/bin/env python3
"""Close issue #5 only after an exact successful post-deploy live verification."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ISSUE_NUMBER = 5
EXPECTED_TITLE = "Переключить parket36.ru на GitHub Pages"
API_VERSION = "2022-11-28"


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
            "User-Agent": "Parket36-Pages-Switch-Completer/1.0",
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


def github_context() -> tuple[str, str, str, str, str, str]:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    event_name = os.environ.get("GITHUB_EVENT_NAME", "").strip()
    monitoring_run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    deploy_sha = os.environ.get("PAGES_DEPLOY_SHA", "").strip()
    deploy_run_id = os.environ.get("PAGES_DEPLOY_RUN_ID", "").strip()

    missing = [
        name
        for name, value in (
            ("GITHUB_REPOSITORY", repository),
            ("GITHUB_TOKEN", token),
            ("GITHUB_EVENT_NAME", event_name),
            ("GITHUB_RUN_ID", monitoring_run_id),
            ("PAGES_DEPLOY_SHA", deploy_sha),
            ("PAGES_DEPLOY_RUN_ID", deploy_run_id),
        )
        if not value
    ]
    if missing:
        raise RuntimeError("missing GitHub Actions environment: " + ", ".join(missing))
    if event_name != "workflow_run":
        raise RuntimeError("issue #5 may only be completed from a workflow_run post-deploy check")

    return repository, token, monitoring_run_id, deploy_sha, deploy_run_id, event_name


def issue_api_base(repository: str) -> str:
    return f"https://api.github.com/repos/{repository}"


def completion_comment(
    repository: str,
    monitoring_run_id: str,
    deploy_sha: str,
    deploy_run_id: str,
) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    repository_url = f"https://github.com/{repository}"
    return "\n".join(
        [
            "## Переключение на GitHub Pages подтверждено автоматически",
            "",
            "Post-deploy проверка завершилась успешно:",
            "",
            "- DNS корневого домена и `www` направлен в инфраструктуру GitHub Pages;",
            "- HTTPS, главная, `robots.txt` и `sitemap.xml` доступны;",
            "- `/deployment.json` подтверждает публикацию Actions artifact `_site`;",
            "- SHA и run ID live-сборки совпали с завершившимся Pages deploy.",
            "",
            f"Проверено: `{generated}`",
            f"Опубликованный commit: `{deploy_sha}`",
            f"Pages deploy: {repository_url}/actions/runs/{deploy_run_id}",
            f"Live verification: {repository_url}/actions/runs/{monitoring_run_id}",
            "",
            "Issue закрывается автоматически как выполненный.",
        ]
    )


def complete_issue() -> int:
    repository, token, monitoring_run_id, deploy_sha, deploy_run_id, _ = github_context()
    base = issue_api_base(repository)
    issue = api_request("GET", f"{base}/issues/{ISSUE_NUMBER}", token)

    if not isinstance(issue, dict) or "pull_request" in issue:
        raise RuntimeError(f"issue #{ISSUE_NUMBER} is unavailable or is a pull request")
    if issue.get("title") != EXPECTED_TITLE:
        raise RuntimeError(
            f"issue #{ISSUE_NUMBER} title changed: {issue.get('title')!r}; expected {EXPECTED_TITLE!r}"
        )
    if issue.get("state") == "closed":
        print(f"Issue #{ISSUE_NUMBER} is already closed")
        return 0

    comment = completion_comment(repository, monitoring_run_id, deploy_sha, deploy_run_id)
    api_request("POST", f"{base}/issues/{ISSUE_NUMBER}/comments", token, {"body": comment})
    api_request(
        "PATCH",
        f"{base}/issues/{ISSUE_NUMBER}",
        token,
        {"state": "closed", "state_reason": "completed"},
    )
    print(f"Closed completed Pages switch issue #{ISSUE_NUMBER}")
    return 0


def self_test() -> int:
    findings: list[str] = []
    body = completion_comment("owner/repo", "200", "abc123", "100")
    required = [
        "Переключение на GitHub Pages подтверждено автоматически",
        "DNS корневого домена",
        "Actions artifact `_site`",
        "Опубликованный commit: `abc123`",
        "owner/repo/actions/runs/100",
        "owner/repo/actions/runs/200",
        "Issue закрывается автоматически",
    ]
    findings.extend(f"missing completion marker: {marker}" for marker in required if marker not in body)

    if ISSUE_NUMBER != 5:
        findings.append("Pages switch issue number must remain #5")
    if EXPECTED_TITLE != "Переключить parket36.ru на GitHub Pages":
        findings.append("Pages switch issue title guard changed")

    if findings:
        print("Pages switch issue completer self-test failed:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Pages switch issue completer self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    return complete_issue()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print(f"Pages switch issue completer error: {exc}", file=sys.stderr)
        sys.exit(1)
