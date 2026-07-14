#!/usr/bin/env python3
"""Create one monitoring issue for lead endpoint failures and close it on recovery."""

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
MAX_REPORT_CHARS = 8_000
MONITORS = {
    "protected": {
        "title": "[monitoring] production lead endpoint failure",
        "heading": "Production lead endpoint failure",
        "failure": "The protected healthcheck could not confirm that the public lead function is ready.",
        "recovery": "The protected test-mode request confirmed the function and required tables.",
        "safety": "The report never contains the health token and the check does not create a lead.",
        "default_report": "lead-endpoint-health.md",
    },
    "preflight": {
        "title": "[monitoring] public lead preflight failure",
        "heading": "Public lead endpoint preflight failure",
        "failure": "The public OPTIONS request could not confirm endpoint routing and the browser CORS contract for parket36.ru.",
        "recovery": "The public OPTIONS request confirmed endpoint routing and the required CORS headers.",
        "safety": "The check uses OPTIONS only, sends no form data, requires no secret and does not create a lead.",
        "default_report": "lead-endpoint-preflight.md",
    },
}


def monitor_config(kind: str) -> dict[str, str]:
    return MONITORS[kind]


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
            "User-Agent": "Parket36-Lead-Endpoint-Issue-Manager/2.0",
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


def find_open_issue(repository: str, token: str, title: str) -> dict[str, Any] | None:
    issues = api_request("GET", api_base(repository) + "/issues?state=open&per_page=100", token)
    for issue in issues or []:
        if issue.get("title") == title and "pull_request" not in issue:
            return issue
    return None


def report_excerpt(path: Path, kind: str) -> str:
    if not path.exists():
        return f"{monitor_config(kind)['heading']} report was not created."
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if len(text) <= MAX_REPORT_CHARS:
        return text
    return text[:MAX_REPORT_CHARS].rstrip() + "\n\n_Report truncated._"


def run_url(server: str, repository: str, run_id: str) -> str:
    return f"{server}/{repository}/actions/runs/{run_id}"


def failure_body(kind: str, report: str, run_link: str) -> str:
    config = monitor_config(kind)
    generated = datetime.now(timezone.utc).isoformat()
    return "\n".join(
        [
            f"## {config['heading']}",
            "",
            config["failure"],
            "",
            f"Checked: `{generated}`",
            f"Workflow run: {run_link}",
            "",
            "### Diagnostic report",
            "",
            report,
            "",
            "This issue is maintained automatically and will close after a successful check of the same kind.",
            config["safety"],
        ]
    )


def recovery_comment(kind: str, run_link: str) -> str:
    config = monitor_config(kind)
    generated = datetime.now(timezone.utc).isoformat()
    return "\n".join(
        [
            f"{config['heading']} recovered.",
            "",
            f"Checked: `{generated}`",
            f"Workflow run: {run_link}",
            "",
            config["recovery"],
            "Closing automatically.",
        ]
    )


def add_comment(repository: str, token: str, issue_number: int, body: str) -> None:
    api_request(
        "POST",
        api_base(repository) + f"/issues/{issue_number}/comments",
        token,
        {"body": body},
    )


def handle_failure(kind: str, report_path: Path) -> int:
    repository, token, run_id, server = github_context()
    config = monitor_config(kind)
    issue = find_open_issue(repository, token, config["title"])
    body = failure_body(kind, report_excerpt(report_path, kind), run_url(server, repository, run_id))
    if issue:
        add_comment(repository, token, int(issue["number"]), body)
        print(f"Updated {kind} lead endpoint issue #{issue['number']}")
        return 0

    created = api_request(
        "POST",
        api_base(repository) + "/issues",
        token,
        {"title": config["title"], "body": body},
    )
    print(f"Created {kind} lead endpoint issue #{created['number']}")
    return 0


def handle_success(kind: str) -> int:
    repository, token, run_id, server = github_context()
    config = monitor_config(kind)
    issue = find_open_issue(repository, token, config["title"])
    if not issue:
        print(f"No open {kind} lead endpoint issue to close")
        return 0

    issue_number = int(issue["number"])
    add_comment(repository, token, issue_number, recovery_comment(kind, run_url(server, repository, run_id)))
    api_request(
        "PATCH",
        api_base(repository) + f"/issues/{issue_number}",
        token,
        {"state": "closed", "state_reason": "completed"},
    )
    print(f"Closed {kind} lead endpoint issue #{issue_number}")
    return 0


def self_test() -> int:
    failures: list[str] = []
    report = "| `allow_origin` | FAIL | wrong origin |"

    for kind in MONITORS:
        failure = failure_body(kind, report, "https://example.test/actions/runs/1")
        config = monitor_config(kind)
        for marker in (config["heading"], report, config["safety"], "same kind"):
            if marker not in failure:
                failures.append(f"{kind} failure body missing marker: {marker}")

        recovery = recovery_comment(kind, "https://example.test/actions/runs/2")
        for marker in ("recovered", config["recovery"], "Closing automatically"):
            if marker not in recovery:
                failures.append(f"{kind} recovery comment missing marker: {marker}")

        excerpt = report_excerpt(Path(__file__), kind)
        if not excerpt or len(excerpt) > MAX_REPORT_CHARS + 50:
            failures.append(f"{kind} report excerpt limit is invalid")

    if MONITORS["protected"]["title"] == MONITORS["preflight"]["title"]:
        failures.append("monitoring issue titles must be distinct")

    if failures:
        print("Production lead endpoint issue manager self-test failed:")
        for failure_item in failures:
            print(f"  - {failure_item}")
        return 1

    print("Production lead endpoint issue manager self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", nargs="?", choices=("failure", "success"))
    parser.add_argument("--kind", choices=tuple(MONITORS), default="protected")
    parser.add_argument("--report")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if args.state == "failure":
        report = args.report or monitor_config(args.kind)["default_report"]
        return handle_failure(args.kind, Path(report))
    if args.state == "success":
        return handle_success(args.kind)
    parser.error("state is required unless --self-test is used")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print(f"Production lead endpoint issue manager error: {exc}", file=sys.stderr)
        sys.exit(1)
