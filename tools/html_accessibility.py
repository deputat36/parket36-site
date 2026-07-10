#!/usr/bin/env python3
"""Inject mandatory accessibility markup into the generated public HTML."""

from __future__ import annotations

from pathlib import Path
import re

SKIP_LINK = '<a class="skip-link" href="#main-content">Перейти к содержанию</a>'
BODY_RE = re.compile(r"<body(?P<attrs>[^>]*)>", re.IGNORECASE)
MAIN_RE = re.compile(r"<main(?P<attrs>[^>]*)>", re.IGNORECASE)
MENU_BUTTON_RE = re.compile(
    r"<button(?P<attrs>[^>]*\bdata-menu-toggle\b[^>]*)>",
    re.IGNORECASE,
)
NAV_RE = re.compile(r"<nav(?P<attrs>[^>]*\bdata-nav\b[^>]*)>", re.IGNORECASE)


def attribute_value(tag: str, name: str) -> str | None:
    match = re.search(rf"\b{re.escape(name)}=[\"']([^\"']*)[\"']", tag, re.IGNORECASE)
    return match.group(1) if match else None


def ensure_attribute(tag: str, name: str, value: str, context: str, errors: list[str]) -> str:
    current = attribute_value(tag, name)
    if current is not None:
        if current != value:
            errors.append(f"{context}: {name} must be {value}, found {current}")
        return tag
    return tag[:-1] + f' {name}="{value}">'


def inject_skip_link(text: str, context: str, errors: list[str]) -> str:
    count = text.count(SKIP_LINK)
    if count > 1:
        errors.append(f"{context}: duplicate skip links")
        return text
    if count == 1:
        return text

    body = BODY_RE.search(text)
    if body is None:
        errors.append(f"{context}: body tag is missing")
        return text

    return text[: body.end()] + "\n" + SKIP_LINK + text[body.end() :]


def inject_main_id(text: str, context: str, errors: list[str]) -> str:
    main = MAIN_RE.search(text)
    if main is None:
        errors.append(f"{context}: main tag is missing")
        return text

    original = main.group(0)
    updated = ensure_attribute(original, "id", "main-content", context, errors)
    return text[: main.start()] + updated + text[main.end() :]


def inject_menu_aria(text: str, context: str, errors: list[str]) -> str:
    button = MENU_BUTTON_RE.search(text)
    nav = NAV_RE.search(text)

    if button is None and nav is None:
        return text
    if button is None or nav is None:
        errors.append(f"{context}: menu button and navigation must be present together")
        return text

    button_tag = button.group(0)
    button_tag = ensure_attribute(button_tag, "aria-controls", "site-navigation", context, errors)
    button_tag = ensure_attribute(button_tag, "aria-expanded", "false", context, errors)
    text = text[: button.start()] + button_tag + text[button.end() :]

    nav = NAV_RE.search(text)
    if nav is None:
        errors.append(f"{context}: navigation disappeared during accessibility transform")
        return text
    nav_tag = ensure_attribute(nav.group(0), "id", "site-navigation", context, errors)
    return text[: nav.start()] + nav_tag + text[nav.end() :]


def validate_accessibility_markup(text: str, context: str, errors: list[str]) -> None:
    if text.count(SKIP_LINK) != 1:
        errors.append(f"{context}: expected exactly one static skip link")
    main_landmarks = re.findall(
        r"<main\b[^>]*\bid=[\"']main-content[\"']",
        text,
        re.IGNORECASE,
    )
    if len(main_landmarks) != 1:
        errors.append(f"{context}: expected exactly one main-content landmark")

    button = MENU_BUTTON_RE.search(text)
    nav = NAV_RE.search(text)
    if button is not None:
        button_tag = button.group(0)
        if attribute_value(button_tag, "aria-controls") != "site-navigation":
            errors.append(f"{context}: menu button aria-controls is missing or invalid")
        if attribute_value(button_tag, "aria-expanded") != "false":
            errors.append(f"{context}: initial menu aria-expanded must be false")
    if nav is not None and attribute_value(nav.group(0), "id") != "site-navigation":
        errors.append(f"{context}: navigation id must be site-navigation")


def inject_accessibility_html(destination: Path, errors: list[str]) -> None:
    """Make skip navigation and menu relationships available without JavaScript."""
    for html_file in sorted(destination.rglob("*.html")):
        context = html_file.relative_to(destination).as_posix()
        text = html_file.read_text(encoding="utf-8")
        text = inject_skip_link(text, context, errors)
        text = inject_main_id(text, context, errors)
        text = inject_menu_aria(text, context, errors)
        validate_accessibility_markup(text, context, errors)
        html_file.write_text(text, encoding="utf-8")
