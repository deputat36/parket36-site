#!/usr/bin/env python3
"""Report controlled-smoke GitHub secret readiness without reading secret values."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

DEFAULT_REPORT = Path("controlled-lead-smoke-secret-readiness.md")
SECRET_ARGUMENTS = (
    ("PARKET_SMOKE_CONTACT", "has_smoke_contact"),
    ("PARKET_HEALTHCHECK_TOKEN", "has_healthcheck_token"),
)


def parse_flag(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ValueError(f"expected a boolean flag, received {value!r}")


def evaluate(flags: dict[str, bool]) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    findings: list[str] = []
    for secret_name, argument_name in SECRET_ARGUMENTS:
        configured = bool(flags.get(argument_name, False))
        rows.append({
            "secret": secret_name,
            "status": "PASS" if configured else "FAIL",
            "detail": "configured" if configured else "missing",
        })
        if not configured:
            findings.append(f"GitHub Actions secret is missing: {secret_name}")
    return rows, findings


def render_report(rows: list[dict[str, str]], findings: list[str]) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    result = "PASS" if not findings else "FAIL"
    lines = [
        "# GitHub secret readiness for controlled production lead smoke",
        "",
        f"Generated: `{generated}`",
        f"Result: **{result}**",
        "",
        "| Secret | Status | Detail |",
        "|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| `{row['secret']}` | {row['status']} | {row['detail']} |")
    if findings:
        lines.extend(["", "## Findings", ""])
        lines.extend(f"- {finding}" for finding in findings)
    lines.extend([
        "",
        "This report contains secret names and configured/missing booleans only.",
        "It never reads, prints, hashes, measures or stores secret values.",
        "",
    ])
    return "\n".join(lines)


def run_check(*, raw_flags: dict[str, str], report_path: Path) -> int:
    try:
        parsed = {name: parse_flag(value) for name, value in raw_flags.items()}
        rows, findings = evaluate(parsed)
    except ValueError as exc:
        rows = []
        findings = [str(exc)]

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(rows, findings), encoding="utf-8")

    if findings:
        print("Controlled smoke GitHub secret readiness findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("Controlled smoke GitHub secret readiness passed")
    return 0


def self_test() -> int:
    failures: list[str] = []
    all_present = {argument_name: True for _, argument_name in SECRET_ARGUMENTS}
    rows, findings = evaluate(all_present)
    if findings or len(rows) != len(SECRET_ARGUMENTS):
        failures.append("complete controlled smoke secret configuration was rejected")

    for argument_name, secret_name in (
        ("has_smoke_contact", "PARKET_SMOKE_CONTACT"),
        ("has_healthcheck_token", "PARKET_HEALTHCHECK_TOKEN"),
    ):
        missing = dict(all_present)
        missing[argument_name] = False
        _, missing_findings = evaluate(missing)
        if not any(secret_name in finding for finding in missing_findings):
            failures.append(f"missing {secret_name} was not detected")

    try:
        parse_flag("secret-value")
    except ValueError:
        pass
    else:
        failures.append("non-boolean input was accepted")

    report = render_report(rows, [])
    for forbidden in ("+79990000000", "token-value", "digest", "hash:", "length:"):
        if forbidden in report:
            failures.append(f"report contains forbidden protected-data marker: {forbidden}")

    if failures:
        print("Controlled smoke GitHub secret readiness self-test failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Controlled smoke GitHub secret readiness self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--has-smoke-contact")
    parser.add_argument("--has-healthcheck-token")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    values = {
        "has_smoke_contact": args.has_smoke_contact,
        "has_healthcheck_token": args.has_healthcheck_token,
    }
    if any(value is None for value in values.values()):
        parser.error("all --has-* flags are required unless --self-test is used")
    return run_check(raw_flags=values, report_path=Path(args.report))


if __name__ == "__main__":
    sys.exit(main())
