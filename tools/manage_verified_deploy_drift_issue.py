#!/usr/bin/env python3
"""Maintain one issue after repeated verified-deploy drift failures."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ISSUE_TITLE = "[monitoring] verified deploy drift"
WORKFLOW_FILE = "verified-deploy-drift.yml"
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
            "User-Agent": "Parket36-Verified-Deploy-Drift-Issue-Manager/1.0",
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


def validated_context(environment: Mapping[str, str]) -> tuple[str, str, str, str]:
    repository = environment.get("GITHUB_REPOSITORY", "").strip()
    token = environment.get("GITHUB_TOKEN", "").strip()
    run_id = environment.get("GITHUB_RUN_ID", "").strip()
    server = environment.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")

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
    if repository.count("/") != 1 or any(not part for part in repository.split("/")):
        raise RuntimeError(f"invalid GITHUB_REPOSITORY: {repository!r}")
    if not run_id.isdigit():
        raise RuntimeError("GITHUB_RUN_ID must contain digits only")
    if not server.startswith("https://"):
        raise RuntimeError("GITHUB_SERVER_URL must use HTTPS")
    return repository, token, run_id, server


def github_context() -> tuple[str, str, str, str]:
    return validated_context(os.environ)


def api_base(repository: str) -> str:
    return f"https://api.github.com/repos/{repository}"


def run_url(server: str, repository: str, run_id: str) -> str:
    return f"{server}/{repository}/actions/runs/{run_id}"


def find_open_issue(repository: str, token: str) -> dict[str, Any] | None:
    issues = api_request("GET", api_base(repository) + "/issues?state=open&per_page=100", token)
    for issue in issues or []:
        if issue.get("title") == ISSUE_TITLE and "pull_request" not in issue:
            return issue
    return None


def previous_completed_conclusion(repository: str, token: str) -> str:
    workflow = quote(WORKFLOW_FILE, safe="")
    response = api_request(
        "GET",
        api_base(repository) + f"/actions/workflows/{workflow}/runs?status=completed&per_page=10",
        token,
    )
    for run in (response or {}).get("workflow_runs", []):
        conclusion = str(run.get("conclusion") or "").strip().lower()
        if conclusion:
            return conclusion
    return ""


def report_excerpt(path: Path) -> str:
    if not path.exists():
        return "Verified deploy drift report was not created."
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) <= MAX_REPORT_CHARS:
        return text
    return text[:MAX_REPORT_CHARS].rstrip() + "\n\n_Report truncated._"


def failure_body(report: str, workflow_link: str) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    return "\n".join(
        [
            "## Verified deploy drift detected",
            "",
            "The current `main` commit is not the commit recorded by the latest successful post-deploy verification.",
            "",
            f"Checked: `{generated}`",
            f"Workflow run: {workflow_link}",
            "",
            "### Diagnostic report",
            "",
            report,
            "",
            "The issue body is updated in place after later failed checks. A matching verified deploy adds a recovery comment and closes this issue.",
            "",
            "This monitor does not deploy the site, change Pages settings or inspect secrets.",
        ]
    )


def recovery_comment(workflow_link: str) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    return "\n".join(
        [
            "Verified deploy drift recovered.",
            "",
            f"Checked: `{generated}`",
            f"Workflow run: {workflow_link}",
            "",
            "Current `main` now matches the latest successfully verified Pages deploy. Closing the monitoring issue automatically.",
        ]
    )


def update_issue_body(repository: str, token: str, issue_number: int, body: str) -> None:
    api_request(
        "PATCH",
        api_base(repository) + f"/issues/{issue_number}",
        token,
        {"body": body},
    )


def create_issue(repository: str, token: str, body: str) -> int:
    created = api_request(
        "POST",
        api_base(repository) + "/issues",
        token,
        {"title": ISSUE_TITLE, "body": body},
    )
    return int(created["number"])


def close_issue(repository: str, token: str, issue_number: int, comment: str) -> None:
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


def handle_failure(report_path: Path) -> int:
    repository, token, run_id, server = github_context()
    open_issue = find_open_issue(repository, token)
    link = run_url(server, repository, run_id)
    body = failure_body(report_excerpt(report_path), link)

    if open_issue:
        issue_number = int(open_issue["number"])
        update_issue_body(repository, token, issue_number, body)
        print(f"Updated verified deploy drift issue #{issue_number}")
        return 0

    previous = previous_completed_conclusion(repository, token)
    if previous != "failure":
        print(
            "First isolated verified deploy drift: issue creation deferred until "
            "the next consecutive failed run"
        )
        return 0

    issue_number = create_issue(repository, token, body)
    print(f"Created verified deploy drift issue #{issue_number}")
    return 0


def handle_success() -> int:
    repository, token, run_id, server = github_context()
    open_issue = find_open_issue(repository, token)
    if not open_issue:
        print("No open verified deploy drift issue to close")
        return 0

    issue_number = int(open_issue["number"])
    close_issue(
        repository,
        token,
        issue_number,
        recovery_comment(run_url(server, repository, run_id)),
    )
    print(f"Closed recovered verified deploy drift issue #{issue_number}")
    return 0


def self_test() -> int:
    findings: list[str] = []
    report = "# Verified deploy drift report\n\n- Status: **FAIL**"
    body = failure_body(report, "https://github.example/owner/repo/actions/runs/123")
    for marker in (
        "Verified deploy drift detected",
        "current `main` commit",
        "Diagnostic report",
        report,
        "updated in place",
        "does not deploy the site",
    ):
        if marker not in body:
            findings.append(f"failure body missing marker: {marker}")

    recovery = recovery_comment("https://github.example/owner/repo/actions/runs/124")
    for marker in (
        "drift recovered",
        "Current `main` now matches",
        "Closing the monitoring issue",
        "actions/runs/124",
    ):
        if marker not in recovery:
            findings.append(f"recovery comment missing marker: {marker}")

    excerpt = report_excerpt(Path(__file__))
    if not excerpt or len(excerpt) > MAX_REPORT_CHARS + 50:
        findings.append("report excerpt limit is not enforced")

    valid_environment = {
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_TOKEN": "token",
        "GITHUB_RUN_ID": "123",
        "GITHUB_SERVER_URL": "https://github.example",
    }
    try:
        validated_context(valid_environment)
    except RuntimeError as exc:
        findings.append(f"valid workflow context rejected: {exc}")

    invalid_contexts = (
        {**valid_environment, "GITHUB_RUN_ID": "run-123"},
        {**valid_environment, "GITHUB_SERVER_URL": "http://github.example"},
    )
    for context in invalid_contexts:
        try:
            validated_context(context)
        except RuntimeError:
            continue
        findings.append(f"invalid workflow context accepted: {context}")

    if ISSUE_TITLE != "[monitoring] verified deploy drift":
        findings.append("verified deploy drift issue title changed")
    if WORKFLOW_FILE != "verified-deploy-drift.yml":
        findings.append("verified deploy drift workflow file changed")

    if findings:
        print("Verified deploy drift issue manager self-test failed:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("Verified deploy drift issue manager self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", nargs="?", choices=("failure", "success"))
    parser.add_argument("--report", default="verified-deploy-drift-report.md")
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
        print(f"Verified deploy drift issue manager error: {exc}", file=sys.stderr)
        sys.exit(1)
