#!/usr/bin/env python3
"""Stamp a production lead readiness summary with the exact source commit."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

DEFAULT_REPORT = Path("production-lead-launch-readiness.md")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SOURCE_PREFIX = "Source commit: `"
VALIDITY_LINE = (
    "Snapshot validity: this result applies only to this exact commit; "
    "rerun after any change to `main`."
)


def normalize_commit_sha(value: str) -> str:
    sha = value.strip()
    if not COMMIT_RE.fullmatch(sha):
        raise ValueError("commit SHA must contain exactly 40 lowercase hexadecimal characters")
    return sha


def stamp_text(text: str, commit_sha: str) -> str:
    sha = normalize_commit_sha(commit_sha)
    if "# Production lead launch readiness" not in text:
        raise ValueError("readiness summary header is missing")
    if "Readiness level:" not in text:
        raise ValueError("readiness level is missing")

    filtered: list[str] = []
    for line in text.splitlines():
        if line.startswith(SOURCE_PREFIX):
            continue
        if line == VALIDITY_LINE:
            continue
        filtered.append(line)

    insert_at = 1
    for index, line in enumerate(filtered):
        if line.startswith("Generated: `"):
            insert_at = index + 1
            break

    stamped = filtered[:insert_at] + [f"Source commit: `{sha}`", VALIDITY_LINE] + filtered[insert_at:]
    return "\n".join(stamped).rstrip() + "\n"


def stamp_report(path: Path, commit_sha: str) -> int:
    if not path.is_file():
        raise ValueError(f"readiness summary was not created: {path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    path.write_text(stamp_text(text, commit_sha), encoding="utf-8")
    print(f"Stamped production lead readiness with source commit {commit_sha}")
    return 0


def self_test() -> int:
    failures: list[str] = []
    sha = "a" * 40
    other_sha = "b" * 40
    source = "\n".join(
        [
            "# Production lead launch readiness",
            "",
            "Generated: `2026-07-15T00:00:00+00:00`",
            "Readiness level: **LAUNCH_READY**",
            "",
        ]
    )

    stamped = stamp_text(source, sha)
    for marker in (f"Source commit: `{sha}`", VALIDITY_LINE, "Readiness level: **LAUNCH_READY**"):
        if marker not in stamped:
            failures.append(f"stamped summary missing marker: {marker}")

    restamped = stamp_text(stamped, other_sha)
    if f"Source commit: `{other_sha}`" not in restamped:
        failures.append("restamp did not replace the previous source commit")
    if f"Source commit: `{sha}`" in restamped:
        failures.append("restamp retained the previous source commit")
    if restamped.count("Source commit: `") != 1 or restamped.count(VALIDITY_LINE) != 1:
        failures.append("stamping is not idempotent")

    for invalid in ("", "abc", "A" * 40, "g" * 40, "1" * 39, "1" * 41):
        try:
            normalize_commit_sha(invalid)
        except ValueError:
            pass
        else:
            failures.append(f"invalid commit SHA was accepted: {invalid!r}")

    for invalid_report in ("Readiness level: **BLOCKED**", "# Production lead launch readiness"):
        try:
            stamp_text(invalid_report, sha)
        except ValueError:
            pass
        else:
            failures.append("incomplete readiness summary was accepted")

    if failures:
        print("Production lead readiness commit stamp self-test failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Production lead readiness commit stamp self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit-sha")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.commit_sha:
        parser.error("--commit-sha is required unless --self-test is used")
    return stamp_report(Path(args.report), normalize_commit_sha(args.commit_sha))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as exc:
        print(f"Production lead readiness commit stamp error: {exc}", file=sys.stderr)
        sys.exit(1)
