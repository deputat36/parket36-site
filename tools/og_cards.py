#!/usr/bin/env python3
"""Generate raster Open Graph cards for the public build."""

from __future__ import annotations

from hashlib import sha256
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
from typing import Any
from urllib.parse import urlsplit

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1200
HEIGHT = 630
PHONE = "8 (900) 926-79-29"
BRAND = "ПАРКЕТ36"
STRUCTURED_IMAGE_TYPES = {"Article", "ProfessionalService"}
FONT_REGULAR_CANDIDATES = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
)
FONT_BOLD_CANDIDATES = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
)
META_CONTENT_RE_TEMPLATE = (
    r'(<meta\b(?=[^>]*\b{attribute}=["\']{key}["\'])[^>]*?\bcontent=["\'])'
    r'([^"\']*)(["\'][^>]*>)'
)
JSON_LD_SCRIPT_RE = re.compile(
    r'(<script\b[^>]*\btype=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',
    re.IGNORECASE | re.DOTALL,
)


class OgPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.properties: dict[str, str] = {}
        self.names: dict[str, str] = {}
        self.canonical = ""

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key.lower(): (value or "") for key, value in attrs_list}
        if tag.lower() == "meta":
            prop = attrs.get("property", "").lower()
            name = attrs.get("name", "").lower()
            if prop:
                self.properties[prop] = attrs.get("content", "").strip()
            if name:
                self.names[name] = attrs.get("content", "").strip()
        elif tag.lower() == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonical = attrs.get("href", "").strip()


def _font_path(candidates: tuple[Path, ...]) -> Path:
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError("A DejaVu Sans or Liberation Sans font is required for OG card generation")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = FONT_BOLD_CANDIDATES if bold else FONT_REGULAR_CANDIDATES
    return ImageFont.truetype(str(_font_path(candidates)), size)


def _fit_line(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> str:
    if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
        return text
    clipped = text
    while clipped and draw.textbbox((0, 0), clipped + "…", font=font)[2] > max_width:
        clipped = clipped[:-1]
    return clipped.rstrip() + "…"


def _wrap(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    max_lines: int,
) -> list[str]:
    normalized = " ".join(text.split())
    words = normalized.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = _fit_line(draw, word, font, max_width)
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and " ".join(lines) != normalized:
        lines[-1] = _fit_line(draw, lines[-1] + "…", font, max_width)
    return lines[:max_lines]


def _section_label(canonical: str) -> str:
    path = urlsplit(canonical).path.strip("/")
    if not path:
        return "ЦИКЛЁВКА И РЕСТАВРАЦИЯ ПАРКЕТА"
    first = path.split("/", 1)[0]
    return {
        "sovety": "СОВЕТЫ ПО ПАРКЕТУ",
        "uslugi": "УСЛУГИ ПО ПОЛУ",
        "resheniya": "ГОТОВЫЕ РЕШЕНИЯ",
        "ceny": "СТОИМОСТЬ РАБОТ",
        "o-mastere": "МАСТЕР ИВАН",
        "portfolio": "ПРИМЕРЫ ЗАДАЧ",
        "kontakty": "КОНТАКТЫ",
        "zayavka": "ОЦЕНКА ПО ФОТО",
        "voprosy-i-otvety": "ВОПРОСЫ И ОТВЕТЫ",
        "kak-rabotaem": "КАК ПРОХОДИТ РАБОТА",
    }.get(first, "ПАРКЕТ И ДЕРЕВЯННЫЕ ПОЛЫ")


def render_card(title: str, description: str, canonical: str, output: Path) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#f6e7d3")
    draw = ImageDraw.Draw(image)

    for y in range(HEIGHT):
        ratio = y / (HEIGHT - 1)
        start = (255, 248, 239)
        end = (111, 70, 40)
        color = tuple(round(start[i] * (1 - ratio) + end[i] * ratio) for i in range(3))
        draw.line((0, y, WIDTH, y), fill=color)

    for x in range(760, WIDTH + 120, 96):
        draw.rounded_rectangle(
            (x, 0, x + 62, HEIGHT),
            radius=22,
            fill="#6f4628",
            outline="#8d6041",
            width=3,
        )
        draw.arc((x + 10, 70, x + 52, 230), 70, 290, fill="#c79d74", width=4)
        draw.arc((x + 10, 310, x + 52, 490), 70, 290, fill="#c79d74", width=4)

    draw.rounded_rectangle(
        (56, 48, 1042, 582),
        radius=38,
        fill="#fffaf4",
        outline="#e1c6a6",
        width=3,
    )
    draw.rounded_rectangle((88, 82, 178, 172), radius=22, fill="#6f4628")
    draw.text((133, 126), "36", font=_font(40, True), fill="#fff8ef", anchor="mm")
    draw.text((202, 91), BRAND, font=_font(40, True), fill="#6f4628")
    draw.text(
        (202, 139),
        "мастер Иван · Воронеж и область",
        font=_font(22),
        fill="#705746",
    )

    label = _section_label(canonical)
    label_font = _font(20, True)
    label_width = draw.textbbox((0, 0), label, font=label_font)[2] + 36
    draw.rounded_rectangle((88, 198, 88 + label_width, 238), radius=20, fill="#ead2b6")
    draw.text((106, 207), label, font=label_font, fill="#6f4628")

    title_size = 54
    title_lines: list[str] = []
    while title_size >= 42:
        title_font = _font(title_size, True)
        title_lines = _wrap(draw, title, title_font, 820, 3)
        if len(title_lines) * (title_size + 8) <= 190:
            break
        title_size -= 4
    y = 264
    for line in title_lines:
        draw.text((88, y), line, font=title_font, fill="#24170f")
        y += title_size + 8

    description_font = _font(25)
    description_lines = _wrap(draw, description, description_font, 820, 2)
    y = max(y + 10, 445)
    for line in description_lines:
        draw.text((88, y), line, font=description_font, fill="#5f493b")
        y += 36

    draw.rounded_rectangle((88, 522, 390, 566), radius=22, fill="#6f4628")
    draw.text((239, 544), PHONE, font=_font(22, True), fill="#fff8ef", anchor="mm")
    draw.text((418, 532), "parket36.ru", font=_font(22, True), fill="#6f4628")

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="PNG", optimize=True, compress_level=9)


