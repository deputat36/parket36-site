#!/usr/bin/env python3
"""Validate the isolated Parket36 redesign prototype and generated assets."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE = ROOT / "design" / "prototypes" / "homepage-v1.html"
CSS_FILES = tuple(
    ROOT / "design" / "prototypes" / f"homepage-v1-{name}.css"
    for name in ("base", "hero", "content", "responsive")
)
GENERATED_CSS = ROOT / "design" / "generated" / "parket36-tokens.css"
DOC = ROOT / "docs" / "design" / "parket36-prototype-v1.md"
LOGOS = tuple(ROOT / "design" / "logos" / f"parket36-mark-{name}.svg" for name in ("a", "b", "c"))

REQUIRED_HTML = (
    'meta name="robots" content="noindex,nofollow"',
    "data-design-prototype",
    "не является опубликованной версией сайта",
    'href="../generated/parket36-tokens.css"',
    'src="../logos/parket36-mark-a.svg"',
    "Получить оценку по фото",
    "Этот прототип не отправляет данные",
)
REQUIRED_CSS = (
    "var(--p36-color-semantic-action-primary)",
    "var(--p36-font-family-display)",
    "var(--p36-size-touch-min)",
    "@media (max-width:640px)",
    "@media (prefers-reduced-motion:reduce)",
    ":focus-visible",
)
FORBIDDEN = ("#6f4628", "#9b683d", "#d7a86e", "supabase", "parket-public-lead", "<script", "<form")


class PrototypeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h1_count = 0
        self.images_without_alt: list[str] = []
        self.local_assets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if tag == "img" and "alt" not in values:
            self.images_without_alt.append(values.get("src", "<unknown>") or "<unknown>")
        if tag in {"img", "link"}:
            path = values.get("src") or values.get("href")
            if path and not path.startswith(("http://", "https://", "#", "tel:")):
                self.local_assets.append(path)


def main() -> int:
    findings: list[str] = []
    required_files = (PROTOTYPE, *CSS_FILES, GENERATED_CSS, DOC, *LOGOS)
    for path in required_files:
        if not path.is_file():
            findings.append(f"missing design prototype asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    generation = subprocess.run(
        [sys.executable, "tools/build_design_token_css.py", "--check"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if generation.returncode:
        findings.append(generation.stdout.strip() or generation.stderr.strip())

    html = PROTOTYPE.read_text(encoding="utf-8")
    css = "\n".join(path.read_text(encoding="utf-8") for path in CSS_FILES)
    lowered = f"{html}\n{css}".lower()

    for marker in REQUIRED_HTML:
        if marker not in html:
            findings.append(f"prototype HTML is missing marker: {marker}")
    for marker in REQUIRED_CSS:
        if marker not in css:
            findings.append(f"prototype CSS is missing marker: {marker}")
    for marker in FORBIDDEN:
        if marker in lowered:
            findings.append(f"isolated prototype contains forbidden marker: {marker}")

    parser = PrototypeParser()
    parser.feed(html)
    if parser.h1_count != 1:
        findings.append(f"prototype must contain exactly one h1, found {parser.h1_count}")
    for source in parser.images_without_alt:
        findings.append(f"prototype image is missing alt: {source}")

    for raw_path in parser.local_assets:
        asset = (PROTOTYPE.parent / raw_path).resolve()
        try:
            asset.relative_to(ROOT)
        except ValueError:
            findings.append(f"prototype asset escapes repository: {raw_path}")
            continue
        if not asset.is_file():
            findings.append(f"prototype references missing asset: {raw_path}")

    titles: set[str] = set()
    for logo in LOGOS:
        try:
            root = ET.parse(logo).getroot()
        except (OSError, ET.ParseError) as exc:
            findings.append(f"invalid SVG {logo.relative_to(ROOT)}: {exc}")
            continue
        title = root.find("{http://www.w3.org/2000/svg}title")
        desc = root.find("{http://www.w3.org/2000/svg}desc")
        if title is None or not (title.text or "").strip():
            findings.append(f"SVG title is missing: {logo.relative_to(ROOT)}")
        else:
            if title.text in titles:
                findings.append(f"SVG titles must be unique: {title.text}")
            titles.add(title.text)
        if desc is None or not (desc.text or "").strip():
            findings.append(f"SVG description is missing: {logo.relative_to(ROOT)}")

    if findings:
        print("Design prototype findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Design prototype passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
