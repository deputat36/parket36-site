#!/usr/bin/env python3
"""Mark the managed production lead readiness snapshot stale after main advances."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_VERSION = "2022-11-28"
ISSUE_NUMBER = 373
COMMENT_MARKER = "<!-- parket36-production-lead-launch-readiness -->"
STALE_START = "<!-- parket36-production-lead-launch-readiness-stale:start -->"
STALE_END = "<!-- parket36-production-lead-launch-readiness-stale:end -->"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SOURCE_RE = re.compile(r"(?m)^Source commit: `(?P<sha>[0-9a-f]{40})`$")


def normalize_commit_sha(value: str) -> str:
    sha = value.strip()
    if not COMMIT_RE.fullmatch(sha):
        raise ValueError("commit SHA must contain exactly 40 lowercase hexadecimal characters")
    return sha


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
            "User-Agent": "Parket36-Production-Lead-Readiness-Stale/1.0",
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


def github_context() -> tuple[str, str, str, str, str]:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    current_sha = os.environ.get("GITHUB_SHA", "").strip()
    missing = [
        name
        for name, value in (
            ("GITHUB_REPOSITORY", repository),
            ("GITHUB_TOKEN", token),
            ("GITHUB_RUN_ID", run_id),
            ("GITHUB_SHA", current_sha),
        )
        if not value
    ]
    if missing:
        raise RuntimeError("missing GitHub Actions environment: " + ", ".join(missing))
    return repository, token, run_id, server, normalize_commit_sha(current_sha)


def api_base(repository: str) -> str:
    return f"https://api.github.com/repos/{repository}"


def run_url(server: str, repository: str, run_id: str) -> str:
    return f"{server}/{repository}/actions/runs/{run_id}"


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


def find_managed_comment(comments: list[dict[str, Any]]) -> dict[str, Any] | None:
    for comment in comments:
        if COMMENT_MARKER in str(comment.get("body") or ""):
            return comment
    return None


def extract_source_commit(body: str) -> str | None:
    match = SOURCE_RE.search(body)
    return match.group("sha") if match else None


def remove_stale_banner(body: str) -> str:
    pattern = re.compile(
        rf"\n?{re.escape(STALE_START)}.*?{re.escape(STALE_END)}\n?",
        re.DOTALL,
    )
    cleaned = pattern.sub("\n", body)
    return cleaned.strip()


def stale_banner(*, source_sha: str | None, current_sha: str, run_link: str) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    source_text = f"`{source_sha}`" if source_sha else "не определён"
    return "\n".join(
        [
            STALE_START,
            "> [!WARNING]",
            "> Этот readiness-снимок устарел и не должен использоваться для deploy.",
            ">",
            f"> Проверенный commit: {source_text}",
            f"> Текущий `main`: `{current_sha}`",
            "> Повторно запустите `Production lead launch readiness` из актуального `main`.",
            f"> Проверено: `{generated}` · Workflow run: {run_link}",
            STALE_END,
        ]
    )


def mark_body_stale(body: str, *, current_sha: str, run_link: str) -> tuple[str, bool]:
    current = normalize_commit_sha(current_sha)
    if COMMENT_MARKER not in body:
        raise ValueError("managed readiness comment marker is missing")

    source_sha = extract_source_commit(body)
    clean = remove_stale_banner(body)
    if source_sha == current:
        return clean, clean != body.strip()

    lines = clean.splitlines()
    marker_index = lines.index(COMMENT_MARKER)
    banner = stale_banner(source_sha=source_sha, current_sha=current, run_link=run_link)
    updated = lines[: marker_index + 1] + [banner] + lines[marker_index + 1 :]
    text = "\n".join(updated).strip()
    return text, text != body.strip()


def mark_snapshot_stale(current_sha: str | None = None) -> int:
    repository, token, run_id, server, env_sha = github_context()
    current = normalize_commit_sha(current_sha) if current_sha else env_sha
    managed = find_managed_comment(list_issue_comments(repository, token))
    if not managed:
        print(f"No managed production readiness snapshot exists on issue #{ISSUE_NUMBER}; nothing to mark stale")
        return 0

    body = str(managed.get("body") or "")
    updated, changed = mark_body_stale(
        body,
        current_sha=current,
        run_link=run_url(server, repository, run_id),
    )
    if not changed:
        print(f"Managed production readiness snapshot already matches current main {current}")
        return 0

    comment_id = int(managed["id"])
    api_request(
        "PATCH",
        api_base(repository) + f"/issues/comments/{comment_id}",
        token,
        {"body": updated},
    )
    print(f"Marked production readiness snapshot comment {comment_id} stale for main {current}")
    return 0


def self_test() -> int:
    failures: list[str] = []
    old_sha = "a" * 40
    current_sha = "b" * 40
    base = "\n".join(
        [
            COMMENT_MARKER,
            "## Последняя готовность production-заявок",
            "",
            f"Source commit: `{old_sha}`",
            "Readiness level: **LAUNCH_READY**",
        ]
    )

    updated, changed = mark_body_stale(
        base,
        current_sha=current_sha,
        run_link="https://example.test/actions/runs/1",
    )
    for marker in (STALE_START, STALE_END, old_sha, current_sha, "не должен использоваться для deploy"):
        if marker not in updated:
            failures.append(f"stale body missing marker: {marker}")
    if not changed:
        failures.append("stale body was not reported as changed")

    repeated, repeated_changed = mark_body_stale(
        updated,
        current_sha=current_sha,
        run_link="https://example.test/actions/runs/1",
    )
    if repeated != updated or repeated_changed:
        failures.append("stale marking is not idempotent for the same main commit and run link")
    if repeated.count(STALE_START) != 1 or repeated.count(STALE_END) != 1:
        failures.append("stale banner was duplicated")

    current_body = base.replace(old_sha, current_sha)
    cleaned, cleaned_changed = mark_body_stale(
        current_body,
        current_sha=current_sha,
        run_link="https://example.test/actions/runs/2",
    )
    if cleaned != current_body or cleaned_changed:
        failures.append("current readiness snapshot was changed")

    legacy = base.replace(f"Source commit: `{old_sha}`\n", "")
    legacy_updated, _ = mark_body_stale(
        legacy,
        current_sha=current_sha,
        run_link="https://example.test/actions/runs/3",
    )
    if "Проверенный commit: не определён" not in legacy_updated:
        failures.append("legacy snapshot without source commit was not marked stale")

    for invalid in ("", "abc", "A" * 40, "g" * 40, "1" * 39, "1" * 41):
        try:
            normalize_commit_sha(invalid)
        except ValueError:
            pass
        else:
            failures.append(f"invalid commit SHA was accepted: {invalid!r}")

    try:
        mark_body_stale(
            "ordinary comment",
            current_sha=current_sha,
            run_link="https://example.test/actions/runs/4",
        )
    except ValueError:
        pass
    else:
        failures.append("ordinary comment was accepted as managed readiness snapshot")

    for forbidden in ("+79990000000", "token-value", "digest:", "hash:"):
        if forbidden in updated:
            failures.append(f"stale banner contains protected-data marker: {forbidden}")

    if failures:
        print("Production lead readiness stale marker self-test failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Production lead readiness stale marker self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-commit")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    return mark_snapshot_stale(args.current_commit)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"Production lead readiness stale marker error: {exc}", file=sys.stderr)
        sys.exit(1)
