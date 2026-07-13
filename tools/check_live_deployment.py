#!/usr/bin/env python3
"""Check that the live domain serves the expected GitHub Actions _site artifact."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import ssl
import sys
import time
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from deployment_manifest import render_manifest, validate_manifest_text
from site_settings import load_config

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "Parket36-Deployment-Source/1.1"
TIMEOUT_SECONDS = 20
MAX_RESPONSE_BYTES = 100_000
DEFAULT_RETRY_DELAY_SECONDS = 10
MAX_ATTEMPTS = 6


@dataclass
class DeploymentResult:
    ok: bool
    detail: str


def fetch_manifest(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    context = ssl.create_default_context()
    with urlopen(request, timeout=TIMEOUT_SECONDS, context=context) as response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError(f"response is larger than {MAX_RESPONSE_BYTES} bytes")
        if response.status != 200:
            raise ValueError(f"HTTP {response.status}")
        return body.decode("utf-8", errors="replace")


def evaluate_manifest(
    text: str,
    *,
    expected_sha: str | None = None,
    expected_run_id: str | None = None,
) -> DeploymentResult:
    ok, detail = validate_manifest_text(text)
    if not ok:
        return DeploymentResult(False, detail)

    payload = json.loads(text)
    mismatches: list[str] = []
    actual_sha = str(payload.get("commit", ""))
    actual_run_id = str(payload.get("run_id", ""))

    if expected_sha and actual_sha != expected_sha:
        mismatches.append(f"commit={actual_sha!r}, expected {expected_sha!r}")
    if expected_run_id and actual_run_id != expected_run_id:
        mismatches.append(f"run_id={actual_run_id!r}, expected {expected_run_id!r}")

    if mismatches:
        return DeploymentResult(False, "stale or unexpected deployment: " + "; ".join(mismatches))

    expected_parts: list[str] = []
    if expected_sha:
        expected_parts.append(f"expected_commit={expected_sha}")
    if expected_run_id:
        expected_parts.append(f"expected_run_id={expected_run_id}")
    if expected_parts:
        detail += "; " + "; ".join(expected_parts)
    return DeploymentResult(True, detail)


def check_manifest_with_retry(
    url: str,
    *,
    expected_sha: str | None,
    expected_run_id: str | None,
    attempts: int,
    retry_delay: int,
) -> DeploymentResult:
    last_result = DeploymentResult(False, "deployment manifest was not checked")

    for attempt in range(1, attempts + 1):
        try:
            last_result = evaluate_manifest(
                fetch_manifest(url),
                expected_sha=expected_sha,
                expected_run_id=expected_run_id,
            )
        except HTTPError as exc:
            last_result = DeploymentResult(False, f"HTTP {exc.code}: deployment manifest is not published")
        except (URLError, TimeoutError, ssl.SSLError, ValueError) as exc:
            last_result = DeploymentResult(False, str(exc))

        if last_result.ok:
            if attempt > 1:
                last_result.detail += f"; matched after attempt {attempt}/{attempts}"
            return last_result

        if attempt < attempts:
            print(
                f"Deployment manifest attempt {attempt}/{attempts} failed: "
                f"{last_result.detail}; retrying in {retry_delay}s",
                flush=True,
            )
            time.sleep(retry_delay)

    if attempts > 1:
        last_result.detail += f"; attempts={attempts}"
    return last_result


def append_report(path: Path, domain: str, result: DeploymentResult) -> None:
    state = "PASS" if result.ok else "FAIL"
    detail = result.detail.replace("|", "\\|").replace("\n", " ")
    block = [
        "",
        "## Deployment source",
        "",
        f"Manifest: `{domain.rstrip('/')}/deployment.json`",
        "",
        "| Check | Result | Detail |",
        "| --- | --- | --- |",
        f"| GitHub Actions `_site` artifact | {state} | {detail} |",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.is_file() else "# Parket36 live health report\n"
    path.write_text(existing.rstrip() + "\n" + "\n".join(block), encoding="utf-8")


def self_test() -> int:
    findings: list[str] = []
    valid_text = render_manifest({
        "schema": 1,
        "site": "parket36",
        "publisher": "github-actions",
        "artifact": "_site",
        "commit": "abc123",
        "run_id": "456",
    })

    passing = evaluate_manifest(valid_text)
    if not passing.ok or "commit=abc123" not in passing.detail:
        findings.append("valid deployment manifest must pass")

    exact = evaluate_manifest(valid_text, expected_sha="abc123", expected_run_id="456")
    if not exact.ok or "expected_commit=abc123" not in exact.detail or "expected_run_id=456" not in exact.detail:
        findings.append("matching expected SHA and run ID must pass with detail")

    stale_sha = evaluate_manifest(valid_text, expected_sha="def789", expected_run_id="456")
    if stale_sha.ok or "stale or unexpected deployment" not in stale_sha.detail or "def789" not in stale_sha.detail:
        findings.append("stale deployment SHA must fail with expected SHA detail")

    stale_run = evaluate_manifest(valid_text, expected_sha="abc123", expected_run_id="999")
    if stale_run.ok or "run_id='456', expected '999'" not in stale_run.detail:
        findings.append("unexpected deployment run ID must fail")

    failing = evaluate_manifest(render_manifest({
        "schema": 1,
        "site": "parket36",
        "publisher": "branch-root",
        "artifact": "root",
        "commit": "abc123",
        "run_id": "456",
    }))
    if failing.ok or "publisher='branch-root'" not in failing.detail:
        findings.append("branch-root deployment must fail")

    with TemporaryDirectory() as temporary:
        report = Path(temporary) / "report.md"
        report.write_text("# Existing report\n\n| Check | Result | Detail |\n", encoding="utf-8")
        append_report(report, "https://example.test", exact)
        text = report.read_text(encoding="utf-8")

    required = [
        "# Existing report",
        "## Deployment source",
        "Manifest: `https://example.test/deployment.json`",
        "| GitHub Actions `_site` artifact | PASS |",
        "commit=abc123",
        "expected_commit=abc123",
        "expected_run_id=456",
    ]
    findings.extend(f"missing report marker: {marker}" for marker in required if marker not in text)

    if findings:
        print("Live deployment self-test failed:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Live deployment self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="live-health-report.md")
    parser.add_argument("--domain")
    parser.add_argument("--expected-sha")
    parser.add_argument("--expected-run-id")
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--retry-delay", type=int, default=DEFAULT_RETRY_DELAY_SECONDS)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if not 1 <= args.attempts <= MAX_ATTEMPTS:
        print(f"Deployment source check findings: attempts must be between 1 and {MAX_ATTEMPTS}")
        return 1
    if args.retry_delay < 0 or args.retry_delay > 60:
        print("Deployment source check findings: retry delay must be between 0 and 60 seconds")
        return 1

    expected_sha = (args.expected_sha or "").strip() or None
    expected_run_id = (args.expected_run_id or "").strip() or None
    domain = (args.domain or str(load_config()["domain"])).rstrip("/")
    url = domain + "/deployment.json"
    attempts = args.attempts if expected_sha or expected_run_id else 1

    result = check_manifest_with_retry(
        url,
        expected_sha=expected_sha,
        expected_run_id=expected_run_id,
        attempts=attempts,
        retry_delay=args.retry_delay,
    )

    append_report(ROOT / args.report, domain, result)
    state = "PASS" if result.ok else "FAIL"
    print(f"[{state}] GitHub Actions _site artifact: {result.detail}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
