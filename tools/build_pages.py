#!/usr/bin/env python3
"""Create and validate a clean _site directory for GitHub Pages."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit
import shutil
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "_site"
DOMAIN = "https://parket36.ru"

PUBLIC_DIRS = {
    "css",
    "js",
    "img",
    "uslugi",
    "o-mastere",
    "kontakty",
    "portfolio",
    "ceny",
    "resheniya",
    "sovety",
    "politika",
    "kak-rabotaem",
    "voprosy-i-otvety",
    "zayavka",
}
PUBLIC_FILES = {
    "index.html",
    "404.html",
    "CNAME",
    "robots.txt",
    "sitemap.xml",
    ".nojekyll",
    "manifest.webmanifest",
}
IGNORED_DIRS = {".git", ".github", "tools", "data", "node_modules", "_site"}
INTERNAL_WORKING_PATHS = {
    Path("foto-dlya-sajta"),
    Path("portfolio") / "shablon-kejsa",
}


def is_internal_working_path(relative: Path) -> bool:
    return any(relative == path or path in relative.parents for path in INTERNAL_WORKING_PATHS)


def copy_path(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination)
    elif source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def remove_internal_working_paths() -> None:
    for relative in INTERNAL_WORKING_PATHS:
        target = DEST / relative
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()


def iter_source_html() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*.html"):
        parts = path.relative_to(ROOT).parts
        if any(part in IGNORED_DIRS for part in parts):
            continue
        result.append(path)
    return sorted(result)


def url_to_built_file(url: str) -> Path | None:
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc:
        if not url.startswith(DOMAIN + "/"):
            return None
        path = parsed.path
    else:
        path = parsed.path

    relative = path.lstrip("/")
    if not relative:
        return DEST / "index.html"
    candidate = DEST / relative
    if path.endswith("/"):
        return candidate / "index.html"
    if candidate.suffix:
        return candidate
    return candidate / "index.html"


def validate_public_html(errors: list[str]) -> None:
    for source in iter_source_html():
        relative = source.relative_to(ROOT)
        if is_internal_working_path(relative):
            continue
        built = DEST / relative
        if not built.exists():
            errors.append(
                f"Public HTML page was not copied: {relative.as_posix()}. "
                "Add its top-level directory to PUBLIC_DIRS."
            )


def validate_sitemap(errors: list[str]) -> None:
    sitemap = DEST / "sitemap.xml"
    if not sitemap.exists():
        errors.append("sitemap.xml is missing from the public build")
        return

    try:
        tree = ET.parse(sitemap)
    except ET.ParseError as exc:
        errors.append(f"Public sitemap.xml is invalid XML: {exc}")
        return

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    for node in tree.findall("sm:url/sm:loc", ns):
        url = (node.text or "").strip()
        target = url_to_built_file(url)
        if target is None:
            errors.append(f"Unexpected sitemap domain: {url}")
        elif not target.exists():
            errors.append(
                f"Sitemap URL is absent from the public build: {url} -> "
                f"{target.relative_to(DEST).as_posix()}"
            )


def validate_private_files(errors: list[str]) -> None:
    forbidden = [
        DEST / "data",
        DEST / "tools",
        DEST / ".github",
        DEST / "README.md",
    ]
    for path in forbidden:
        if path.exists():
            errors.append(f"Private project file leaked into public build: {path.name}")

    for relative in INTERNAL_WORKING_PATHS:
        target = DEST / relative
        if target.exists():
            errors.append(f"Internal working page leaked into public build: {relative.as_posix()}")


def main() -> int:
    if DEST.exists():
        shutil.rmtree(DEST)
    DEST.mkdir()

    for name in sorted(PUBLIC_DIRS):
        source = ROOT / name
        if source.exists():
            copy_path(source, DEST / name)

    for name in sorted(PUBLIC_FILES):
        source = ROOT / name
        if source.exists():
            copy_path(source, DEST / name)

    remove_internal_working_paths()

    errors: list[str] = []
    required = ["index.html", "404.html", "CNAME", "robots.txt", "sitemap.xml"]
    missing = [name for name in required if not (DEST / name).exists()]
    if missing:
        errors.append("Missing required public files: " + ", ".join(missing))

    validate_public_html(errors)
    validate_sitemap(errors)
    validate_private_files(errors)

    if errors:
        print("Public build validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    total = sum(1 for path in DEST.rglob("*") if path.is_file())
    html_total = sum(1 for path in DEST.rglob("*.html") if path.is_file())
    print(f"Prepared {total} public files, including {html_total} HTML pages, in {DEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())