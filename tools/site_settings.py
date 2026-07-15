#!/usr/bin/env python3
"""Check or update shared Parket36 contact, endpoint and analytics settings.

Usage:
    python tools/site_settings.py --check
    python tools/site_settings.py --write
    python tools/site_settings.py --self-test

The script intentionally touches only predictable shared values: phone links,
display phone, approved MAX links, current-year fallbacks, the public lead
endpoint and the optional Yandex Metrika snippet generated from data/site.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "data" / "site.json"
MAIN_JS_PATH = ROOT / "js" / "main.js"
LEAD_ENDPOINT_DOCS = (
    ROOT / "docs" / "supabase-parket-leads.md",
    ROOT / "docs" / "lead-endpoint-test-mode.md",
)
SHARED_FRAGMENT_DIR = Path("data/shared-shell")
IGNORED_DIRS = {".git", ".github", "tools", "node_modules", "_site"}

TEL_RE = re.compile(r"tel:\+7\d{10}")
DISPLAY_PHONE_RE = re.compile(r"8\s*\(\d{3}\)\s*\d{3}[\-– ]\d{2}[\-– ]\d{2}")
CURRENT_YEAR_RE = re.compile(
    r'(<span\b[^>]*\bdata-current-year\b[^>]*>)\d{4}(</span>)',
    re.IGNORECASE,
)
MAX_HREF_RE = re.compile(r'href="https://max\.ru[^\"]*"')
METRIKA_BLOCK_RE = re.compile(
    r"\n?\s*<!-- Parket36 Metrika start -->.*?<!-- Parket36 Metrika end -->\n?",
    re.DOTALL,
)
LEAD_ENDPOINT_RE = re.compile(
    r"https://[a-z0-9-]+\.supabase\.co/functions/v1/parket-public-lead"
)
LEAD_ENDPOINT_CONST_RE = re.compile(
    r"const\s+PARKET_LEAD_ENDPOINT\s*=\s*['\"][^'\"]+['\"]\s*;"
)


def iter_markup_files(root: Path = ROOT) -> list[Path]:
    """Return source HTML plus canonical shared-shell fragments."""
    result: set[Path] = set()

    for path in root.rglob("*.html"):
        rel_parts = path.relative_to(root).parts
        if any(part in IGNORED_DIRS for part in rel_parts):
            continue
        result.add(path)

    fragment_dir = root / SHARED_FRAGMENT_DIR
    if fragment_dir.is_dir():
        result.update(fragment_dir.glob("*.htmlfrag"))

    return sorted(result)


def shared_endpoint_files() -> tuple[Path, ...]:
    return (MAIN_JS_PATH, *LEAD_ENDPOINT_DOCS)


def load_config() -> dict[str, object]:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    required = {
        "phone_display",
        "phone_e164",
        "domain",
        "lead_endpoint",
        "max_url",
        "metrika_id",
        "default_request_path",
        "current_year",
    }
    missing = sorted(required - data.keys())
    if missing:
        raise ValueError(f"Missing settings: {', '.join(missing)}")

    phone_display = str(data["phone_display"]).strip()
    if not phone_display:
        raise ValueError("phone_display must not be empty")
    data["phone_display"] = phone_display

    phone_e164 = str(data["phone_e164"])
    if not re.fullmatch(r"\+7\d{10}", phone_e164):
        raise ValueError("phone_e164 must have the format +7XXXXXXXXXX")

    domain = str(data["domain"]).rstrip("/")
    if not re.fullmatch(r"https://[a-z0-9.-]+", domain):
        raise ValueError("domain must use https and must not contain a trailing slash")
    data["domain"] = domain

    lead_endpoint = str(data["lead_endpoint"]).strip()
    if not LEAD_ENDPOINT_RE.fullmatch(lead_endpoint):
        raise ValueError(
            "lead_endpoint must use an HTTPS Supabase functions URL ending in "
            "/functions/v1/parket-public-lead"
        )
    data["lead_endpoint"] = lead_endpoint

    max_url = str(data.get("max_url", "")).strip()
    if max_url and not re.fullmatch(r"https://max\.ru/[^\s\"'<>]+", max_url):
        raise ValueError("max_url must be empty or use https://max.ru/...")
    data["max_url"] = max_url

    metrika_id = str(data.get("metrika_id", "")).strip()
    if metrika_id and not re.fullmatch(r"\d{5,12}", metrika_id):
        raise ValueError("metrika_id must be empty or contain 5-12 digits")
    data["metrika_id"] = metrika_id

    default_request_path = str(data["default_request_path"]).strip()
    if not re.fullmatch(r"/[a-z0-9\-/]+/", default_request_path):
        raise ValueError("default_request_path must look like /zayavka/")
    data["default_request_path"] = default_request_path

    current_year = data["current_year"]
    if isinstance(current_year, bool) or not isinstance(current_year, int):
        raise ValueError("current_year must be an integer")
    if not 2000 <= current_year <= 2100:
        raise ValueError("current_year must be between 2000 and 2100")

    return data


def render_metrika_block(counter_id: str) -> str:
    return f"""
  <!-- Parket36 Metrika start -->
  <script>
    window.parket36MetrikaId = {counter_id};
    (function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)}})(window, document, 'script', 'https://mc.yandex.ru/metrika/tag.js', 'ym');
    ym({counter_id}, 'init', {{ clickmap: true, trackLinks: true, accurateTrackBounce: true }});
  </script>
  <noscript><div><img src="https://mc.yandex.ru/watch/{counter_id}" style="position:absolute; left:-9999px;" alt=""></div></noscript>
  <!-- Parket36 Metrika end -->"""


def update_markup_text(text: str, config: dict[str, object]) -> str:
    phone_e164 = str(config["phone_e164"])
    phone_display = str(config["phone_display"])
    current_year = str(config["current_year"])
    max_url = str(config.get("max_url", "")).strip()
    metrika_id = str(config.get("metrika_id", "")).strip()

    text = TEL_RE.sub(f"tel:{phone_e164}", text)
    text = DISPLAY_PHONE_RE.sub(phone_display, text)
    text = CURRENT_YEAR_RE.sub(rf"\g<1>{current_year}\g<2>", text)

    if max_url:
        text = MAX_HREF_RE.sub(f'href="{max_url}"', text)

    text = METRIKA_BLOCK_RE.sub("\n", text)
    if metrika_id and "</head>" in text:
        text = text.replace("</head>", f"{render_metrika_block(metrika_id)}\n</head>", 1)

    return text


def update_endpoint_text(path: Path, text: str, config: dict[str, object]) -> str:
    endpoint = str(config["lead_endpoint"])
    if path == MAIN_JS_PATH:
        if not LEAD_ENDPOINT_CONST_RE.search(text):
            raise ValueError("js/main.js is missing the PARKET_LEAD_ENDPOINT constant")
        return LEAD_ENDPOINT_CONST_RE.sub(
            f"const PARKET_LEAD_ENDPOINT = '{endpoint}';",
            text,
            count=1,
        )

    if not LEAD_ENDPOINT_RE.search(text):
        raise ValueError(f"{path.relative_to(ROOT)} is missing the public lead endpoint URL")
    return LEAD_ENDPOINT_RE.sub(endpoint, text)


def run_self_test(verbose: bool = True) -> int:
    """Exercise markup discovery and deterministic shared-value rewriting."""
    findings: list[str] = []
    config: dict[str, object] = {
        "phone_display": "8 (900) 926-79-29",
        "phone_e164": "+79009267929",
        "current_year": 2026,
        "max_url": "https://max.ru/ivan-parket",
        "metrika_id": "12345678",
    }

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        fragment_dir = root / SHARED_FRAGMENT_DIR
        fragment_dir.mkdir(parents=True)
        ignored_dir = root / "tools"
        ignored_dir.mkdir()

        (root / "index.html").write_text("<html><head></head><body></body></html>", encoding="utf-8")
        (fragment_dir / "header.htmlfrag").write_text("<header></header>", encoding="utf-8")
        (ignored_dir / "ignored.html").write_text("<html></html>", encoding="utf-8")

        discovered = {path.relative_to(root).as_posix() for path in iter_markup_files(root)}
        expected = {"index.html", "data/shared-shell/header.htmlfrag"}
        if discovered != expected:
            findings.append(
                "markup discovery must include source HTML and shared-shell fragments only; "
                f"found: {sorted(discovered)}"
            )

    stale_html = (
        '<html><head></head><body><a href="tel:+79999999999">8 (999) 999-99-99</a>'
        '<a href="https://max.ru/old">MAX</a><span data-current-year>2025</span></body></html>'
    )
    updated_html = update_markup_text(stale_html, config)
    expected_html_markers = (
        'href="tel:+79009267929"',
        "8 (900) 926-79-29",
        'href="https://max.ru/ivan-parket"',
        '<span data-current-year>2026</span>',
        "window.parket36MetrikaId = 12345678;",
    )
    for marker in expected_html_markers:
        if marker not in updated_html:
            findings.append(f"markup rewrite is missing expected marker: {marker}")
    if updated_html.count("<!-- Parket36 Metrika start -->") != 1:
        findings.append("markup rewrite must add exactly one Metrika block")
    if update_markup_text(updated_html, config) != updated_html:
        findings.append("markup rewrite must be idempotent")

    stale_fragment = (
        '<!-- shared-shell:footer --><footer><a href="tel:+79999999999">'
        '8 (999) 999-99-99</a><span data-current-year>2025</span></footer>'
    )
    updated_fragment = update_markup_text(stale_fragment, config)
    if 'href="tel:+79009267929"' not in updated_fragment:
        findings.append("shared-shell fragment phone link was not synchronized")
    if "8 (900) 926-79-29" not in updated_fragment:
        findings.append("shared-shell fragment display phone was not synchronized")
    if '<span data-current-year>2026</span>' not in updated_fragment:
        findings.append("shared-shell fragment current-year fallback was not synchronized")
    if "Parket36 Metrika start" in updated_fragment:
        findings.append("shared-shell fragments must not receive a Metrika block")

    if findings:
        print("Shared settings self-test findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    if verbose:
        print("Shared settings self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()
    if args.check and run_self_test(verbose=False) != 0:
        return 1

    try:
        config = load_config()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Configuration error: {exc}")
        return 1

    missing_shared = [path.relative_to(ROOT).as_posix() for path in shared_endpoint_files() if not path.is_file()]
    if missing_shared:
        print("Configuration error: missing shared files: " + ", ".join(missing_shared))
        return 1

    changed: list[str] = []
    try:
        for path in iter_markup_files():
            original = path.read_text(encoding="utf-8")
            updated = update_markup_text(original, config)
            if original == updated:
                continue
            rel = path.relative_to(ROOT).as_posix()
            changed.append(rel)
            if args.write:
                path.write_text(updated, encoding="utf-8")

        for path in shared_endpoint_files():
            original = path.read_text(encoding="utf-8")
            updated = update_endpoint_text(path, original, config)
            if original == updated:
                continue
            rel = path.relative_to(ROOT).as_posix()
            changed.append(rel)
            if args.write:
                path.write_text(updated, encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"Configuration error: {exc}")
        return 1

    if args.check and changed:
        print("Shared settings are not synchronized:")
        for rel in changed:
            print(f"  - {rel}")
        print("Run: python tools/site_settings.py --write")
        return 1

    if args.write:
        if changed:
            print(f"Updated {len(changed)} files")
            for rel in changed:
                print(f"  - {rel}")
        else:
            print("Shared settings are already synchronized")
    else:
        print("Shared settings check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
