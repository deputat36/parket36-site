#!/usr/bin/env python3
"""Create one issue after repeated IndexNow failures and close it on recovery."""

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

ISSUE_TITLE = "[monitoring] IndexNow notification failure"
WORKFLOW_FILE = "indexnow.yml"
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
            "User-Agent": "Parket36-IndexNow-Issue-Manager/1.0",
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


def find_open_issue(repository: str, token: str) -> dict[str, Any] | None:
    issues = api_request("GET", api_base(repository) + "/issues?state=open&per_page=100", token)
    for issue in issues or []:
        if issue.get("title") == ISSUE_TITLE and "pull_request" not in issue:
            return issue
    return None


def previous_completed_conclusion(repository: str, token: str, run_id: str) -> str:
    workflow = quote(WORKFLOW_FILE, safe="")
    runs = api_request(
        "GET",
        api_base(repository) + f"/actions/workflows/{workflow}/runs?status=completed&per_page=10",
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
        return "IndexNow report was not created."
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) <= MAX_REPORT_CHARS:
        return text
    return text[:MAX_REPORT_CHARS].rstrip() + "\n\n_Report truncated._"


def run_url(server: str, repository: str, run_id: str) -> str:
    return f"{server}/{repository}/actions/runs/{run_id}"


def failure_body(report: str, run_link: str) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    return "\n".join(
        [
            "## IndexNow notification failure",
            "",
            "Repeated failure detected.",
            "",
            f"Checked: `{generated}`",
            f"Workflow run: {run_link}",
            "",
            "### Diagnostic report",
            "",
            report,
            "",
            "This issue is maintained automatically and will close after a successful IndexNow run.",
            "A failed notification does not roll back the already completed GitHub Pages deployment.",
        ]
    )


def recovery_comment(run_link: str) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    return "\n".join(
        [
            "IndexNow notification recovered.",
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
        api_base(repository) + f"/issues/{issue_number}/comments",
        token,
        {"body": body},
    )


def handle_failure(report_path: Path) -> int:
    repository, token, current_run_id, server = github_context()
    open_issue = find_open_issue(repository, token)
    link = run_url(server, repository, current_run_id)
    report = report_excerpt(report_path)

    if open_issue:
        add_comment(repository, token, int(open_issue["number"]), failure_body(report, link))
        print(f"Updated open IndexNow issue #{open_issue['number']}")
        return 0

    previous = previous_completed_conclusion(repository, token, current_run_id)
    if previous != "failure":
        print("First isolated IndexNow failure: issue creation deferred until the next consecutive failed run")
        return 0

    created = api_request(
        "POST",
        api_base(repository) + "/issues",
        token,
        {"title": ISSUE_TITLE, "body": failure_body(report, link)},
    )
    print(f"Created IndexNow issue #{created['number']}")
    return 0


def handle_success() -> int:
    repository, token, current_run_id, server = github_context()
    open_issue = find_open_issue(repository, token)
    if not open_issue:
        print("No open IndexNow issue to close")
        return 0

    issue_number = int(open_issue["number"])
    link = run_url(server, repository, current_run_id)
    add_comment(repository, token, issue_number, recovery_comment(link))
    api_request(
        "PATCH",
        api_base(repository) + f"/issues/{issue_number}",
        token,
        {"state": "closed", "state_reason": "completed"},
    )
    print(f"Closed recovered IndexNow issue #{issue_number}")
    return 0


def self_test() -> int:
    findings: list[str] = []
    sample = failure_body("Result: **FAIL**", "https://example.test/actions/runs/1")
    for marker in (
        "Repeated failure detected.",
        "Diagnostic report",
        "Result: **FAIL**",
        "maintained automatically",
        "does not roll back",
    ):
        if marker not in sample:
            findings.append(f"failure body missing marker: {marker}")

    recovery = recovery_comment("https://example.test/actions/runs/2")
    if "recovered" not in recovery or "Closing" not in recovery:
        findings.append("recovery comment is incomplete")

    excerpt = report_excerpt(Path(__file__))
    if not excerpt or len(excerpt) > MAX_REPORT_CHARS + 50:
        findings.append("report excerpt limit is not enforced")

    if ISSUE_TITLE != "[monitoring] IndexNow notification failure":
        findings.append("issue title changed unexpectedly")
    if WORKFLOW_FILE != "indexnow.yml":
        findings.append("workflow filename changed unexpectedly")

    if findings:
        print("IndexNow issue-manager self-test failed:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("IndexNow issue-manager self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", nargs="?", choices=("failure", "success"))
    parser.add_argument("--report", default="indexnow-report.md")
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
        print(f"IndexNow issue-manager error: {exc}", file=sys.stderr)
        sys.exit(1)
