#!/usr/bin/env python3
"""Validate honest public copy for lead storage, notification and manual fallback."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from lead_copy import FORBIDDEN_MARKERS, REPLACEMENTS, apply_replacements  # noqa: E402

NORMALIZER = ROOT / "tools" / "lead_copy.py"
JS_ASSETS = ROOT / "tools" / "js_assets.py"
E2E = ROOT / "tests" / "e2e" / "lead-copy-honesty.spec.mjs"
DOC = ROOT / "docs" / "lead-copy-honesty.md"
RUNNER = ROOT / "tools" / "run_quality_checks.py"
QUALITY_CHECKER = ROOT / "tools" / "check_quality_runner.py"

SOURCE_PATHS = (
    ROOT / "index.html",
    ROOT / "zayavka" / "index.html",
    ROOT / "kontakty" / "index.html",
    ROOT / "politika" / "index.html",
    ROOT / "js" / "main.js",
)

REQUIRED_NORMALIZED_MARKERS = {
    ROOT / "index.html": (
        "Форма попробует сохранить заявку в защищённой системе",
        "Если уведомление Ивану не подтвердится",
        "сразу появится кнопка звонка",
    ),
    ROOT / "zayavka" / "index.html": (
        "сервис попробует сохранить заявку",
        "Заполните форму — получите понятный следующий шаг",
        "Если автоматическое уведомление не подтвердится",
        "Форма попробует сохранить заявку в защищённой системе",
    ),
    ROOT / "kontakty" / "index.html": (
        "Форма попробует сохранить контакт в защищённой системе",
        "Форма попробует сохранить номер в защищённой системе",
        "Если уведомление Ивану не подтвердится",
    ),
    ROOT / "politika" / "index.html": (
        "Форма пытается сохранить заявку в защищённой системе",
        "подтверждено ли автоматическое уведомление Ивану",
        "Успешно принятые заявки сохраняются в защищённом хранилище Supabase",
    ),
    ROOT / "js" / "main.js": (
        "Форма попробует сохранить заявку в защищённой системе",
        "сразу появится кнопка звонка",
    ),
}

REQUIRED_FILE_MARKERS = {
    NORMALIZER: (
        "REPLACEMENTS = (",
        "FORBIDDEN_MARKERS = (",
        "def apply_replacements(text: str) -> str:",
        "def normalize_lead_copy(destination: Path, errors: list[str]) -> None:",
        'destination.rglob("*.html")',
        'destination.rglob("*.js")',
        "unconditional lead-delivery claim remains",
        "def self_test() -> int:",
    ),
    JS_ASSETS: (
        "from lead_copy import normalize_lead_copy",
        "normalize_lead_copy(destination, errors)",
        "mapping = build_mapping(js_dir, errors)",
        "Normalize lead copy, fingerprint every public JS file",
    ),
    E2E: (
        "главная не обещает доставку без подтверждения",
        "страница оценки различает сохранение и уведомление",
        "callback не обещает получение заявки без подтверждения",
        "политика описывает хранение отдельно от уведомления",
        "expectNoStaleClaims",
        "сервис попробует сохранить заявку",
        "Успешно принятые заявки сохраняются",
    ),
    DOC: (
        "Честный текст заявки",
        "форма пытается сохранить заявку",
        "подтверждено ли автоматическое уведомление Ивану",
        "notification: sent",
        "tools/lead_copy.py",
        "lead-copy-honesty.spec.mjs",
        "не вызывает production endpoint",
    ),
    RUNNER: (
        '"Validate lead copy honesty", ["tools/check_lead_copy_honesty.py"]',
        '"Validate JavaScript assets", ["tools/check_js_assets.py"]',
    ),
    QUALITY_CHECKER: (
        '["tools/check_lead_copy_honesty.py"]',
        '["tools/check_js_assets.py"]',
    ),
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def main() -> int:
    findings: list[str] = []
    texts: dict[Path, str] = {}

    for path, markers in REQUIRED_FILE_MARKERS.items():
        if not path.is_file():
            findings.append(f"missing required file: {path.relative_to(ROOT)}")
            texts[path] = ""
            continue
        text = read(path)
        texts[path] = text
        for marker in markers:
            if marker not in text:
                findings.append(f"{path.relative_to(ROOT)}: missing marker: {marker}")

    if len(REPLACEMENTS) < 10:
        findings.append("lead copy normalizer must keep the complete approved replacement set")

    for source_path in SOURCE_PATHS:
        if not source_path.is_file():
            findings.append(f"missing public source: {source_path.relative_to(ROOT)}")
            continue
        normalized = apply_replacements(read(source_path))
        for marker in FORBIDDEN_MARKERS:
            if marker in normalized:
                findings.append(
                    f"{source_path.relative_to(ROOT)}: stale unconditional claim survives normalization: {marker}"
                )
        for marker in REQUIRED_NORMALIZED_MARKERS.get(source_path, ()):
            if marker not in normalized:
                findings.append(
                    f"{source_path.relative_to(ROOT)}: normalized copy is missing marker: {marker}"
                )

    js_assets = texts.get(JS_ASSETS, "")
    normalize_position = js_assets.find("normalize_lead_copy(destination, errors)")
    error_guard_position = js_assets.find("if errors:\n        return {}", normalize_position)
    mapping_position = js_assets.find("mapping = build_mapping(js_dir, errors)", error_guard_position)
    if min(normalize_position, error_guard_position, mapping_position) < 0 or not (
        normalize_position < error_guard_position < mapping_position
    ):
        findings.append("lead copy must normalize and fail closed before JavaScript fingerprint mapping")

    runner = texts.get(RUNNER, "")
    honesty_position = runner.find(
        '"Validate lead copy honesty", ["tools/check_lead_copy_honesty.py"]'
    )
    js_position = runner.find('"Validate JavaScript assets", ["tools/check_js_assets.py"]')
    if min(honesty_position, js_position) < 0 or honesty_position > js_position:
        findings.append("lead copy honesty check must run before JavaScript asset validation")

    if findings:
        print("Lead copy honesty findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Lead copy honesty contract passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