def _replace_meta(
    text: str,
    attribute: str,
    key: str,
    value: str,
) -> tuple[str, bool]:
    pattern = re.compile(
        META_CONTENT_RE_TEMPLATE.format(
            attribute=re.escape(attribute),
            key=re.escape(key),
        ),
        re.IGNORECASE,
    )
    updated, count = pattern.subn(
        lambda match: match.group(1) + escape(value, quote=True) + match.group(3),
        text,
        count=1,
    )
    return updated, count == 1


def _set_meta(text: str, attribute: str, key: str, value: str) -> str:
    updated, replaced = _replace_meta(text, attribute, key, value)
    if replaced:
        return updated
    marker = (
        f'  <meta {attribute}="{escape(key, quote=True)}" '
        f'content="{escape(value, quote=True)}">\n'
    )
    if "</head>" not in text:
        return text
    return text.replace("</head>", marker + "</head>", 1)


def _schema_types(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str)}
    return set()


def _walk_schema(value: Any):
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk_schema(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_schema(nested)


def _set_structured_images(payload: Any, public_url: str) -> int:
    updated = 0
    for node in _walk_schema(payload):
        if _schema_types(node.get("@type")) & STRUCTURED_IMAGE_TYPES:
            if node.get("image") != public_url:
                node["image"] = public_url
            updated += 1
    return updated


def _rewrite_structured_images(
    text: str,
    public_url: str,
    relative: str,
    errors: list[str],
) -> tuple[str, int]:
    updated_nodes = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal updated_nodes
        raw = match.group(2).strip()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(
                f"{relative}: cannot update JSON-LD image "
                f"(line {exc.lineno}, column {exc.colno}: {exc.msg})"
            )
            return match.group(0)
        count = _set_structured_images(payload, public_url)
        updated_nodes += count
        if count == 0:
            return match.group(0)
        compact = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        return match.group(1) + compact + match.group(3)

    return JSON_LD_SCRIPT_RE.sub(replace, text), updated_nodes


def _validate_structured_images(
    text: str,
    image_url: str,
    relative: str,
    errors: list[str],
) -> int:
    checked = 0
    for match in JSON_LD_SCRIPT_RE.finditer(text):
        try:
            payload = json.loads(match.group(2).strip())
        except json.JSONDecodeError:
            continue
        for node in _walk_schema(payload):
            if not (_schema_types(node.get("@type")) & STRUCTURED_IMAGE_TYPES):
                continue
            checked += 1
            if node.get("image") != image_url:
                errors.append(
                    f"{relative}: Article/ProfessionalService image must match generated og:image"
                )
    return checked


def apply_og_cards(destination: Path, domain: str, errors: list[str]) -> int:
    output_dir = destination / "img" / "og"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generated = 0
    for html_file in sorted(destination.rglob("*.html")):
        text = html_file.read_text(encoding="utf-8")
        parser = OgPageParser()
        parser.feed(text)
        relative = html_file.relative_to(destination).as_posix()
        title = parser.properties.get("og:title", "")
        description = parser.properties.get("og:description", "")
        canonical = parser.canonical
        noindex = "noindex" in parser.names.get("robots", "").lower()

        if not title or not description or not canonical:
            if not noindex:
                errors.append(
                    f"{relative}: OG card requires og:title, og:description and canonical"
                )
            continue
        if not canonical.startswith(domain + "/"):
            errors.append(f"{relative}: canonical is outside {domain}")
            continue

        digest = sha256(
            f"{canonical}\n{title}\n{description}".encode("utf-8")
        ).hexdigest()[:16]
        filename = f"og-{digest}.png"
        output = output_dir / filename
        try:
            render_card(title, description, canonical, output)
        except (OSError, RuntimeError) as exc:
            errors.append(f"{relative}: cannot generate OG card: {exc}")
            continue

        public_url = f"{domain}/img/og/{filename}"
        text = _set_meta(text, "property", "og:image", public_url)
        text = _set_meta(text, "property", "og:image:type", "image/png")
        text = _set_meta(text, "property", "og:image:width", str(WIDTH))
        text = _set_meta(text, "property", "og:image:height", str(HEIGHT))
        text = _set_meta(text, "name", "twitter:card", "summary_large_image")
        text = _set_meta(text, "name", "twitter:image", public_url)
        text, _ = _rewrite_structured_images(text, public_url, relative, errors)
        html_file.write_text(text, encoding="utf-8")
        generated += 1

    if generated == 0:
        errors.append("No raster OG cards were generated")
    return generated


def validate_og_cards(destination: Path, domain: str, errors: list[str]) -> int:
    checked = 0
    structured_checked = 0
    for html_file in sorted(destination.rglob("*.html")):
        text = html_file.read_text(encoding="utf-8")
        parser = OgPageParser()
        parser.feed(text)
        image_url = parser.properties.get("og:image", "")
        if not image_url:
            continue
        relative = html_file.relative_to(destination).as_posix()
        expected_prefix = f"{domain}/img/og/"
        if not image_url.startswith(expected_prefix) or not image_url.endswith(".png"):
            errors.append(f"{relative}: public og:image must be a generated PNG")
            continue
        image_path = destination / image_url.removeprefix(domain).lstrip("/")
        if not image_path.is_file():
            errors.append(
                f"{relative}: generated og:image is missing: "
                f"{image_path.relative_to(destination)}"
            )
            continue
        try:
            with Image.open(image_path) as image:
                if image.format != "PNG" or image.size != (WIDTH, HEIGHT):
                    errors.append(f"{relative}: OG card must be PNG {WIDTH}x{HEIGHT}")
        except OSError as exc:
            errors.append(f"{relative}: cannot read OG card: {exc}")
            continue

        required = {
            "og:image:type": "image/png",
            "og:image:width": str(WIDTH),
            "og:image:height": str(HEIGHT),
        }
        for key, value in required.items():
            if parser.properties.get(key) != value:
                errors.append(f"{relative}: {key} must be {value}")
        if parser.names.get("twitter:card") != "summary_large_image":
            errors.append(f"{relative}: twitter:card must be summary_large_image")
        if parser.names.get("twitter:image") != image_url:
            errors.append(f"{relative}: twitter:image must match og:image")
        structured_checked += _validate_structured_images(text, image_url, relative, errors)
        checked += 1

    if checked == 0:
        errors.append("No raster OG cards were validated")
    if structured_checked == 0:
        errors.append("No Article or ProfessionalService JSON-LD images were validated")
    return checked
