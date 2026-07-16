#!/usr/bin/env python3
"""Maintain one issue for repeated GitHub Pages deployment failures."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ISSUE_TITLE = "[monitoring] GitHub Pages deploy failure"
WORKFLOW_FILE = "pages.yml"
API_VERSION = "2022-11-28"
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
FAILURE_CONCLUSIONS = frozenset(
    {
        "failure",
        "cancelled",
        "timed_out",
        "action_required",
        "startup_failure",
        "stale",
    }
)
NON_ALERTING_CONCLUSIONS = frozenset({"neutral", "skipped"})
SUPPORTED_CONCLUSIONS = FAILURE_CONCLUSIONS | NON_ALERTING_CONCLUSIONS | {"success"}


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
            "User-Agent": "Parket36-Pages-Deploy-Issue-Manager/1.0",
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


def validate_run_id(name: str, value: str) -> str:
    normalized = value.strip()
    if not normalized.isdigit():
        raise RuntimeError(f"{name} must be a numeric GitHub Actions run ID")
    return normalized


def validate_sha(value: str) -> str:
    normalized = value.strip().lower()
    if not SHA_PATTERN.fullmatch(normalized):
        raise RuntimeError("PAGES_DEPLOY_SHA must be a complete 40-character commit SHA")
    return normalized


def normalize_conclusion(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in SUPPORTED_CONCLUSIONS:
        raise RuntimeError(f"unsupported Pages deploy conclusion: {value!r}")
    return normalized


def github_context() -> tuple[str, str, str, str, str, str, str]:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    monitoring_run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    deploy_run_id = os.environ.get("PAGES_DEPLOY_RUN_ID", "").strip()
    deploy_sha = os.environ.get("PAGES_DEPLOY_SHA", "").strip()
    deploy_conclusion = os.environ.get("PAGES_DEPLOY_CONCLUSION", "").strip()

    missing = [
        name
        for name, value in (
            ("GITHUB_REPOSITORY", repository),
            ("GITHUB_TOKEN", token),
            ("GITHUB_RUN_ID", monitoring_run_id),
            ("PAGES_DEPLOY_RUN_ID", deploy_run_id),
            ("PAGES_DEPLOY_SHA", deploy_sha),
            ("PAGES_DEPLOY_CONCLUSION", deploy_conclusion),
        )
        if not value
    ]
    if missing:
        raise RuntimeError("missing GitHub Actions environment: " + ", ".join(missing))
    if not server.startswith("https://"):
        raise RuntimeError("GITHUB_SERVER_URL must use HTTPS")

    return (
        repository,
        token,
        validate_run_id("GITHUB_RUN_ID", monitoring_run_id),
        server,
        validate_run_id("PAGES_DEPLOY_RUN_ID", deploy_run_id),
        validate_sha(deploy_sha),
        normalize_conclusion(deploy_conclusion),
    )


def api_base(repository: str) -> str:
    return f"https://api.github.com/repos/{repository}"


def run_url(server: str, repository: str, run_id: str) -> str:
    return f"{server}/{repository}/actions/runs/{run_id}"


def find_open_issue(repository: str, token: str) -> dict[str, Any] | None:
    issues = api_request(
        "GET",
        api_base(repository) + "/issues?state=open&per_page=100",
        token,
    )
    for issue in issues or []:
        if issue.get("title") == ISSUE_TITLE and "pull_request" not in issue:
            return issue
    return None


def previous_completed_conclusion(
    repository: str,
    token: str,
    current_deploy_run_id: str,
) -> str:
    workflow = quote(WORKFLOW_FILE, safe="")
    response = api_request(
        "GET",
        api_base(repository)
        + f"/actions/workflows/{workflow}/runs?status=completed&per_page=20",
        token,
    )
    for run in (response or {}).get("workflow_runs", []):
        if str(run.get("id", "")) == current_deploy_run_id:
            continue
        conclusion = str(run.get("conclusion") or "").strip().lower()
        if conclusion:
            return conclusion
    return ""


def should_open_issue(current: str, previous: str) -> bool:
    return current in FAILURE_CONCLUSIONS and previous in FAILURE_CONCLUSIONS


def failure_body(
    repository: str,
    server: str,
    monitoring_run_id: str,
    deploy_run_id: str,
    deploy_sha: str,
    conclusion: str,
    previous: str,
) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    return "\n".join(
        [
            "## GitHub Pages deployment failure",
            "",
            "Repeated deployment failure detected.",
            "",
            f"Checked: `{generated}`",
            f"Commit: `{deploy_sha}`",
            f"Current conclusion: `{conclusion}`",
            f"Previous completed conclusion: `{previous or 'unavailable'}`",
            f"Pages deploy: {run_url(server, repository, deploy_run_id)}",
            f"Monitoring run: {run_url(server, repository, monitoring_run_id)}",
            "",
            "The issue body is updated in place after later failed deploys. "
            "A successful Pages deploy adds a recovery comment and closes this issue.",
            "",
            "This monitor does not deploy the site, change Pages settings or expose workflow logs.",
        ]
    )


def recovery_comment(
    repository: str,
    server: str,
    monitoring_run_id: str,
    deploy_run_id: str,
    deploy_sha: str,
) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    return "\n".join(
        [
            "GitHub Pages deployment recovered.",
            "",
            f"Checked: `{generated}`",
            f"Commit: `{deploy_sha}`",
            f"Successful Pages deploy: {run_url(server, repository, deploy_run_id)}",
            f"Monitoring run: {run_url(server, repository, monitoring_run_id)}",
            "",
            "Closing the monitoring issue automatically.",
        ]
    )


def update_failure_issue(
    repository: str,
    token: str,
    issue_number: int,
    body: str,
) -> None:
    api_request(
        "PATCH",
        api_base(repository) + f"/issues/{issue_number}",
        token,
        {"body": body},
    )


def create_failure_issue(repository: str, token: str, body: str) -> int:
    created = api_request(
        "POST",
        api_base(repository) + "/issues",
        token,
        {"title": ISSUE_TITLE, "body": body},
    )
    return int(created["number"])


def close_recovered_issue(
    repository: str,
    token: str,
    issue_number: int,
    comment: str,
) -> None:
    api_request(
        "POST",
        api_base(repository) + f"/issues/{issue_number}/comments",
        token,
        {"body": comment},
    )
    api_request(
        "PATCH",
        api_base(repository) + f"/issues/{issue_number}",
        token,
        {"state": "closed", "state_reason": "completed"},
    )


def handle_event() -> int:
    (
        repository,
        token,
        monitoring_run_id,
        server,
        deploy_run_id,
        deploy_sha,
        conclusion,
    ) = github_context()
    open_issue = find_open_issue(repository, token)

    if conclusion == "success":
        if not open_issue:
            print("No open Pages deploy issue to close")
            return 0
        issue_number = int(open_issue["number"])
        close_recovered_issue(
            repository,
            token,
            issue_number,
            recovery_comment(repository, server, monitoring_run_id, deploy_run_id, deploy_sha),
        )
        print(f"Closed recovered Pages deploy issue #{issue_number}")
        return 0

    if conclusion in NON_ALERTING_CONCLUSIONS:
        print(f"Pages deploy conclusion {conclusion!r} does not change monitoring state")
        return 0

    previous = previous_completed_conclusion(repository, token, deploy_run_id)
    body = failure_body(
        repository,
        server,
        monitoring_run_id,
        deploy_run_id,
        deploy_sha,
        conclusion,
        previous,
    )

    if open_issue:
        issue_number = int(open_issue["number"])
        update_failure_issue(repository, token, issue_number, body)
        print(f"Updated open Pages deploy issue #{issue_number}")
        return 0

    if not should_open_issue(conclusion, previous):
        print(
            "First isolated Pages deploy failure: issue creation deferred until "
            "the next consecutive failed deploy"
        )
        return 0

    issue_number = create_failure_issue(repository, token, body)
    print(f"Created Pages deploy issue #{issue_number}")
    return 0


def self_test() -> int:
    findings: list[str] = []

    if not should_open_issue("failure", "timed_out"):
        findings.append("two failure-like conclusions must open an issue")
    if should_open_issue("failure", "success"):
        findings.append("an isolated failure after success must not open an issue")
    if should_open_issue("success", "failure"):
        findings.append("a successful current deploy must not open an issue")

    sample = failure_body(
        "owner/repo",
        "https://github.com",
        "200",
        "100",
        "a" * 40,
        "failure",
        "timed_out",
    )
    for marker in (
        ISSUE_TITLE.split("] ", 1)[-1],
        "Repeated deployment failure detected.",
        "Commit: `" + "a" * 40 + "`",
        "Current conclusion: `failure`",
        "Previous completed conclusion: `timed_out`",
        "owner/repo/actions/runs/100",
        "owner/repo/actions/runs/200",
        "updated in place",
    ):
        if marker not in sample:
            findings.append(f"failure body missing marker: {marker}")

    recovery = recovery_comment(
        "owner/repo",
        "https://github.com",
        "201",
        "101",
        "b" * 40,
    )
    for marker in (
        "deployment recovered",
        "Commit: `" + "b" * 40 + "`",
        "owner/repo/actions/runs/101",
        "owner/repo/actions/runs/201",
        "Closing the monitoring issue",
    ):
        if marker not in recovery:
            findings.append(f"recovery comment missing marker: {marker}")

    try:
        validate_run_id("test", "123")
        validate_sha("c" * 40)
        normalize_conclusion("startup_failure")
    except RuntimeError as exc:
        findings.append(f"valid identifiers were rejected: {exc}")

    for label, callback in (
        ("non-numeric run ID", lambda: validate_run_id("test", "abc")),
        ("short SHA", lambda: validate_sha("abc123")),
        ("unknown conclusion", lambda: normalize_conclusion("mystery")),
    ):
        try:
            callback()
        except RuntimeError:
            continue
        findings.append(f"{label} was accepted")

    if findings:
        print("Pages deploy issue manager self-test failed:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Pages deploy issue manager self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    return handle_event()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print(f"Pages deploy issue manager error: {exc}", file=sys.stderr)
        sys.exit(1)
