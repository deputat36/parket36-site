#!/usr/bin/env python3
"""Create and validate a clean _site directory for GitHub Pages."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import shutil
import sys
import xml.etree.ElementTree as ET

from css_bundle import prepare_css_bundle
from image_attributes import normalize_image_attributes
from site_settings import load_config

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "_site"
SITE_CONFIG = load_config()
DOMAIN = str(SITE_CONFIG["domain"])
DEFAULT_REQUEST_DIR = str(SITE_CONFIG["default_request_path"]).strip("/").split("/", 1)[0]
LEAD_RELIABILITY_SCRIPT = '<script src="/js/lead-reliability.js" defer></script>'
MAIN_SCRIPT = '<script src="/js/main.js" defer></script>'

PUBLIC_DIRS = {
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
    "pozvonit-ivanu",
    DEFAULT_REQUEST_DIR,
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


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {k.lower(): (v or "") for k, v in attrs_list}
        for attr in ("href", "src"):
            value = attrs.get(attr)
            if value:
                self.links.append((attr, value))
        if tag.lower() == "meta" and attrs.get("property", "").lower() == "og:image":
            content = attrs.get("content")
            if content:
                self.links.append(("og:image", content))


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


def inject_lead_reliability(errors: list[str]) -> None:
    script_path = DEST / "js" / "lead-reliability.js"
    if not script_path.exists():
        errors.append("Lead reliability script is missing from the public build")
        return

    for html_file in sorted(DEST.rglob("*.html")):
        text = html_file.read_text(encoding="utf-8")
        if 'id="request-form"' not in text:
            continue
        if LEAD_RELIABILITY_SCRIPT in text:
            continue
        if MAIN_SCRIPT not in text:
            errors.append(
                f"{html_file.relative_to(DEST).as_posix()}: request form page is missing main.js"
            )
            continue
        text = text.replace(
            MAIN_SCRIPT,
            f"{LEAD_RELIABILITY_SCRIPT}\n{MAIN_SCRIPT}",
            1,
        )
        html_file.write_text(text, encoding="utf-8")


def iter_source_html() -> list[Path]:
    result: list[Path] = []
    for path in ROOT.rglob("*.html"):
        parts = path.relative_to(ROOT).parts
        if any(part in IGNORED_DIRS for part in parts):
            continue
        result.append(path)
    return sorted(result)


def url_to_built_file(url: str, base_file: Path | None = None) -> Path | None:
    value = url.strip()
    if not value or value.startswith(("#", "tel:", "mailto:", "javascript:", "data:")):
        return None

    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        if not value.startswith(DOMAIN + "/"):
            return None
        path = parsed.path
    else:
        path = parsed.path

    if not path:
        return None
    if path == "/":
        return DEST / "index.html"

    if path.startswith("/"):
        relative = path.lstrip("/")
        candidate = DEST / relative
    else:
        if base_file is None:
            return None
        candidate = base_file.parent / path

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


def validate_public_links(errors: list[str]) -> None:
    for html_file in sorted(DEST.rglob("*.html")):
        parser = LinkParser()
        parser.feed(html_file.read_text(encoding="utf-8"))
        rel = html_file.relative_to(DEST).as_posix()
        for attr, value in parser.links:
            target = url_to_built_file(value, html_file)
            if target is None:
                continue
            if not target.exists():
                target_display = target.relative_to(DEST).as_posix()
                errors.append(f"{rel}: public build has broken {attr}={value} -> {target_display}")


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
    prepare_css_bundle(ROOT, DEST, errors)
    normalize_image_attributes(DEST, errors)
    inject_lead_reliability(errors)

    required = ["index.html", "404.html", "CNAME", "robots.txt", "sitemap.xml"]
    missing = [name for name in required if not (DEST / name).exists()]
    if missing:
        errors.append("Missing required public files: " + ", ".join(missing))

    validate_public_html(errors)
    validate_sitemap(errors)
    validate_public_links(errors)
    validate_private_files(errors)

    if errors:
        print("Public build validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    total = sum(1 for path in DEST.rglob("*") if path.is_file())
    html_total = sum(1 for path in DEST.rglob("*.html") if path.is_file())
    css_total = sum(1 for path in DEST.rglob("*.css") if path.is_file())
    print(
        f"Prepared {total} public files, including {html_total} HTML pages "
        f"and {css_total} CSS bundle, in {DEST}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
