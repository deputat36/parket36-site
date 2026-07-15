#!/usr/bin/env python3
"""Build one safe summary for the complete production lead launch readiness chain."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ALLOWED_OUTCOMES = {"success", "failure", "skipped"}
DEFAULT_REPORT = Path("production-lead-launch-readiness.md")
COMPONENT_REPORTS = (
    "edge-github-secret-readiness.md",
    "edge-deploy-readiness.md",
    "controlled-lead-smoke-secret-readiness.md",
    "lead-endpoint-preflight.md",
)


def normalize_outcome(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_OUTCOMES:
        raise ValueError(
            f"unsupported step outcome {value!r}; expected one of {sorted(ALLOWED_OUTCOMES)}"
        )
    return normalized


def readiness_level(
    *,
    source_status: str,
    deploy_github_status: str,
    remote_readiness_status: str,
    smoke_github_status: str,
    preflight_status: str,
) -> str:
    if (
        source_status != "success"
        or deploy_github_status != "success"
        or remote_readiness_status != "success"
    ):
        return "BLOCKED"
    if smoke_github_status != "success":
        return "DEPLOY_READY"
    if preflight_status == "success":
        return "PRODUCTION_CONTRACT_CURRENT"
    return "LAUNCH_READY"


def stage_status(outcome: str, *, skipped_label: str = "BLOCKED") -> str:
    if outcome == "success":
        return "PASS"
    if outcome == "failure":
        return "FAIL"
    return skipped_label


def preflight_stage_status(outcome: str) -> str:
    if outcome == "success":
        return "CURRENT"
    if outcome == "failure":
        return "DRIFT"
    return "UNKNOWN"


def next_actions(
    *,
    level: str,
    source_status: str,
    deploy_github_status: str,
    remote_readiness_status: str,
    smoke_github_status: str,
    preflight_status: str,
) -> list[str]:
    actions: list[str] = []

    if source_status != "success":
        actions.append("Исправить source verification до любых production-действий.")
    if deploy_github_status != "success":
        actions.append(
            "Настроить GitHub secrets для deploy по отчёту `edge-github-secret-readiness.md`."
        )
    if remote_readiness_status == "skipped":
        actions.append(
            "После настройки GitHub deploy secrets повторить запуск, чтобы проверить remote Supabase secrets."
        )
    elif remote_readiness_status == "failure":
        actions.append(
            "Исправить обязательные или частично настроенные Supabase secrets по `edge-deploy-readiness.md`."
        )
    if smoke_github_status != "success":
        actions.append(
            "Настроить GitHub secrets controlled smoke по `controlled-lead-smoke-secret-readiness.md`."
        )

    if level == "LAUNCH_READY":
        actions.append(
            "Запустить `Deploy production lead function`: сначала `validate-only`, затем отдельный `deploy` с approval."
        )
        if preflight_status == "failure":
            actions.append(
                "Текущий production CORS-контракт устарел; это ожидаемо исправится после deploy актуального `main`."
            )
    elif level == "PRODUCTION_CONTRACT_CURRENT":
        actions.append(
            "Подтвердить protected healthcheck, затем выполнить один `Controlled production lead smoke` и получить подтверждение Ивана."
        )
    elif level == "DEPLOY_READY":
        actions.append(
            "Deploy-требования выполнены, но полный launch заблокирован до готовности controlled smoke."
        )

    if not actions:
        actions.append("Повторить readiness после устранения отмеченных блокеров.")
    return actions


def render_report(
    *,
    notification_policy: str,
    source_status: str,
    deploy_github_status: str,
    remote_readiness_status: str,
    smoke_github_status: str,
    preflight_status: str,
) -> tuple[str, str]:
    level = readiness_level(
        source_status=source_status,
        deploy_github_status=deploy_github_status,
        remote_readiness_status=remote_readiness_status,
        smoke_github_status=smoke_github_status,
        preflight_status=preflight_status,
    )
    generated = datetime.now(timezone.utc).isoformat()
    rows = [
        (
            "source_verification",
            stage_status(source_status),
            "Deno tests and type-check for both Edge Functions",
        ),
        (
            "github_deploy_secrets",
            stage_status(deploy_github_status),
            "SUPABASE_ACCESS_TOKEN, SUPABASE_PROJECT_ID, PARKET_HEALTHCHECK_TOKEN",
        ),
        (
            "remote_supabase_readiness",
            stage_status(remote_readiness_status),
            f"required remote secrets and notification policy={notification_policy}",
        ),
        (
            "github_controlled_smoke_secrets",
            stage_status(smoke_github_status),
            "PARKET_SMOKE_CONTACT and PARKET_HEALTHCHECK_TOKEN",
        ),
        (
            "current_production_contract",
            preflight_stage_status(preflight_status),
            "public HTTP OPTIONS only; DRIFT does not create a lead and does not block preparation",
        ),
    ]

    lines = [
        "# Production lead launch readiness",
        "",
        f"Generated: `{generated}`",
        f"Notification policy: `{notification_policy}`",
        f"Readiness level: **{level}**",
        "",
        "## Stages",
        "",
        "| Stage | Status | Detail |",
        "|---|---|---|",
    ]
    for stage, status, detail in rows:
        lines.append(f"| `{stage}` | {status} | {detail} |")

    lines.extend(["", "## Next actions", ""])
    for action in next_actions(
        level=level,
        source_status=source_status,
        deploy_github_status=deploy_github_status,
        remote_readiness_status=remote_readiness_status,
        smoke_github_status=smoke_github_status,
        preflight_status=preflight_status,
    ):
        lines.append(f"- {action}")

    lines.extend(["", "## Component reports", ""])
    lines.extend(f"- `{name}`" for name in COMPONENT_REPORTS)
    lines.extend([
        "",
        "This summary never contains secret values, lengths, hashes, tokens or contact data.",
        "It does not deploy an Edge Function, call the protected healthcheck or create a lead.",
        "A green readiness run permits the manual deploy sequence but does not prove notification delivery.",
        "",
    ])
    return level, "\n".join(lines)


def run_check(
    *,
    notification_policy: str,
    source_status: str,
    deploy_github_status: str,
    remote_readiness_status: str,
    smoke_github_status: str,
    preflight_status: str,
    report_path: Path,
) -> int:
    try:
        outcomes = {
            "source_status": normalize_outcome(source_status),
            "deploy_github_status": normalize_outcome(deploy_github_status),
            "remote_readiness_status": normalize_outcome(remote_readiness_status),
            "smoke_github_status": normalize_outcome(smoke_github_status),
            "preflight_status": normalize_outcome(preflight_status),
        }
        if notification_policy not in {"require-configured", "allow-disabled"}:
            raise ValueError(f"unsupported notification policy: {notification_policy}")
        level, report = render_report(
            notification_policy=notification_policy,
            **outcomes,
        )
    except ValueError as exc:
        level = "BLOCKED"
        report = (
            "# Production lead launch readiness\n\n"
            f"Readiness level: **BLOCKED**\n\n## Findings\n\n- {exc}\n"
        )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"Production lead launch readiness: {level}")
    return 1 if level in {"BLOCKED", "DEPLOY_READY"} else 0


def self_test() -> int:
    failures: list[str] = []
    cases = [
        (
            {
                "source_status": "failure",
                "deploy_github_status": "success",
                "remote_readiness_status": "success",
                "smoke_github_status": "success",
                "preflight_status": "failure",
            },
            "BLOCKED",
        ),
        (
            {
                "source_status": "success",
                "deploy_github_status": "success",
                "remote_readiness_status": "success",
                "smoke_github_status": "failure",
                "preflight_status": "failure",
            },
            "DEPLOY_READY",
        ),
        (
            {
                "source_status": "success",
                "deploy_github_status": "success",
                "remote_readiness_status": "success",
                "smoke_github_status": "success",
                "preflight_status": "failure",
            },
            "LAUNCH_READY",
        ),
        (
            {
                "source_status": "success",
                "deploy_github_status": "success",
                "remote_readiness_status": "success",
                "smoke_github_status": "success",
                "preflight_status": "success",
            },
            "PRODUCTION_CONTRACT_CURRENT",
        ),
    ]

    for outcomes, expected in cases:
        actual = readiness_level(**outcomes)
        if actual != expected:
            failures.append(f"expected {expected}, received {actual} for {outcomes}")

    level, report = render_report(
        notification_policy="require-configured",
        source_status="success",
        deploy_github_status="success",
        remote_readiness_status="success",
        smoke_github_status="success",
        preflight_status="failure",
    )
    if level != "LAUNCH_READY":
        failures.append("stale production contract incorrectly blocked launch preparation")
    for marker in (
        "Readiness level: **LAUNCH_READY**",
        "current_production_contract",
        "HTTP OPTIONS only",
        "does not deploy an Edge Function",
    ):
        if marker not in report:
            failures.append(f"summary report missing marker: {marker}")
    for forbidden in ("+79990000000", "token-value", "digest:", "hash:", "secret length"):
        if forbidden in report:
            failures.append(f"summary report contains forbidden protected-data marker: {forbidden}")

    try:
        normalize_outcome("unknown")
    except ValueError:
        pass
    else:
        failures.append("unsupported workflow outcome was accepted")

    if failures:
        print("Production lead launch readiness self-test failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Production lead launch readiness self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--notification-policy",
        choices=("require-configured", "allow-disabled"),
        default="require-configured",
    )
    parser.add_argument("--source-status")
    parser.add_argument("--deploy-github-status")
    parser.add_argument("--remote-readiness-status")
    parser.add_argument("--smoke-github-status")
    parser.add_argument("--preflight-status")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    required = (
        args.source_status,
        args.deploy_github_status,
        args.remote_readiness_status,
        args.smoke_github_status,
        args.preflight_status,
    )
    if any(value is None for value in required):
        parser.error("all --*-status arguments are required unless --self-test is used")

    return run_check(
        notification_policy=args.notification_policy,
        source_status=args.source_status,
        deploy_github_status=args.deploy_github_status,
        remote_readiness_status=args.remote_readiness_status,
        smoke_github_status=args.smoke_github_status,
        preflight_status=args.preflight_status,
        report_path=Path(args.report),
    )


if __name__ == "__main__":
    sys.exit(main())
