#!/usr/bin/env python3
"""Compare current main with the durable ledger of the latest verified Pages deploy."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
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
LEDGER_SHA_PATTERN = re.compile(r"^Опубликованный commit: `([0-9a-f]{40})`$", re.MULTILINE)
MAX_COMMENT_PAGES = 50


def api_request(method: str, url: str, token: str) -> Any:
    request = Request(
        url,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Parket36-Verified-Deploy-Drift-Check/1.0",
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


def validate_sha(name: str, value: str) -> str:
    normalized = value.strip().lower()
    if not SHA_PATTERN.fullmatch(normalized):
        raise RuntimeError(f"{name} must be a full lowercase 40-character commit SHA")
    return normalized


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


def issue_api_base(repository: str) -> str:
    return f"https://api.github.com/repos/{repository}"


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


def find_ledger_comment(comments: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [comment for comment in comments if COMMENT_MARKER in str(comment.get("body") or "")]
    if len(matches) > 1:
        ids = ", ".join(str(comment.get("id")) for comment in matches)
        raise RuntimeError(f"multiple live verification ledger comments found: {ids}")
    return matches[0] if matches else None


def extract_ledger_sha(body: str) -> str:
    if body.count(COMMENT_MARKER) != 1:
        raise RuntimeError("ledger comment must contain exactly one hidden marker")
    matches = LEDGER_SHA_PATTERN.findall(body)
    if len(matches) != 1:
        raise RuntimeError("ledger comment must contain exactly one published commit line")
    return validate_sha("ledger commit", matches[0])


def evaluate_drift(
    current_sha: str,
    comments: list[dict[str, Any]],
) -> tuple[bool, str | None, str]:
    current = validate_sha("current main commit", current_sha)
    ledger = find_ledger_comment(comments)
    if not ledger:
        return False, None, "live verification ledger comment is missing"

    body = str(ledger.get("body") or "")
    ledger_sha = extract_ledger_sha(body)
    if ledger_sha != current:
        return (
            False,
            ledger_sha,
            "current main commit does not match the latest verified Pages deploy",
        )
    return True, ledger_sha, "current main commit matches the latest verified Pages deploy"


def report_text(
    *,
    passed: bool,
    current_sha: str,
    ledger_sha: str | None,
    reason: str,
    repository: str,
    server: str,
    run_id: str,
    generated: str | None = None,
) -> str:
    checked = generated or datetime.now(timezone.utc).isoformat()
    status = "PASS" if passed else "FAIL"
    ledger_value = f"`{ledger_sha}`" if ledger_sha else "unavailable"
    repository_url = f"{server}/{repository}"
    return "\n".join(
        [
            "# Verified deploy drift report",
            "",
            f"- Status: **{status}**",
            f"- Checked: `{checked}`",
            f"- Current main commit: `{current_sha}`",
            f"- Latest verified deploy commit: {ledger_value}",
            f"- Roadmap ledger: {repository_url}/issues/{ISSUE_NUMBER}",
            f"- Workflow run: {repository_url}/actions/runs/{run_id}",
            f"- Result: {reason}",
            "",
            "The check is read-only. It does not deploy the site, change Pages settings or inspect secrets.",
        ]
    ) + "\n"


def run_check(current_sha: str, report_path: Path) -> int:
    repository, token, run_id, server = validated_context(os.environ)
    current = validate_sha("current main commit", current_sha)
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

    passed, ledger_sha, reason = evaluate_drift(current, load_all_comments(base, token))
    report_path.write_text(
        report_text(
            passed=passed,
            current_sha=current,
            ledger_sha=ledger_sha,
            reason=reason,
            repository=repository,
            server=server,
            run_id=run_id,
        ),
        encoding="utf-8",
    )
    print(reason)
    return 0 if passed else 1


def self_test() -> int:
    findings: list[str] = []
    current = "a" * 40
    other = "b" * 40

    matching_body = "\n".join(
        [
            COMMENT_MARKER,
            "## Последняя подтверждённая публикация parket36.ru",
            f"Опубликованный commit: `{current}`",
        ]
    )
    mismatch_body = matching_body.replace(current, other)

    passed, ledger_sha, reason = evaluate_drift(current, [{"id": 1, "body": matching_body}])
    if not passed or ledger_sha != current or "matches" not in reason:
        findings.append("matching main and ledger commits must pass")

    passed, ledger_sha, reason = evaluate_drift(current, [{"id": 1, "body": mismatch_body}])
    if passed or ledger_sha != other or "does not match" not in reason:
        findings.append("mismatched main and ledger commits must fail")

    passed, ledger_sha, reason = evaluate_drift(current, [])
    if passed or ledger_sha is not None or "missing" not in reason:
        findings.append("missing ledger comment must fail")

    try:
        evaluate_drift(
            current,
            [
                {"id": 1, "body": matching_body},
                {"id": 2, "body": matching_body},
            ],
        )
    except RuntimeError:
        pass
    else:
        findings.append("duplicate ledger comments must fail closed")

    malformed = COMMENT_MARKER + "\nОпубликованный commit: `abc123`"
    try:
        evaluate_drift(current, [{"id": 1, "body": malformed}])
    except RuntimeError:
        pass
    else:
        findings.append("malformed ledger commit must fail closed")

    report = report_text(
        passed=False,
        current_sha=current,
        ledger_sha=other,
        reason="test mismatch",
        repository="owner/repo",
        server="https://github.example",
        run_id="123",
        generated="2026-07-16T12:00:00+00:00",
    )
    for marker in (
        "Verified deploy drift report",
        "Status: **FAIL**",
        f"Current main commit: `{current}`",
        f"Latest verified deploy commit: `{other}`",
        "github.example/owner/repo/issues/308",
        "github.example/owner/repo/actions/runs/123",
        "read-only",
    ):
        if marker not in report:
            findings.append(f"report missing marker: {marker}")

    valid_environment = {
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_TOKEN": "token",
        "GITHUB_RUN_ID": "123",
        "GITHUB_SERVER_URL": "https://github.example",
    }
    try:
        validated_context(valid_environment)
        validate_sha("test", current)
    except RuntimeError as exc:
        findings.append(f"valid context rejected: {exc}")

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

    try:
        validate_sha("test", "abc123")
    except RuntimeError:
        pass
    else:
        findings.append("short SHA was accepted")

    if ISSUE_NUMBER != 308 or EXPECTED_TITLE != "Автономная дорожная карта улучшения Паркет36":
        findings.append("roadmap issue guard changed")

    if findings:
        print("Verified deploy drift self-test failed:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("Verified deploy drift self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-sha")
    parser.add_argument("--report", default="verified-deploy-drift-report.md")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.current_sha:
        parser.error("--current-sha is required unless --self-test is used")
    return run_check(args.current_sha, Path(args.report))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as exc:
        print(f"Verified deploy drift check error: {exc}", file=sys.stderr)
        sys.exit(1)
