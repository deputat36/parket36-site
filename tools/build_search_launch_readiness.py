#!/usr/bin/env python3
"""Build one safe readiness report for Parket36 search discovery launch."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile

from site_settings import load_config

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LIVE_HEALTH = ROOT / "search-live-health.md"
DEFAULT_INDEXNOW = ROOT / "search-indexnow.md"
DEFAULT_REPORT = ROOT / "search-launch-readiness.md"


@dataclass(frozen=True)
class ComponentResult:
    name: str
    ok: bool
    detail: str


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def read_component(
    path: Path,
    required_markers: tuple[str, ...],
    failure_markers: tuple[str, ...],
) -> ComponentResult:
    if not path.is_file():
        return ComponentResult(path.name, False, "report is missing")
    text = path.read_text(encoding="utf-8")
    missing = [marker for marker in required_markers if marker not in text]
    failures = [marker for marker in failure_markers if marker in text]
    if missing or failures:
        parts: list[str] = []
        if missing:
            parts.append("missing markers: " + ", ".join(missing))
        if failures:
            parts.append("failure markers: " + ", ".join(failures))
        return ComponentResult(path.name, False, "; ".join(parts))
    return ComponentResult(path.name, True, "required PASS markers confirmed")


def evaluate_reports(
    config: dict[str, object],
    live_health_path: Path,
    indexnow_path: Path,
) -> tuple[str, list[ComponentResult], list[str]]:
    live_health = read_component(
        live_health_path,
        (
            "# Parket36 live health report",
            "| Homepage HTTPS | PASS |",
            "| robots.txt | PASS |",
            "| Sitemap content | PASS |",
        ),
        ("| FAIL |",),
    )
    indexnow = read_component(
        indexnow_path,
        (
            "# IndexNow submission report",
            "Action: `verify-live-key`",
            "Result: **PASS**",
            "Sitemap URLs: `",
            "Live key attempts: `",
        ),
        ("Result: **FAIL**",),
    )
    components = [live_health, indexnow]
    pending: list[str] = []

    metrika_id = str(config.get("metrika_id", "")).strip()
    if not metrika_id:
        pending.append("Получить ID Яндекс Метрики и заполнить `metrika_id` в `data/site.json`.")
    pending.extend(
        [
            "Добавить сайт и sitemap в Яндекс Вебмастер.",
            "Добавить сайт и sitemap в Google Search Console.",
            "Добавить сайт и sitemap в Bing Webmaster Tools и проверить IndexNow.",
        ]
    )

    if not all(component.ok for component in components):
        level = "BLOCKED"
    elif metrika_id:
        level = "SEARCH_LAUNCH_READY"
    else:
        level = "TECHNICAL_READY_ANALYTICS_PENDING"
    return level, components, pending


def render_report(
    config: dict[str, object],
    level: str,
    components: list[ComponentResult],
    pending: list[str],
) -> str:
    generated = datetime.now(timezone.utc).isoformat()
    domain = str(config.get("domain", "")).rstrip("/")
    metrika_id = str(config.get("metrika_id", "")).strip()
    lines = [
        "# Search launch readiness — Паркет36",
        "",
        f"Generated: `{generated}`",
        f"Source commit: `{str(config.get('_source_commit', 'not provided'))}`",
        f"Domain: `{domain}`",
        f"Readiness level: **{level}**",
        "",
        "## Автоматические проверки",
        "",
        "| Компонент | Результат | Детали |",
        "| --- | --- | --- |",
    ]
    for component in components:
        result = "PASS" if component.ok else "FAIL"
        detail = component.detail.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {component.name} | {result} | {detail} |")

    lines.extend(
        [
            "",
            "## Аналитика",
            "",
            f"- Яндекс Метрика: {'настроена' if metrika_id else 'не настроена'}.",
            "- UTM-атрибуция заявок уже поддерживается формами сайта.",
            "- Отчёт не проверяет данные внутри поисковых кабинетов и не получает к ним доступ.",
            "",
            "## Оставшиеся ручные действия",
            "",
        ]
    )
    lines.extend(f"- [ ] {item}" for item in pending)
    lines.extend(
        [
            "",
            "## Границы проверки",
            "",
            "- Workflow выполняет только чтение публичного сайта и файлов репозитория.",
            "- Он не отправляет URL повторно в IndexNow, не меняет DNS и не создаёт аккаунты.",
            "- Он не добавляет verification-токены, счётчики или доступы.",
            "- PASS подтверждает техническую готовность, но не гарантирует индексацию или позиции.",
            "",
        ]
    )
    return "\n".join(lines)


def run_self_test() -> int:
    findings: list[str] = []
    config: dict[str, object] = {
        "domain": "https://parket36.ru",
        "metrika_id": "",
        "_source_commit": "a" * 40,
    }
    with tempfile.TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir)
        live = temp / "live.md"
        indexnow = temp / "indexnow.md"
        live.write_text(
            "\n".join(
                [
                    "# Parket36 live health report",
                    "| Homepage HTTPS | PASS | ok |",
                    "| robots.txt | PASS | ok |",
                    "| Sitemap content | PASS | URLs: 94 |",
                ]
            ),
            encoding="utf-8",
        )
        indexnow.write_text(
            "\n".join(
                [
                    "# IndexNow submission report",
                    "Action: `verify-live-key`",
                    "Result: **PASS**",
                    "Sitemap URLs: `94`",
                    "Live key attempts: `1`",
                ]
            ),
            encoding="utf-8",
        )
        level, components, pending = evaluate_reports(config, live, indexnow)
        if level != "TECHNICAL_READY_ANALYTICS_PENDING":
            findings.append(f"unexpected pending-analytics level: {level}")
        report = render_report(config, level, components, pending)
        for marker in (
            "Readiness level: **TECHNICAL_READY_ANALYTICS_PENDING**",
            "| live.md | PASS |",
            "| indexnow.md | PASS |",
            "Яндекс Метрика: не настроена",
            "не отправляет URL повторно в IndexNow",
        ):
            if marker not in report:
                findings.append(f"report is missing marker: {marker}")

        config["metrika_id"] = "12345678"
        ready_level, _, _ = evaluate_reports(config, live, indexnow)
        if ready_level != "SEARCH_LAUNCH_READY":
            findings.append(f"unexpected configured level: {ready_level}")

        live.write_text(
            "# Parket36 live health report\n| Homepage HTTPS | FAIL | down |",
            encoding="utf-8",
        )
        blocked_level, blocked_components, _ = evaluate_reports(config, live, indexnow)
        if blocked_level != "BLOCKED":
            findings.append(f"failed live health must block; got {blocked_level}")
        if blocked_components[0].ok:
            findings.append("failed live health component was accepted")

    if findings:
        print("Search launch readiness self-test findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("Search launch readiness self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-health", default=str(DEFAULT_LIVE_HEALTH.relative_to(ROOT)))
    parser.add_argument("--indexnow", default=str(DEFAULT_INDEXNOW.relative_to(ROOT)))
    parser.add_argument("--report", default=str(DEFAULT_REPORT.relative_to(ROOT)))
    parser.add_argument("--source-commit", default="")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    try:
        config = load_config()
        config["_source_commit"] = args.source_commit.strip() or "not provided"
        live_health_path = resolve_path(args.live_health)
        indexnow_path = resolve_path(args.indexnow)
        report_path = resolve_path(args.report)
        level, components, pending = evaluate_reports(config, live_health_path, indexnow_path)
        report_path.write_text(render_report(config, level, components, pending), encoding="utf-8")
    except (OSError, ValueError, KeyError) as exc:
        print(f"Search launch readiness failed: {exc}", file=sys.stderr)
        return 1

    print(f"Readiness level: {level}")
    print(f"Report: {report_path.relative_to(ROOT) if report_path.is_relative_to(ROOT) else report_path}")
    return 1 if level == "BLOCKED" else 0


if __name__ == "__main__":
    sys.exit(main())
