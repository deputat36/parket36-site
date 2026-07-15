#!/usr/bin/env python3
"""Verify that a stamped readiness summary still matches the current main ref."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_VERSION = "2022-11-28"
DEFAULT_REPORT = Path("production-lead-launch-readiness.md")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SOURCE_RE = re.compile(r"(?m)^Source commit: `(?P<sha>[0-9a-f]{40})`$")


def normalize_commit_sha(value: str) -> str:
    sha = value.strip()
    if not COMMIT_RE.fullmatch(sha):
        raise ValueError("commit SHA must contain exactly 40 lowercase hexadecimal characters")
    return sha


def extract_source_commit(text: str) -> str:
    matches = SOURCE_RE.findall(text)
    if len(matches) != 1:
        raise ValueError("readiness summary must contain exactly one valid Source commit")
    return normalize_commit_sha(matches[0])


def verify_match(source_sha: str, main_sha: str) -> None:
    source = normalize_commit_sha(source_sha)
    current = normalize_commit_sha(main_sha)
    if source != current:
        raise ValueError(
            "readiness summary is stale: "
            f"source commit {source} does not match current main {current}"
        )


def api_request(url: str, token: str) -> Any:
    request = Request(
        url,
        method="GET",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Parket36-Production-Lead-Current-Main/1.0",
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


def current_main_sha(repository: str, token: str) -> str:
    payload = api_request(f"https://api.github.com/repos/{repository}/git/ref/heads/main", token)
    try:
        value = str(payload["object"]["sha"])
    except (KeyError, TypeError) as exc:
        raise RuntimeError("GitHub main ref response did not contain object.sha") from exc
    return normalize_commit_sha(value)


def verify_report(path: Path) -> int:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    missing = [
        name
        for name, value in (("GITHUB_REPOSITORY", repository), ("GITHUB_TOKEN", token))
        if not value
    ]
    if missing:
        raise RuntimeError("missing GitHub Actions environment: " + ", ".join(missing))
    if not path.is_file():
        raise ValueError(f"readiness summary was not created: {path}")

    source = extract_source_commit(path.read_text(encoding="utf-8", errors="replace"))
    current = current_main_sha(repository, token)
    verify_match(source, current)
    print(f"Production lead readiness source matches current main {current}")
    return 0


def self_test() -> int:
    failures: list[str] = []
    sha = "a" * 40
    other = "b" * 40
    report = f"# Production lead launch readiness\n\nSource commit: `{sha}`\n"

    try:
        source = extract_source_commit(report)
        verify_match(source, sha)
    except ValueError as exc:
        failures.append(f"matching source and main were rejected: {exc}")

    for stale_source, stale_main in ((sha, other), (other, sha)):
        try:
            verify_match(stale_source, stale_main)
        except ValueError:
            pass
        else:
            failures.append("stale readiness source was accepted")

    for invalid_report in (
        "# Production lead launch readiness",
        report + f"Source commit: `{other}`\n",
        report.replace(sha, "A" * 40),
    ):
        try:
            extract_source_commit(invalid_report)
        except ValueError:
            pass
        else:
            failures.append("invalid or ambiguous Source commit was accepted")

    for invalid in ("", "abc", "A" * 40, "g" * 40, "1" * 39, "1" * 41):
        try:
            normalize_commit_sha(invalid)
        except ValueError:
            pass
        else:
            failures.append(f"invalid commit SHA was accepted: {invalid!r}")

    if failures:
        print("Production lead readiness current-main verifier self-test failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Production lead readiness current-main verifier self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    return verify_report(Path(args.report))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError) as exc:
        print(f"Production lead readiness current-main verifier error: {exc}", file=sys.stderr)
        sys.exit(1)
