#!/usr/bin/env python3
"""Create a clean _site directory for GitHub Pages deployment."""

from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "_site"

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


def copy_path(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination)
    elif source.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


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

    required = ["index.html", "404.html", "CNAME", "robots.txt", "sitemap.xml"]
    missing = [name for name in required if not (DEST / name).exists()]
    if missing:
        print("Missing required public files:", ", ".join(missing))
        return 1

    total = sum(1 for path in DEST.rglob("*") if path.is_file())
    print(f"Prepared {total} public files in {DEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
