#!/usr/bin/env python3
"""Create one issue after repeated live-site failures and close it on recovery."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ISSUE_TITLE = "[monitoring] parket36.ru live health failure"
WORKFLOW_FILE = "live-site-health.yml"
API_VERSION = "2022-11-28"
MAX_REPORT_CHARS = 8_000


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
            "User-Agent": "Parket36-Live-Health-Issue-Manager/1.0",
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


def issue_api_base(repository: str) -> str:
    return f"https://api.github.com/repos/{repository}"


def find_open_issue(repository: str, token: str) -> dict[str, Any] | None:
    issues = api_request(
        "GET",
        issue_api_base(repository) + "/issues?state=open&per_page=100",
        token,
    )
    for issue in issues or []:
        if issue.get("title") == ISSUE_TITLE and "pull_request" not in issue:
            return issue
    return None


def previous_completed_conclusion(repository: str, token: str, run_id: str) -> str:
    workflow = quote(WORKFLOW_FILE, safe="")
    runs = api_request(
        "GET",
        issue_api_base(repository)
        + f"/actions/workflows/{workflow}/runs?status=completed&per_page=10",
        token,
    )
    for run in (runs or {}).get("workflow_runs", []):
        if str(run.get("id", "")) == run_id:
            continue
        conclusion = str(run.get("conclusion") or "").lower()
        if conclusion:
            return conclusion
    return ""


def report_excerpt(path: Path) -> str:
    if not path.exists():
        return "Live health report was not created."
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) <= MAX_REPORT_CHARS:
        return text
    return text[:MAX_REPORT_CHARS].rstrip() + "\n\n_Report truncated._"


def run_url(server: str, repository: str, run_id: str) -> str:
    return f"{server}/{repository}/actions/runs/{run_id}"


def failure_body(report: str, run_link: str, repeated: bool) -> str:
    state = "Repeated failure detected." if repeated else "Live health failure detected."
    generated = datetime.now(timezone.utc).isoformat()
    return "\n".join(
        [
            "## parket36.ru live health failure",
            "",
            state,
            "",
            f"Checked: `{generated}`",
            f"Workflow run: {run_link}",
            "",
            "### Diagnostic report",
            "",
            report,
            "",
            "This issue is maintained automatically. It will be closed after a successful live-health run.",
        ]
    )


def recovery_comment(run_link: str) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    return "\n".join(
        [
            "Live health recovered.",
            "",
            f"Checked: `{generated}`",
            f"Workflow run: {run_link}",
            "",
            "Closing the monitoring issue automatically.",
        ]
    )


def add_comment(repository: str, token: str, issue_number: int, body: str) -> None:
    api_request(
        "POST",
        issue_api_base(repository) + f"/issues/{issue_number}/comments",
        token,
        {"body": body},
    )


def handle_failure(report_path: Path) -> int:
    repository, token, current_run_id, server = github_context()
    open_issue = find_open_issue(repository, token)
    previous = previous_completed_conclusion(repository, token, current_run_id)
    link = run_url(server, repository, current_run_id)
    report = report_excerpt(report_path)

    if open_issue:
        body = failure_body(report, link, repeated=True)
        add_comment(repository, token, int(open_issue["number"]), body)
        print(f"Updated open live-health issue #{open_issue['number']}")
        return 0

    if previous != "failure":
        print(
            "First isolated live-health failure: issue creation deferred until "
            "the next consecutive failed run"
        )
        return 0

    body = failure_body(report, link, repeated=True)
    created = api_request(
        "POST",
        issue_api_base(repository) + "/issues",
        token,
        {"title": ISSUE_TITLE, "body": body},
    )
    print(f"Created live-health issue #{created['number']}")
    return 0


def handle_success() -> int:
    repository, token, current_run_id, server = github_context()
    open_issue = find_open_issue(repository, token)
    if not open_issue:
        print("No open live-health issue to close")
        return 0

    link = run_url(server, repository, current_run_id)
    issue_number = int(open_issue["number"])
    add_comment(repository, token, issue_number, recovery_comment(link))
    api_request(
        "PATCH",
        issue_api_base(repository) + f"/issues/{issue_number}",
        token,
        {"state": "closed", "state_reason": "completed"},
    )
    print(f"Closed recovered live-health issue #{issue_number}")
    return 0


def self_test() -> int:
    failures: list[str] = []

    sample = failure_body("| DNS | FAIL | no address |", "https://example.test/run/1", True)
    required = [
        ISSUE_TITLE.split("] ", 1)[-1],
        "Repeated failure detected.",
        "Diagnostic report",
        "| DNS | FAIL | no address |",
        "maintained automatically",
    ]
    for marker in required:
        if marker not in sample:
            failures.append(f"failure body missing marker: {marker}")

    with_report = report_excerpt(Path(__file__))
    if not with_report or len(with_report) > MAX_REPORT_CHARS + 50:
        failures.append("report excerpt limit is not enforced")

    if failure_body("x", "https://example.test", False).count("Live health failure detected.") != 1:
        failures.append("isolated failure wording is invalid")

    recovery = recovery_comment("https://example.test/run/2")
    if "Live health recovered." not in recovery or "Closing" not in recovery:
        failures.append("recovery comment is incomplete")

    if failures:
        print("Live-health issue manager self-test failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("Live-health issue manager self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", nargs="?", choices=("failure", "success"))
    parser.add_argument("--report", default="live-health-report.md")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.state == "failure":
        return handle_failure(Path(args.report))
    if args.state == "success":
        return handle_success()

    parser.error("state is required unless --self-test is used")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print(f"Live-health issue manager error: {exc}", file=sys.stderr)
        sys.exit(1)
