#!/usr/bin/env python3
"""Validate static homepage callback links and their browser coverage."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
HOME_MODULE = ROOT / "tools" / "home_callback_links.py"
SERVICE_MODULE = ROOT / "tools" / "service_callback_links.py"
E2E_TEST = ROOT / "tests" / "e2e" / "home-callback-path.spec.mjs"
DOC = ROOT / "docs" / "callback-form.md"

REQUIRED_MARKERS = {
    HOME_MODULE: {
        'CALLBACK_URL = "/kontakty/#callback"': "callback URL",
        "Неудобно звонить — оставить номер для обратного звонка →": "hero callback copy",
        "Удобнее, чтобы Иван позвонил сам — оставить номер →": "quick-call callback copy",
        "text.count(CALLBACK_URL) != 2": "post-injection count check",
        "missing_markers": "strict source marker validation",
    },
    SERVICE_MODULE: {
        "from home_callback_links import inject_home_callback_links": "homepage injector import",
        "inject_home_callback_links(site_root, errors)": "homepage injector call",
    },
    E2E_TEST: {
        "главная предлагает два статических пути к обратному звонку": "static link scenario",
        "переход с главной сохраняет UTM и отправляет общую callback-заявку": "submission scenario",
        "toHaveCount(2)": "exact link count assertion",
        "landing: '/'": "homepage first-touch assertion",
        "callback_topic: 'general'": "generic topic assertion",
        ".mobile-cta": "unchanged mobile CTA assertion",
    },
    DOC: {
        "## Путь с главной страницы": "homepage callback documentation",
        "две статические ссылки": "static link explanation",
        "landing `/`": "homepage first-touch documentation",
    },
}


def main() -> int:
    findings: list[str] = []

    for path, markers in REQUIRED_MARKERS.items():
        if not path.is_file():
            findings.append(f"missing required file: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker, label in markers.items():
            if marker not in text:
                findings.append(f"{path.relative_to(ROOT)}: missing {label}: {marker}")

    if findings:
        print("Homepage callback findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Homepage callback links passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
