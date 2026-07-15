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

ADJACENT_SERVICE_PAGES = (
    Path("uslugi/demontazh/index.html"),
    Path("uslugi/elektrika/index.html"),
    Path("uslugi/melkiy-remont/index.html"),
    Path("uslugi/muzh-na-chas/index.html"),
    Path("uslugi/otdelka/index.html"),
    Path("uslugi/pereezdy/index.html"),
    Path("uslugi/santehnika/index.html"),
    Path("uslugi/sborka-mebeli/index.html"),
    Path("uslugi/vyvoz-musora/index.html"),
)

FAMILY_PROFILES = (
    {
        "name": "articles",
        "root": Path("sovety"),
        "glob": "*/index.html",
        "required_og_type": "article",
        "profile": {
            "components": ("header", "mobile-cta"),
            "active_nav": "/sovety/",
            "request_href": "/zayavka/",
        },
    },
    {
        "name": "solutions",
        "root": Path("resheniya"),
        "glob": "*/index.html",
        "required_og_type": "website",
        "profile": {
            "components": ("header", "mobile-cta"),
            "active_nav": None,
            "request_href": "/zayavka/",
        },
    },
    {
        "name": "adjacent-services",
        "root": Path("uslugi"),
        "members": ADJACENT_SERVICE_PAGES,
        "required_og_type": "website",
        "required_robots": "noindex, follow",
        "profile": {
            "components": ("header", "mobile-cta"),
            "active_nav": None,
            "request_href": "/zayavka/",
        },
    },
)

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


def build_meta_re(attribute: str, key: str, value: str) -> re.Pattern[str]:
    """Build a strict matcher for one meta attribute/value pair."""
    return re.compile(
        rf'<meta\b(?=[^>]*\b{re.escape(attribute)}=["\']{re.escape(key)}["\'])'
        rf'(?=[^>]*\bcontent=["\']{re.escape(value)}["\'])[^>]*>',
        re.IGNORECASE,
    )


def validate_family_root(value: object, label: str, errors: list[str]) -> Path | None:
    if not isinstance(value, Path) or not value.parts:
        errors.append(f"{label}: root must be a non-empty relative Path")
        return None
    if value.is_absolute() or ".." in value.parts:
        errors.append(f"{label}: root must stay inside the repository")
        return None
    return value


def declared_family_pages(root: Path, family: dict[str, object], errors: list[str]) -> list[Path]:
    """Resolve either a safe direct-page glob or an exact allowlist."""
    name = family.get("name")
    label = f"{name.strip()} family" if isinstance(name, str) and name.strip() else "shared shell family"
    family_root = validate_family_root(family.get("root"), label, errors)
    if family_root is None:
        return []

    pattern = family.get("glob")
    members = family.get("members")
    if (pattern is None) == (members is None):
        errors.append(f"{label}: define exactly one of glob or members")
        return []

    if pattern is not None:
        if pattern != "*/index.html":
            errors.append(f"{label}: glob must be the safe direct-page pattern */index.html")
            return []
        base = root / family_root
        if not base.is_dir():
            errors.append(f"{label} source directory is missing: {family_root.as_posix()}")
            return []
        pages = sorted(path.relative_to(root) for path in base.glob(pattern) if path.is_file())
        if not pages:
            errors.append(f"{label} has no direct pages matching {family_root.as_posix()}/{pattern}")
            return []
        family_index = family_root / "index.html"
        all_indexes = {path.relative_to(root) for path in base.rglob("index.html") if path.is_file()}
        unsupported = sorted(all_indexes - set(pages) - {family_index})
        if unsupported:
            errors.append(
                f"{label} contains unsupported nested index pages: "
                + ", ".join(path.as_posix() for path in unsupported)
            )
        return pages

    if not isinstance(members, tuple) or not members:
        errors.append(f"{label}: members must be a non-empty tuple of direct index paths")
        return []

    pages: list[Path] = []
    for member in members:
        if not isinstance(member, Path):
            errors.append(f"{label}: every member must be a Path")
            continue
        if member.is_absolute() or ".." in member.parts:
            errors.append(f"{label}: member must stay inside the repository: {member}")
            continue
        if member.name != "index.html" or member.parent.parent != family_root:
            errors.append(f"{label}: member must be a direct page under {family_root.as_posix()}: {member}")
            continue
        pages.append(member)

    if len(set(pages)) != len(pages):
        errors.append(f"{label}: members contain duplicate paths")
    return sorted(set(pages))


