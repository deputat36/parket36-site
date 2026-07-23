#!/usr/bin/env python3
"""Build one cache-busted public CSS file from readable source modules."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re
import shutil

from html_accessibility import inject_accessibility_html
from og_cards import apply_og_cards, validate_og_cards
from shared_shell import apply_shared_shell
from site_settings import load_config

CSS_MODULES = (
    "design-tokens.css",
    "style.css",
    "enhancements.css",
    "photo-brief.css",
    "interface-polish.css",
    "mobile-menu.css",
    "typography-polish.css",
    "scroll-progress.css",
    "accessibility-polish.css",
    "cta-polish.css",
    "choice-chip-polish.css",
    "back-to-top-polish.css",
    "breadcrumbs-polish.css",
    "proof-card-polish.css",
    "process-step-polish.css",
    "logo-brand.css",
)
CSS_LINK_RE = re.compile(
    r"[ \t]*<link\b(?=[^>]*\brel=[\"']stylesheet[\"'])"
    r"(?=[^>]*\bhref=[\"']/css/[^\"']+[\"'])[^>]*>[ \t]*\n?",
    re.IGNORECASE,
)
CSS_HREF_RE = re.compile(r"href=[\"'](/css/[^\"']+\.css)[\"']", re.IGNORECASE)

DYNAMIC_CSS_BLOCK = """  const ensureStylesheet = href => {
    if (document.querySelector(`link[href="${href}"]`)) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    document.head.appendChild(link);
  };

  ensureStylesheet('/css/enhancements.css');
  ensureStylesheet('/css/photo-brief.css');
  ensureStylesheet('/css/interface-polish.css');
  ensureStylesheet('/css/mobile-menu.css');
  ensureStylesheet('/css/typography-polish.css');
  ensureStylesheet('/css/scroll-progress.css');
  ensureStylesheet('/css/accessibility-polish.css');
  ensureStylesheet('/css/cta-polish.css');
  ensureStylesheet('/css/logo-brand.css');

"""

BUNDLE_MARKER = 'data-css-bundle="true"'


def build_bundle(root: Path, destination: Path, errors: list[str]) -> str | None:
    """Create the hashed bundle and return its public href."""
    parts: list[str] = []

    for module in CSS_MODULES:
        source = root / "css" / module
        if not source.is_file():
            errors.append(f"CSS source module is missing: css/{module}")
            continue
        text = source.read_text(encoding="utf-8").rstrip()
        parts.append(f"/* source: css/{module} */\n{text}\n")

    if errors:
        return None

    content = "\n".join(parts)
    digest = sha256(content.encode("utf-8")).hexdigest()[:12]
    filename = f"site.{digest}.css"
    css_dir = destination / "css"

    if css_dir.exists():
        shutil.rmtree(css_dir)
    css_dir.mkdir(parents=True)
    (css_dir / filename).write_text(content, encoding="utf-8")

    return f"/css/{filename}"


def rewrite_html(destination: Path, bundle_href: str, errors: list[str]) -> None:
    """Replace source stylesheet links with one hashed bundle link."""
    bundle_link = (
        f'  <link rel="stylesheet" href="{bundle_href}" '
        f'{BUNDLE_MARKER}>\n'
    )

    for html_file in sorted(destination.rglob("*.html")):
        text = html_file.read_text(encoding="utf-8")
        text_without_links, removed = CSS_LINK_RE.subn("", text)
        relative = html_file.relative_to(destination).as_posix()

        if removed == 0:
            errors.append(f"{relative}: no source CSS link found for bundle replacement")
            continue
        if "</head>" not in text_without_links:
            errors.append(f"{relative}: closing head tag is missing")
            continue

        updated = text_without_links.replace("</head>", f"{bundle_link}</head>", 1)
        html_file.write_text(updated, encoding="utf-8")


def remove_dynamic_css_loader(destination: Path, errors: list[str]) -> None:
    """Remove runtime CSS injection from the production JavaScript copy."""
    main_js = destination / "js" / "main.js"
    if not main_js.is_file():
        errors.append("Public js/main.js is missing")
        return

    text = main_js.read_text(encoding="utf-8")
    if DYNAMIC_CSS_BLOCK not in text:
        errors.append("Public js/main.js dynamic CSS block does not match the expected source")
        return

    replacement = "  // Production CSS is bundled by tools/build_pages.py.\n\n"
    main_js.write_text(text.replace(DYNAMIC_CSS_BLOCK, replacement, 1), encoding="utf-8")


def validate_bundle(destination: Path, bundle_href: str, errors: list[str]) -> None:
    """Ensure the public build contains and references exactly one CSS file."""
    css_files = sorted((destination / "css").glob("*.css"))
    expected_name = Path(bundle_href).name

    if [path.name for path in css_files] != [expected_name]:
        found = ", ".join(path.name for path in css_files) or "none"
        errors.append(f"Public CSS directory must contain only {expected_name}; found: {found}")

    for html_file in sorted(destination.rglob("*.html")):
        text = html_file.read_text(encoding="utf-8")
        relative = html_file.relative_to(destination).as_posix()
        css_hrefs = CSS_HREF_RE.findall(text)

        if text.count(BUNDLE_MARKER) != 1:
            errors.append(f"{relative}: expected exactly one CSS bundle marker")
        if css_hrefs != [bundle_href]:
            found = ", ".join(css_hrefs) or "none"
            errors.append(
                f"{relative}: expected only CSS bundle {bundle_href}; found: {found}"
            )

    main_js = destination / "js" / "main.js"
    if main_js.is_file() and "ensureStylesheet('/css/" in main_js.read_text(encoding="utf-8"):
        errors.append("Public js/main.js still injects CSS modules at runtime")


def prepare_css_bundle(root: Path, destination: Path, errors: list[str]) -> str | None:
    """Build and validate public CSS, shared shell, accessibility and OG assets."""
    bundle_href = build_bundle(root, destination, errors)
    if bundle_href is None:
        return None

    rewrite_html(destination, bundle_href, errors)
    apply_shared_shell(root, destination, errors)
    inject_accessibility_html(destination, errors)
    domain = str(load_config()["domain"])
    apply_og_cards(destination, domain, errors)
    validate_og_cards(destination, domain, errors)
    remove_dynamic_css_loader(destination, errors)
    validate_bundle(destination, bundle_href, errors)
    return bundle_href
