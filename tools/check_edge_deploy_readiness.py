#!/usr/bin/env python3
"""Validate Parket36 production Edge Function deployment readiness without exposing secret values."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SITE_CONFIG = ROOT / "data" / "site.json"
SUPABASE_CONFIG = ROOT / "supabase" / "config.toml"
PUBLIC_FUNCTION_DIR = ROOT / "supabase" / "functions" / "parket-public-lead"
VERIFY_FUNCTION_DIR = ROOT / "supabase" / "functions" / "parket-lead-verify"
DEFAULT_REPORT = Path("edge-deploy-readiness.md")

REQUIRED_REMOTE_SECRETS = {
    "PARKET_IP_HASH_SALT",
    "PARKET_HEALTHCHECK_TOKEN",
}
TELEGRAM_SECRETS = {
    "PARKET_TELEGRAM_BOT_TOKEN",
    "PARKET_TELEGRAM_CHAT_ID",
}
EMAIL_SECRETS = {
    "PARKET_RESEND_API_KEY",
    "PARKET_EMAIL_FROM",
    "PARKET_EMAIL_TO",
}
PUBLIC_FUNCTION_FILES = {
    "index.ts",
    "origin-policy.ts",
    "field-limits.ts",
    "payload-shape.ts",
    "contact-validation.ts",
}
VERIFY_FUNCTION_FILES = {
    "index.ts",
    "request-id.ts",
    "request-id_test.ts",
}
FUNCTION_SLUGS = ("parket-public-lead", "parket-lead-verify")
PROJECT_REF_RE = re.compile(r"https://(?P<ref>[a-z0-9]+)\.supabase\.co/functions/v1/parket-public-lead")


def expected_project_ref() -> str:
    payload = json.loads(SITE_CONFIG.read_text(encoding="utf-8"))
    endpoint = str(payload.get("lead_endpoint") or "").strip()
    match = PROJECT_REF_RE.fullmatch(endpoint)
    if not match:
        raise ValueError("data/site.json lead_endpoint is not a valid parket-public-lead Supabase URL")
    return match.group("ref")


def extract_secret_names(payload: Any) -> set[str]:
    names: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, str):
            if re.fullmatch(r"[A-Z][A-Z0-9_]{2,120}", value):
                names.add(value)
            return
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if isinstance(value, dict):
            for key in ("name", "key", "secret_name"):
                candidate = value.get(key)
                if isinstance(candidate, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{2,120}", candidate):
                    names.add(candidate)
            for key in ("secrets", "data", "items", "results"):
                if key in value:
                    visit(value[key])
            if not any(key in value for key in ("name", "key", "secret_name", "secrets", "data", "items", "results")):
                for key, nested in value.items():
                    if isinstance(key, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{2,120}", key):
                        names.add(key)
                    visit(nested)

    visit(payload)
    return names


def read_remote_secret_names(path: Path) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return extract_secret_names(payload)


def notification_state(names: set[str]) -> tuple[str, list[str]]:
    telegram_present = TELEGRAM_SECRETS & names
    email_present = EMAIL_SECRETS & names
    findings: list[str] = []

    if telegram_present and telegram_present != TELEGRAM_SECRETS:
        findings.append(
            "Telegram secrets are partially configured; missing: "
            + ", ".join(sorted(TELEGRAM_SECRETS - telegram_present))
        )
    if email_present and email_present != EMAIL_SECRETS:
        findings.append(
            "Email secrets are partially configured; missing: "
            + ", ".join(sorted(EMAIL_SECRETS - email_present))
        )

    complete_channels: list[str] = []
    if telegram_present == TELEGRAM_SECRETS:
        complete_channels.append("telegram")
    if email_present == EMAIL_SECRETS:
        complete_channels.append("email")

    return ", ".join(complete_channels) if complete_channels else "disabled", findings


def function_config_has_public_mode(config_text: str, slug: str) -> bool:
    pattern = re.compile(
        rf"(?ms)^\[functions\.{re.escape(slug)}\]\s*$"
        rf"(?P<body>.*?)(?=^\[|\Z)"
    )
    match = pattern.search(config_text)
    if not match:
        return False
    return bool(re.search(r"(?m)^verify_jwt\s*=\s*false\s*$", match.group("body")))


def validate_repository(project_ref: str) -> list[str]:
    findings: list[str] = []
    expected = expected_project_ref()
    if project_ref != expected:
        findings.append(f"SUPABASE_PROJECT_ID mismatch: received {project_ref}; expected {expected}")

    if not SUPABASE_CONFIG.is_file():
        findings.append("supabase/config.toml is missing")
    else:
        config_text = SUPABASE_CONFIG.read_text(encoding="utf-8", errors="ignore")
        for slug in FUNCTION_SLUGS:
            if not function_config_has_public_mode(config_text, slug):
                findings.append(
                    f"supabase/config.toml must configure [functions.{slug}] with verify_jwt = false"
                )

    missing_public = sorted(
        name for name in PUBLIC_FUNCTION_FILES if not (PUBLIC_FUNCTION_DIR / name).is_file()
    )
    if missing_public:
        findings.append("parket-public-lead source is incomplete; missing: " + ", ".join(missing_public))

    missing_verifier = sorted(
        name for name in VERIFY_FUNCTION_FILES if not (VERIFY_FUNCTION_DIR / name).is_file()
    )
    if missing_verifier:
        findings.append("parket-lead-verify source is incomplete; missing: " + ", ".join(missing_verifier))

    return findings


def evaluate(
    *,
    project_ref: str,
    remote_names: set[str],
    notification_policy: str,
) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    repo_findings = validate_repository(project_ref)
    findings = list(repo_findings)

    missing_required = sorted(REQUIRED_REMOTE_SECRETS - remote_names)
    rows.append({
        "check": "required_remote_secrets",
        "status": "PASS" if not missing_required else "FAIL",
        "detail": "configured" if not missing_required else "missing: " + ", ".join(missing_required),
    })
    if missing_required:
        findings.append("required remote secrets are missing: " + ", ".join(missing_required))

    channels, channel_findings = notification_state(remote_names)
    findings.extend(channel_findings)
    channel_ok = not channel_findings and (channels != "disabled" or notification_policy == "allow-disabled")
    rows.append({
        "check": "notification_policy",
        "status": "PASS" if channel_ok else "FAIL",
        "detail": f"policy={notification_policy}; channels={channels}",
    })
    if channels == "disabled" and notification_policy != "allow-disabled":
        findings.append("no complete notification channel is configured; choose allow-disabled only consciously")

    rows.append({
        "check": "repository_contract",
        "status": "PASS" if not repo_findings else "FAIL",
        "detail": "project ref, both function configs and source files match"
        if not repo_findings else "; ".join(repo_findings),
    })

    return rows, findings


def render_report(
    *,
    project_ref: str,
    notification_policy: str,
    remote_names: set[str],
    rows: list[dict[str, str]],
    findings: list[str],
) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    result = "PASS" if not findings else "FAIL"
    visible_names = sorted(name for name in remote_names if name.startswith("PARKET_"))
    lines = [
        "# Edge Function deployment readiness",
        "",
        f"Generated: `{generated}`",
        f"Project ref: `{project_ref}`",
        "Functions: `parket-public-lead`, `parket-lead-verify`",
        f"Notification policy: `{notification_policy}`",
        f"Result: **{result}**",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for row in rows:
        detail = row["detail"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{row['check']}` | {row['status']} | {detail} |")

    lines.extend(["", "## Detected PARKET_* secret names", ""])
    if visible_names:
        lines.extend(f"- `{name}`" for name in visible_names)
    else:
        lines.append("- none")

    if findings:
        lines.extend(["", "## Findings", ""])
        lines.extend(f"- {finding}" for finding in findings)

    lines.extend([
        "",
        "This report contains secret names only. It never contains secret values, digests or access tokens.",
        "A PASS permits deployment of both functions but does not replace the post-deploy preflight, protected healthcheck or controlled real lead.",
        "",
    ])
    return "\n".join(lines)


def run_check(
    *,
    project_ref: str,
    remote_secrets_path: Path,
    notification_policy: str,
    report_path: Path,
) -> int:
    try:
        remote_names = read_remote_secret_names(remote_secrets_path)
        rows, findings = evaluate(
            project_ref=project_ref,
            remote_names=remote_names,
            notification_policy=notification_policy,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        rows = []
        findings = [str(exc)]
        remote_names = set()

    report_path.write_text(
        render_report(
            project_ref=project_ref,
            notification_policy=notification_policy,
            remote_names=remote_names,
            rows=rows,
            findings=findings,
        ),
        encoding="utf-8",
    )
    if findings:
        print("Edge deploy readiness findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("Edge deploy readiness passed")
    return 0


def self_test() -> int:
    failures: list[str] = []
    expected = expected_project_ref()

    payloads = [
        [
            {"name": "PARKET_IP_HASH_SALT"},
            {"name": "PARKET_HEALTHCHECK_TOKEN"},
            {"name": "PARKET_TELEGRAM_BOT_TOKEN"},
            {"name": "PARKET_TELEGRAM_CHAT_ID"},
        ],
        {"secrets": {"PARKET_IP_HASH_SALT": {"digest": "hidden"}, "PARKET_HEALTHCHECK_TOKEN": {}}},
    ]
    if "PARKET_TELEGRAM_CHAT_ID" not in extract_secret_names(payloads[0]):
        failures.append("list-shaped secret output was not parsed")
    if "PARKET_IP_HASH_SALT" not in extract_secret_names(payloads[1]):
        failures.append("mapping-shaped secret output was not parsed")

    healthy_names = extract_secret_names(payloads[0])
    _, healthy_findings = evaluate(
        project_ref=expected,
        remote_names=healthy_names,
        notification_policy="require-configured",
    )
    if healthy_findings:
        failures.append("complete Telegram configuration was rejected")

    missing_salt = set(healthy_names)
    missing_salt.remove("PARKET_IP_HASH_SALT")
    _, missing_findings = evaluate(
        project_ref=expected,
        remote_names=missing_salt,
        notification_policy="require-configured",
    )
    if not any("PARKET_IP_HASH_SALT" in finding for finding in missing_findings):
        failures.append("missing IP hash salt was not detected")

    disabled_names = set(REQUIRED_REMOTE_SECRETS)
    _, disabled_findings = evaluate(
        project_ref=expected,
        remote_names=disabled_names,
        notification_policy="allow-disabled",
    )
    if disabled_findings:
        failures.append("explicit allow-disabled policy was rejected")

    partial_names = set(REQUIRED_REMOTE_SECRETS) | {"PARKET_TELEGRAM_BOT_TOKEN"}
    _, partial_findings = evaluate(
        project_ref=expected,
        remote_names=partial_names,
        notification_policy="allow-disabled",
    )
    if not any("partially configured" in finding for finding in partial_findings):
        failures.append("partial notification configuration was not detected")

    if failures:
        print("Edge deploy readiness self-test failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Edge deploy readiness self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-ref")
    parser.add_argument("--remote-secrets")
    parser.add_argument(
        "--notification-policy",
        choices=("require-configured", "allow-disabled"),
        default="require-configured",
    )
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.project_ref or not args.remote_secrets:
        parser.error("--project-ref and --remote-secrets are required unless --self-test is used")
    return run_check(
        project_ref=args.project_ref,
        remote_secrets_path=Path(args.remote_secrets),
        notification_policy=args.notification_policy,
        report_path=Path(args.report),
    )


if __name__ == "__main__":
    sys.exit(main())
