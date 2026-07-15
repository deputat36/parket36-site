#!/usr/bin/env python3
"""Apply shared header, footer and CTA fragments to selected public pages."""

from __future__ import annotations

from pathlib import Path
import re

DEFAULT_REQUEST_LABEL = "Оценка по фото"

PAGE_PROFILES = {
    Path("index.html"): {
        "components": ("header", "final-cta", "footer", "mobile-cta"),
        "active_nav": None,
        "request_href": "#request",
    },
    Path("zayavka/index.html"): {
        "components": ("header", "final-cta", "footer", "mobile-cta"),
        "active_nav": None,
        "request_href": "#request",
    },
    Path("uslugi/index.html"): {
        "components": ("header", "footer", "mobile-cta"),
        "active_nav": "/uslugi/",
        "request_href": "/zayavka/",
    },
    Path("uslugi/parket-i-poly/index.html"): {
        "components": ("header", "mobile-cta"),
        "active_nav": "/uslugi/",
        "request_href": "/zayavka/",
    },
    Path("uslugi/ciklevka-parketa/index.html"): {
        "components": ("header", "mobile-cta"),
        "active_nav": "/uslugi/",
        "request_href": "/zayavka/",
    },
    Path("uslugi/restavraciya-parketa/index.html"): {
        "components": ("header", "mobile-cta"),
        "active_nav": "/uslugi/",
        "request_href": "/zayavka/",
    },
    Path("uslugi/ukladka-parketa/index.html"): {
        "components": ("header", "mobile-cta"),
        "active_nav": "/uslugi/",
        "request_href": "/zayavka/",
    },
    Path("uslugi/ukladka-laminata/index.html"): {
        "components": ("header", "mobile-cta"),
        "active_nav": "/uslugi/",
        "request_href": "/zayavka/",
    },
    Path("uslugi/shlifovka-doshchatogo-pola/index.html"): {
        "components": ("header", "mobile-cta"),
        "active_nav": "/uslugi/",
        "request_href": "/zayavka/",
    },
    Path("uslugi/terrasy-i-derevyannye-poly/index.html"): {
        "components": ("header", "mobile-cta"),
        "active_nav": "/uslugi/",
        "request_href": "/zayavka/",
    },
    Path("uslugi/pokrytie-lakom-i-maslom/index.html"): {
        "components": ("header", "mobile-cta"),
        "active_nav": "/uslugi/",
        "request_href": "/zayavka/",
    },
    Path("ceny/index.html"): {
        "components": ("header", "footer", "mobile-cta"),
        "active_nav": "/ceny/",
        "request_href": "/zayavka/",
    },
    Path("o-mastere/index.html"): {
        "components": ("header", "footer", "mobile-cta"),
        "active_nav": "/o-mastere/",
        "request_href": "/zayavka/",
    },
    Path("portfolio/index.html"): {
        "components": ("header", "footer", "mobile-cta"),
        "active_nav": "/portfolio/",
        "request_href": "/zayavka/",
    },
    Path("sovety/index.html"): {
        "components": ("header", "footer", "mobile-cta"),
        "active_nav": "/sovety/",
        "request_href": "/zayavka/",
    },
    Path("kontakty/index.html"): {
        "components": ("header", "footer", "mobile-cta"),
        "active_nav": "/kontakty/",
        "request_href": "#callback",
        "request_label": "Обратный звонок",
    },
    Path("resheniya/index.html"): {
        "components": ("header", "footer", "mobile-cta"),
        "active_nav": None,
        "request_href": "/zayavka/",
    },
    Path("voprosy-i-otvety/index.html"): {
        "components": ("header", "footer", "mobile-cta"),
        "active_nav": None,
        "request_href": "/zayavka/",
    },
    Path("kak-rabotaem/index.html"): {
        "components": ("header", "footer", "mobile-cta"),
        "active_nav": None,
        "request_href": "/zayavka/",
    },
}

# Backward-compatible name retained for the static workflow guardrail.
PILOT_PAGES = tuple(PAGE_PROFILES)

FRAGMENTS = {
    "header": Path("data/shared-shell/header.htmlfrag"),
    "final-cta": Path("data/shared-shell/final-cta.htmlfrag"),
    "footer": Path("data/shared-shell/footer.htmlfrag"),
    "mobile-cta": Path("data/shared-shell/mobile-cta.htmlfrag"),
}

