#!/usr/bin/env python3
"""One-time migration: make public source HTML/SVG client-ready without build-time rewrites."""

from __future__ import annotations

from pathlib import Path
import sys

import build_pages

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "tools" / "build_pages.py"
POLICY_DOC = ROOT / "docs" / "public-placeholder-policy.md"

OLD_POLICY = """`tools/build_pages.py`:

1. заменяет известные служебные формулировки в HTML и SVG;
2. превращает первый экран главной в инструкцию по фото и видео;
3. останавливает сборку, если запрещённая формулировка осталась в готовом публичном файле.
"""

NEW_POLICY = """Публичные HTML и SVG хранятся в репозитории уже в клиентском виде. Служебные подписи не должны зависеть от скрытой подмены во время публикации.

`tools/build_pages.py`:

1. копирует публичные исходники без переписывания клиентского текста;
2. проверяет HTML и SVG на запрещённые редакторские формулировки до остальных преобразований;
3. останавливает сборку, если такая формулировка появилась снова.
"""


def iter_public_text_files() -> list[Path]:
    paths: set[Path] = set()
    for directory in build_pages.PUBLIC_DIRS:
        root = ROOT / directory
        if not root.is_dir():
            continue
        paths.update(root.rglob("*.html"))
        paths.update(root.rglob("*.svg"))

    for name in build_pages.PUBLIC_FILES:
        path = ROOT / name
        if path.suffix in {".html", ".svg"} and path.is_file():
            paths.add(path)

    return sorted(
        path
        for path in paths
        if not build_pages.is_internal_working_path(path.relative_to(ROOT))
    )


def migrate_public_sources() -> list[str]:
    changed: list[str] = []
    findings: list[str] = []

    for path in iter_public_text_files():
        text = path.read_text(encoding="utf-8")
        migrated = text
        for source, replacement in build_pages.PUBLIC_COPY_REPLACEMENTS:
            migrated = migrated.replace(source, replacement)

        relative = path.relative_to(ROOT).as_posix()
        for marker in build_pages.FORBIDDEN_PUBLIC_PLACEHOLDER_MARKERS:
            if marker in migrated:
                findings.append(f"{relative}: forbidden public placeholder remains: {marker}")

        if migrated != text:
            path.write_text(migrated, encoding="utf-8")
            changed.append(relative)

    homepage = (ROOT / "index.html").read_text(encoding="utf-8")
    required_homepage = (
        'aria-label="Как подготовить фотографии пола для предварительной оценки"',
        '<span class="photo-slot__mark">Оценка по фото</span>',
        '<span class="photo-slot__label">Общий вид комнаты</span>',
        '<span class="photo-slot__mark">Дефект крупно</span>',
        '<span class="photo-slot__mark">Короткое видео</span>',
        '<span class="photo-slot__label">Скрип или движение</span>',
    )
    for marker in required_homepage:
        if marker not in homepage:
            findings.append(f"index.html: migrated homepage marker is missing: {marker}")

    if findings:
        raise ValueError("\n".join(findings))
    if "index.html" not in changed:
        raise ValueError("index.html was not migrated")
    return changed


def simplify_build_validator() -> None:
    text = BUILD_SCRIPT.read_text(encoding="utf-8")

    constants_start = text.index("PUBLIC_COPY_REPLACEMENTS = (")
    forbidden_start = text.index("FORBIDDEN_PUBLIC_PLACEHOLDER_MARKERS = (")
    text = text[:constants_start] + text[forbidden_start:]

    function_start = text.index("def normalize_public_copy(errors: list[str]) -> None:")
    next_function = text.index("\ndef inject_lead_reliability", function_start)
    replacement = '''def validate_public_copy(errors: list[str]) -> None:
    public_text_files = sorted([*DEST.rglob("*.html"), *DEST.rglob("*.svg")])

    for path in public_text_files:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(DEST).as_posix()
        for marker in FORBIDDEN_PUBLIC_PLACEHOLDER_MARKERS:
            if marker in text:
                errors.append(f"{relative}: public placeholder copy remains: {marker}")

'''
    text = text[:function_start] + replacement + text[next_function + 1 :]
    text = text.replace("    normalize_public_copy(errors)\n", "    validate_public_copy(errors)\n", 1)

    if "PUBLIC_COPY_REPLACEMENTS" in text or "normalize_public_copy" in text:
        raise ValueError("tools/build_pages.py still contains build-time public copy rewriting")
    if "def validate_public_copy(errors: list[str]) -> None:" not in text:
        raise ValueError("tools/build_pages.py public copy validator was not created")

    BUILD_SCRIPT.write_text(text, encoding="utf-8")


def update_policy() -> None:
    text = POLICY_DOC.read_text(encoding="utf-8")
    if OLD_POLICY not in text:
        raise ValueError("docs/public-placeholder-policy.md has an unexpected automation section")
    text = text.replace(OLD_POLICY, NEW_POLICY, 1)
    POLICY_DOC.write_text(text, encoding="utf-8")


def main() -> int:
    try:
        changed = migrate_public_sources()
        simplify_build_validator()
        update_policy()
    except (OSError, ValueError) as exc:
        print(f"Public source copy migration failed: {exc}", file=sys.stderr)
        return 1

    print(f"Migrated {len(changed)} public source files:")
    for relative in changed:
        print(f"  - {relative}")
    print("Build-time text rewriting removed; validation remains fail-closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
