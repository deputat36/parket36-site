#!/usr/bin/env python3
"""Check that the live domain serves the GitHub Actions _site artifact."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import ssl
import sys
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from deployment_manifest import render_manifest, validate_manifest_text
from site_settings import load_config

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "Parket36-Deployment-Source/1.0"
TIMEOUT_SECONDS = 20
MAX_RESPONSE_BYTES = 100_000


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


def evaluate_manifest(text: str) -> DeploymentResult:
    ok, detail = validate_manifest_text(text)
    return DeploymentResult(ok, detail)


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

    passing = evaluate_manifest(render_manifest({
        "schema": 1,
        "site": "parket36",
        "publisher": "github-actions",
        "artifact": "_site",
        "commit": "abc123",
        "run_id": "456",
    }))
    if not passing.ok or "commit=abc123" not in passing.detail:
        findings.append("valid deployment manifest must pass")

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
        append_report(report, "https://example.test", passing)
        text = report.read_text(encoding="utf-8")

    required = [
        "# Existing report",
        "## Deployment source",
        "Manifest: `https://example.test/deployment.json`",
        "| GitHub Actions `_site` artifact | PASS |",
        "commit=abc123",
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
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    domain = (args.domain or str(load_config()["domain"])).rstrip("/")
    url = domain + "/deployment.json"
    try:
        result = evaluate_manifest(fetch_manifest(url))
    except HTTPError as exc:
        result = DeploymentResult(False, f"HTTP {exc.code}: deployment manifest is not published")
    except (URLError, TimeoutError, ssl.SSLError, ValueError) as exc:
        result = DeploymentResult(False, str(exc))

    append_report(ROOT / args.report, domain, result)
    state = "PASS" if result.ok else "FAIL"
    print(f"[{state}] GitHub Actions _site artifact: {result.detail}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
