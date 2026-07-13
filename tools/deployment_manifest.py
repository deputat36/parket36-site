#!/usr/bin/env python3
"""Create and validate a marker that exists only in the GitHub Pages _site artifact."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

EXPECTED_FIELDS = {
    "schema": 1,
    "site": "parket36",
    "publisher": "github-actions",
    "artifact": "_site",
}


def build_payload() -> dict[str, object]:
    return {
        **EXPECTED_FIELDS,
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
    }


def render_manifest(payload: dict[str, object] | None = None) -> str:
    return json.dumps(payload or build_payload(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def validate_manifest_text(text: str) -> tuple[bool, str]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return False, f"invalid JSON: {exc}"

    if not isinstance(payload, dict):
        return False, "manifest must be a JSON object"

    mismatches = [
        f"{field}={payload.get(field)!r}, expected {expected!r}"
        for field, expected in EXPECTED_FIELDS.items()
        if payload.get(field) != expected
    ]
    commit = payload.get("commit")
    run_id = payload.get("run_id")
    if not isinstance(commit, str) or not commit.strip():
        mismatches.append("commit must be a non-empty string")
    if not isinstance(run_id, str) or not run_id.strip():
        mismatches.append("run_id must be a non-empty string")

    if mismatches:
        return False, "; ".join(mismatches)

    return True, f"publisher=github-actions; artifact=_site; commit={commit}; run_id={run_id}"


def write_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_manifest(), encoding="utf-8")


def self_test() -> int:
    findings: list[str] = []

    valid, detail = validate_manifest_text(render_manifest({
        **EXPECTED_FIELDS,
        "commit": "abc123",
        "run_id": "456",
    }))
    if not valid or "commit=abc123" not in detail:
        findings.append("valid GitHub Actions manifest must pass")

    wrong, wrong_detail = validate_manifest_text(render_manifest({
        **EXPECTED_FIELDS,
        "publisher": "branch-root",
        "commit": "abc123",
        "run_id": "456",
    }))
    if wrong or "publisher='branch-root'" not in wrong_detail:
        findings.append("wrong publisher must fail with detail")

    invalid, invalid_detail = validate_manifest_text("not json")
    if invalid or "invalid JSON" not in invalid_detail:
        findings.append("invalid JSON must fail")

    with TemporaryDirectory() as temporary:
        path = Path(temporary) / "deployment.json"
        write_manifest(path)
        written_ok, written_detail = validate_manifest_text(path.read_text(encoding="utf-8"))
        if not written_ok or "artifact=_site" not in written_detail:
            findings.append("written manifest must validate")

    if findings:
        print("Deployment manifest self-test failed:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Deployment manifest self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", type=Path)
    action.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    write_manifest(args.write)
    ok, detail = validate_manifest_text(args.write.read_text(encoding="utf-8"))
    if not ok:
        print(f"Deployment manifest validation failed: {detail}")
        return 1

    print(f"Wrote deployment manifest: {args.write} ({detail})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
