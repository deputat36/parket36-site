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
STALE_MAIN_RE = re.compile(
    rf"{re.escape(STALE_START)}.*?> Текущий `main`: `(?P<sha>[0-9a-f]{{40}})`.*?{re.escape(STALE_END)}",
    re.DOTALL,
)


def normalize_sha(value: str) -> str:
    sha = value.strip()
    if not COMMIT_RE.fullmatch(sha):
        raise ValueError("commit SHA must contain exactly 40 lowercase hexadecimal characters")
    return sha


def api_request(method: str, url: str, token: str, payload: dict[str, Any] | None = None) -> Any:
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


def api_base(repository: str) -> str:
    return f"https://api.github.com/repos/{repository}"


def find_managed_comment(comments: list[dict[str, Any]]) -> dict[str, Any] | None:
    for comment in comments:
        if COMMENT_MARKER in str(comment.get("body") or ""):
            return comment
    return None


def list_comments(repository: str, token: str) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    for page in range(1, 11):
        batch = api_request(
            "GET",
            api_base(repository) + f"/issues/{ISSUE_NUMBER}/comments?per_page=100&page={page}",
            token,
        ) or []
        comments.extend(batch)
        if len(batch) < 100:
            break
    return comments


def source_sha(body: str) -> str | None:
    match = SOURCE_RE.search(body)
    return match.group("sha") if match else None


def stale_main_sha(body: str) -> str | None:
    match = STALE_MAIN_RE.search(body)
    return match.group("sha") if match else None


def remove_stale_banner(body: str) -> str:
    pattern = re.compile(
        rf"\n?{re.escape(STALE_START)}.*?{re.escape(STALE_END)}\n?",
        re.DOTALL,
    )
    return pattern.sub("\n", body).strip()


def build_banner(snapshot_sha: str | None, current_sha: str, run_link: str) -> str:
    checked = datetime.now(timezone.utc).isoformat()
    snapshot = f"`{snapshot_sha}`" if snapshot_sha else "не определён"
    return "\n".join(
        [
            STALE_START,
            "> [!WARNING]",
            "> Этот readiness-снимок устарел и не должен использоваться для deploy.",
            ">",
            f"> Проверенный commit: {snapshot}",
            f"> Текущий `main`: `{current_sha}`",
            "> Повторно запустите `Production lead launch readiness` из актуального `main`.",
            f"> Проверено: `{checked}` · Workflow run: {run_link}",
            STALE_END,
        ]
    )


def mark_body(body: str, current_sha: str, run_link: str) -> tuple[str, bool]:
    current = normalize_sha(current_sha)
    if COMMENT_MARKER not in body:
        raise ValueError("managed readiness comment marker is missing")
    if stale_main_sha(body) == current:
        return body.strip(), False

    snapshot = source_sha(body)
    clean = remove_stale_banner(body)
    if snapshot == current:
        return clean, clean != body.strip()

    lines = clean.splitlines()
    marker_index = lines.index(COMMENT_MARKER)
    updated = lines[: marker_index + 1] + [build_banner(snapshot, current, run_link)] + lines[marker_index + 1 :]
    text = "\n".join(updated).strip()
    return text, text != body.strip()


def mark_snapshot(current_sha: str | None = None) -> int:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    env_sha = os.environ.get("GITHUB_SHA", "").strip()
    missing = [
        name
        for name, value in (
            ("GITHUB_REPOSITORY", repository),
            ("GITHUB_TOKEN", token),
            ("GITHUB_RUN_ID", run_id),
            ("GITHUB_SHA", env_sha),
        )
        if not value
    ]
    if missing:
        raise RuntimeError("missing GitHub Actions environment: " + ", ".join(missing))

    current = normalize_sha(current_sha or env_sha)
    managed = find_managed_comment(list_comments(repository, token))
    if not managed:
        print(f"No managed production readiness snapshot exists on issue #{ISSUE_NUMBER}; nothing to mark stale")
        return 0

    updated, changed = mark_body(
        str(managed.get("body") or ""),
        current,
        f"{server}/{repository}/actions/runs/{run_id}",
    )
    if not changed:
        print(f"Managed production readiness snapshot already reflects current main {current}")
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

    updated, changed = mark_body(base, current_sha, "https://example.test/actions/runs/1")
    for marker in (STALE_START, STALE_END, old_sha, current_sha, "не должен использоваться для deploy"):
        if marker not in updated:
            failures.append(f"stale body missing marker: {marker}")
    if not changed:
        failures.append("stale body was not reported as changed")

    repeated, repeated_changed = mark_body(updated, current_sha, "https://example.test/actions/runs/1")
    if repeated != updated or repeated_changed:
        failures.append("stale marking is not idempotent for the same main commit")
    if repeated.count(STALE_START) != 1 or repeated.count(STALE_END) != 1:
        failures.append("stale banner was duplicated")

    current_body = base.replace(old_sha, current_sha)
    clean, clean_changed = mark_body(current_body, current_sha, "https://example.test/actions/runs/2")
    if clean != current_body or clean_changed:
        failures.append("current readiness snapshot was changed")

    legacy = base.replace(f"Source commit: `{old_sha}`\n", "")
    legacy_updated, _ = mark_body(legacy, current_sha, "https://example.test/actions/runs/3")
    if "Проверенный commit: не определён" not in legacy_updated:
        failures.append("legacy snapshot without source commit was not marked stale")

    for invalid in ("", "abc", "A" * 40, "g" * 40, "1" * 39, "1" * 41):
        try:
            normalize_sha(invalid)
        except ValueError:
            pass
        else:
            failures.append(f"invalid commit SHA was accepted: {invalid!r}")

    try:
        mark_body("ordinary comment", current_sha, "https://example.test/actions/runs/4")
    except ValueError:
        pass
    else:
        failures.append("ordinary comment was accepted as managed readiness snapshot")

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
    return mark_snapshot(args.current_commit)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"Production lead readiness stale marker error: {exc}", file=sys.stderr)
        sys.exit(1)
