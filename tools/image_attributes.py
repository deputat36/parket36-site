#!/usr/bin/env python3
"""Normalize and validate intrinsic attributes for public content images."""

from __future__ import annotations

from html import escape, unescape
from pathlib import Path
from urllib.parse import urlsplit
import re
import xml.etree.ElementTree as ET

from PIL import Image

IMG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE | re.DOTALL)
ATTR_RE_TEMPLATE = r"\b{attribute}\s*=\s*([\"'])(.*?)\1"
NUMBER_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)")


def _attribute(tag: str, name: str) -> str | None:
    match = re.search(
        ATTR_RE_TEMPLATE.format(attribute=re.escape(name)),
        tag,
        re.IGNORECASE | re.DOTALL,
    )
    return unescape(match.group(2)) if match else None


def _set_attribute(tag: str, name: str, value: str) -> str:
    pattern = re.compile(
        ATTR_RE_TEMPLATE.format(attribute=re.escape(name)),
        re.IGNORECASE | re.DOTALL,
    )
    replacement = f'{name}="{escape(value, quote=True)}"'
    if pattern.search(tag):
        return pattern.sub(replacement, tag, count=1)
    if tag.endswith("/>"):
        return f"{tag[:-2].rstrip()} {replacement} />"
    return f"{tag[:-1].rstrip()} {replacement}>"


def _numeric(value: str | None) -> int | None:
    if not value:
        return None
    match = NUMBER_RE.match(value)
    if not match:
        return None
    number = float(match.group(1))
    if number <= 0:
        return None
    return max(1, round(number))


def _svg_dimensions(path: Path) -> tuple[int, int] | None:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return None

    width = _numeric(root.attrib.get("width"))
    height = _numeric(root.attrib.get("height"))
    if width and height:
        return width, height

    view_box = root.attrib.get("viewBox", "").replace(",", " ").split()
    if len(view_box) == 4:
        width = _numeric(view_box[2])
        height = _numeric(view_box[3])
        if width and height:
            return width, height
    return None


def image_dimensions(path: Path) -> tuple[int, int] | None:
    if path.suffix.lower() == ".svg":
        return _svg_dimensions(path)
    try:
        with Image.open(path) as image:
            width, height = image.size
    except (OSError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return int(width), int(height)


def _local_image_path(destination: Path, src: str) -> Path | None:
    parsed = urlsplit(src.strip())
    if parsed.scheme or parsed.netloc or not parsed.path.startswith("/"):
        return None
    return destination / parsed.path.lstrip("/")


def normalize_image_attributes(destination: Path, errors: list[str]) -> int:
    """Rewrite public img tags with intrinsic dimensions and validate descriptions."""
    processed = 0

    for html_file in sorted(destination.rglob("*.html")):
        relative = html_file.relative_to(destination).as_posix()
        original = html_file.read_text(encoding="utf-8")

        def replace(match: re.Match[str]) -> str:
            nonlocal processed
            tag = match.group(0)
            src = (_attribute(tag, "src") or "").strip()
            alt = _attribute(tag, "alt")
            aria_hidden = (_attribute(tag, "aria-hidden") or "").lower() == "true"
            presentational = (_attribute(tag, "role") or "").lower() == "presentation"

            if not src:
                errors.append(f"{relative}: img is missing a non-empty src")
                return tag
            if alt is None:
                errors.append(f"{relative}: img {src} is missing alt")
            elif not alt.strip() and not (aria_hidden or presentational):
                errors.append(f"{relative}: img {src} has an empty alt without presentation semantics")

            image_path = _local_image_path(destination, src)
            if image_path is None:
                processed += 1
                return tag
            if not image_path.is_file():
                errors.append(f"{relative}: local img does not exist: {src}")
                return tag

            dimensions = image_dimensions(image_path)
            if dimensions is None:
                errors.append(f"{relative}: cannot determine image dimensions: {src}")
                return tag

            width, height = dimensions
            updated = _set_attribute(tag, "width", str(width))
            updated = _set_attribute(updated, "height", str(height))
            if _attribute(updated, "decoding") is None:
                updated = _set_attribute(updated, "decoding", "async")

            filename = image_path.name.lower()
            if (
                _attribute(updated, "loading") is None
                and _attribute(updated, "fetchpriority") is None
                and ("data-placeholder-image" in updated or filename.startswith("work-"))
            ):
                updated = _set_attribute(updated, "loading", "lazy")

            processed += 1
            return updated

        rewritten = IMG_RE.sub(replace, original)
        if rewritten != original:
            html_file.write_text(rewritten, encoding="utf-8")

    if processed == 0:
        errors.append("No public img tags were found for image attribute normalization")
    return processed
