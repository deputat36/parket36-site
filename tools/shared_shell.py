#!/usr/bin/env python3
"""Apply shared header, footer and CTA fragments to selected public pages."""

from __future__ import annotations

from pathlib import Path
import re

PILOT_PAGES = (
    Path("index.html"),
    Path("zayavka/index.html"),
)

FRAGMENTS = {
    "header": Path("data/shared-shell/header.html"),
    "final-cta": Path("data/shared-shell/final-cta.html"),
    "footer": Path("data/shared-shell/footer.html"),
    "mobile-cta": Path("data/shared-shell/mobile-cta.html"),
}

PATTERNS = {
    "header": re.compile(r'<header\b[^>]*class=["\']topbar["\'][^>]*>.*?</header>', re.IGNORECASE | re.DOTALL),
    "final-cta": re.compile(r'<section\b[^>]*class=["\']final-cta["\'][^>]*>.*?</section>', re.IGNORECASE | re.DOTALL),
    "footer": re.compile(r'<footer\b[^>]*class=["\']footer["\'][^>]*>.*?</footer>', re.IGNORECASE | re.DOTALL),
    "mobile-cta": re.compile(r'<div\b[^>]*class=["\']mobile-cta["\'][^>]*>.*?</div>', re.IGNORECASE | re.DOTALL),
}


def load_fragments(root: Path, errors: list[str]) -> dict[str, str]:
    loaded: dict[str, str] = {}
    for name, relative in FRAGMENTS.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"Shared shell fragment is missing: {relative.as_posix()}")
            continue
        text = path.read_text(encoding="utf-8").strip()
        marker = f"<!-- shared-shell:{name} -->"
        if text.count(marker) != 1:
            errors.append(f"{relative.as_posix()}: expected exactly one marker {marker}")
            continue
        loaded[name] = text
    return loaded


def replace_fragment(
    text: str,
    name: str,
    fragment: str,
    context: str,
    errors: list[str],
) -> str:
    updated, count = PATTERNS[name].subn(fragment, text, count=1)
    if count != 1:
        errors.append(f"{context}: expected exactly one replaceable {name} block, found {count}")
        return text
    return updated


def validate_page(text: str, context: str, fragments: dict[str, str], errors: list[str]) -> None:
    for name, fragment in fragments.items():
        marker = f"<!-- shared-shell:{name} -->"
        if text.count(marker) != 1:
            errors.append(f"{context}: expected exactly one {marker}")
        if text.count(fragment) != 1:
            errors.append(f"{context}: shared {name} fragment differs from the canonical source")


def apply_shared_shell(root: Path, destination: Path, errors: list[str]) -> None:
    """Render shared shell fragments into the selected generated HTML pages."""
    fragments = load_fragments(root, errors)
    if len(fragments) != len(FRAGMENTS):
        return

    for relative in PILOT_PAGES:
        page = destination / relative
        context = relative.as_posix()
        if not page.is_file():
            errors.append(f"Shared shell pilot page is missing from public build: {context}")
            continue

        text = page.read_text(encoding="utf-8")
        for name in ("header", "final-cta", "footer", "mobile-cta"):
            text = replace_fragment(text, name, fragments[name], context, errors)
        validate_page(text, context, fragments, errors)
        page.write_text(text, encoding="utf-8")