FRAGMENT_MARKERS = {
    "header": "<!-- shared-shell:header -->",
    "final-cta": "<!-- shared-shell:final-cta -->",
    "footer": "<!-- shared-shell:footer -->",
    "mobile-cta": "<!-- shared-shell:mobile-cta -->",
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
        marker = FRAGMENT_MARKERS[name]
        if text.count(marker) != 1:
            errors.append(f"{relative.as_posix()}: expected exactly one marker {marker}")
            continue
        loaded[name] = text
    return loaded


def render_header(fragment: str, active_nav: str | None, context: str, errors: list[str]) -> str:
    if not active_nav:
        return fragment

    needle = f'<a href="{active_nav}">'
    if fragment.count(needle) != 1:
        errors.append(f"{context}: shared header cannot resolve active navigation link {active_nav}")
        return fragment

    return fragment.replace(
        needle,
        f'<a class="active" aria-current="page" href="{active_nav}">',
        1,
    )


def render_mobile_cta(
    fragment: str,
    request_href: str,
    request_label: str,
    context: str,
    errors: list[str],
) -> str:
    needle = f'<a href="#request">{DEFAULT_REQUEST_LABEL}</a>'
    if fragment.count(needle) != 1:
        errors.append(f"{context}: shared mobile CTA must contain one canonical request action")
        return fragment
    return fragment.replace(
        needle,
        f'<a href="{request_href}">{request_label}</a>',
        1,
    )


def render_fragment(
    name: str,
    fragment: str,
    profile: dict[str, object],
    context: str,
    errors: list[str],
) -> str:
    if name == "header":
        active_nav = profile.get("active_nav")
        return render_header(
            fragment,
            active_nav if isinstance(active_nav, str) else None,
            context,
            errors,
        )
    if name == "mobile-cta":
        request_href = profile.get("request_href")
        if not isinstance(request_href, str) or not request_href:
            errors.append(f"{context}: shared shell profile must define request_href")
            return fragment
        request_label = profile.get("request_label", DEFAULT_REQUEST_LABEL)
        if not isinstance(request_label, str) or not request_label.strip():
            errors.append(f"{context}: shared shell profile must define a non-empty request_label")
            return fragment
        return render_mobile_cta(
            fragment,
            request_href,
            request_label.strip(),
            context,
            errors,
        )
    return fragment


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


def validate_page(
    text: str,
    context: str,
    rendered: dict[str, str],
    profile: dict[str, object],
    errors: list[str],
) -> None:
    for name, fragment in rendered.items():
        marker = FRAGMENT_MARKERS[name]
        if text.count(marker) != 1:
            errors.append(f"{context}: expected exactly one {marker}")
        if text.count(fragment) != 1:
            errors.append(f"{context}: shared {name} fragment differs from the rendered profile")

    active_nav = profile.get("active_nav")
    if isinstance(active_nav, str):
        active_marker = f'class="active" aria-current="page" href="{active_nav}"'
        if text.count(active_marker) != 1:
            errors.append(f"{context}: expected one active navigation marker for {active_nav}")

    request_href = profile.get("request_href")
    request_label = profile.get("request_label", DEFAULT_REQUEST_LABEL)
    if (
        "mobile-cta" in rendered
        and isinstance(request_href, str)
        and isinstance(request_label, str)
    ):
        mobile_target = f'<a href="{request_href}">{request_label.strip()}</a>'
        if text.count(mobile_target) != 1:
            errors.append(
                f"{context}: expected shared mobile CTA action {request_label.strip()} -> {request_href}"
            )


def apply_shared_shell(root: Path, destination: Path, errors: list[str]) -> None:
    """Render shared shell fragments into selected generated HTML pages."""
    fragments = load_fragments(root, errors)
    if len(fragments) != len(FRAGMENTS):
        return

    for relative, profile in PAGE_PROFILES.items():
        page = destination / relative
        context = relative.as_posix()
        if not page.is_file():
            errors.append(f"Shared shell page is missing from public build: {context}")
            continue

        components = profile.get("components")
        if not isinstance(components, tuple) or not components:
            errors.append(f"{context}: shared shell profile must define components")
            continue
        if len(set(components)) != len(components):
            errors.append(f"{context}: shared shell profile contains duplicate components")
            continue
        unknown = [name for name in components if name not in FRAGMENTS]
        if unknown:
            errors.append(f"{context}: unknown shared shell components: {', '.join(unknown)}")
            continue

        rendered = {
            name: render_fragment(name, fragments[name], profile, context, errors)
            for name in components
        }

        text = page.read_text(encoding="utf-8")
        for name in components:
            text = replace_fragment(text, name, rendered[name], context, errors)
        validate_page(text, context, rendered, profile, errors)
        page.write_text(text, encoding="utf-8")