def discover_family_profiles(
    root: Path,
    destination: Path,
    family: dict[str, object],
    errors: list[str],
) -> dict[Path, dict[str, object]]:
    """Discover one page family and validate its source/public contract."""
    name = family.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("Shared shell family must define a non-empty name")
        return {}
    label = f"{name.strip()} family"

    family_root = validate_family_root(family.get("root"), label, errors)
    required_og_type = family.get("required_og_type")
    required_robots = family.get("required_robots")
    profile = family.get("profile")
    if family_root is None:
        return {}
    if not isinstance(required_og_type, str) or not required_og_type.strip():
        errors.append(f"{label}: required_og_type must be a non-empty string")
        return {}
    if required_robots is not None and (
        not isinstance(required_robots, str) or not required_robots.strip()
    ):
        errors.append(f"{label}: required_robots must be a non-empty string when defined")
        return {}
    if not isinstance(profile, dict) or not profile:
        errors.append(f"{label}: profile must be a non-empty mapping")
        return {}

    if not (destination / family_root).is_dir():
        errors.append(f"{label} public directory is missing: {family_root.as_posix()}")
        return {}

    source_pages = declared_family_pages(root, family, errors)
    if not source_pages:
        return {}

    missing_source = [path for path in source_pages if not (root / path).is_file()]
    if missing_source:
        errors.append(
            f"{label} source pages are missing: "
            + ", ".join(path.as_posix() for path in missing_source)
        )

    pattern = family.get("glob")
    if isinstance(pattern, str):
        destination_pages = sorted(
            path.relative_to(destination)
            for path in (destination / family_root).glob(pattern)
            if path.is_file()
        )
        source_set = set(source_pages)
        destination_set = set(destination_pages)
        missing_public = sorted(source_set - destination_set)
        extra_public = sorted(destination_set - source_set)
        if missing_public:
            errors.append(
                f"{label} pages are missing from public build: "
                + ", ".join(path.as_posix() for path in missing_public)
            )
        if extra_public:
            errors.append(
                f"{label} public build contains unexpected pages: "
                + ", ".join(path.as_posix() for path in extra_public)
            )
    else:
        missing_public = [path for path in source_pages if not (destination / path).is_file()]
        if missing_public:
            errors.append(
                f"{label} pages are missing from public build: "
                + ", ".join(path.as_posix() for path in missing_public)
            )

    og_type_re = build_meta_re("property", "og:type", required_og_type.strip())
    robots_re = (
        build_meta_re("name", "robots", required_robots.strip())
        if isinstance(required_robots, str)
        else None
    )
    profiles: dict[Path, dict[str, object]] = {}
    for relative in source_pages:
        source_path = root / relative
        if not source_path.is_file():
            continue
        source_text = source_path.read_text(encoding="utf-8")
        if len(og_type_re.findall(source_text)) != 1:
            errors.append(
                f"{relative.as_posix()}: {label} requires exactly one "
                f"og:type={required_og_type.strip()} marker"
            )
            continue
        if robots_re is not None and len(robots_re.findall(source_text)) != 1:
            errors.append(
                f"{relative.as_posix()}: {label} requires exactly one "
                f"robots={required_robots.strip()} marker"
            )
            continue
        profiles[relative] = dict(profile)
    return profiles


def build_page_profiles(
    root: Path,
    destination: Path,
    errors: list[str],
) -> dict[Path, dict[str, object]]:
    """Combine explicit profiles with validated page-family profiles."""
    profiles = {relative: dict(profile) for relative, profile in PAGE_PROFILES.items()}
    seen_names: set[str] = set()
    seen_roots: set[Path] = set()

    for family in FAMILY_PROFILES:
        name = family.get("name")
        family_root = family.get("root")
        normalized_name = name.strip() if isinstance(name, str) else ""
        if normalized_name in seen_names:
            errors.append(f"Duplicate shared shell family name: {normalized_name}")
            continue
        if normalized_name:
            seen_names.add(normalized_name)
        if isinstance(family_root, Path) and family_root in seen_roots:
            errors.append(f"Duplicate shared shell family root: {family_root.as_posix()}")
            continue
        if isinstance(family_root, Path):
            seen_roots.add(family_root)

        family_profiles = discover_family_profiles(root, destination, family, errors)
        overlaps = sorted(set(profiles) & set(family_profiles))
        if overlaps:
            errors.append(
                "Shared shell profile overlap: "
                + ", ".join(path.as_posix() for path in overlaps)
            )
            continue
        profiles.update(family_profiles)
    return profiles


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
                f"{context}: expected shared mobile CTA action "
                f"{request_label.strip()} -> {request_href}"
            )


def apply_shared_shell(root: Path, destination: Path, errors: list[str]) -> None:
    """Render shared shell fragments into selected generated HTML pages."""
    fragments = load_fragments(root, errors)
    if len(fragments) != len(FRAGMENTS):
        return

    profiles = build_page_profiles(root, destination, errors)
    for relative, profile in profiles.items():
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
