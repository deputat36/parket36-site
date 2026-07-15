#!/usr/bin/env python3
"""Fingerprint public JavaScript files and rewrite built HTML references."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import shutil
import sys
import tempfile

HASH_LENGTH = 12
HASHED_NAME_RE = re.compile(r"^(?P<stem>.+)\.(?P<hash>[0-9a-f]{12})\.js$")
SCRIPT_SRC_RE = re.compile(
    r"(?P<prefix>\bsrc\s*=\s*['\"])(?P<url>/js/(?P<relative>[^'\"?#]+\.js))(?P<suffix>[^'\"]*['\"])",
    re.IGNORECASE,
)


def content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:HASH_LENGTH]


def fingerprint_name(path: Path) -> str:
    return f"{path.stem}.{content_hash(path)}{path.suffix}"


def validate_hashed_file(path: Path) -> str | None:
    match = HASHED_NAME_RE.fullmatch(path.name)
    if not match:
        return f"JavaScript filename is not fingerprinted: {path.name}"
    actual = content_hash(path)
    expected = match.group("hash")
    if actual != expected:
        return f"JavaScript fingerprint mismatch for {path.name}: expected {actual}"
    return None


def build_mapping(js_dir: Path, errors: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for source in sorted(js_dir.rglob("*.js")):
        relative = source.relative_to(js_dir)
        if HASHED_NAME_RE.fullmatch(source.name):
            errors.append(f"Source public JavaScript is already fingerprinted: {relative.as_posix()}")
            continue
        target = source.with_name(fingerprint_name(source))
        old_url = "/js/" + relative.as_posix()
        new_relative = target.relative_to(js_dir)
        new_url = "/js/" + new_relative.as_posix()
        if target.exists():
            errors.append(f"JavaScript fingerprint target already exists: {new_relative.as_posix()}")
            continue
        mapping[old_url] = new_url
    return mapping


def rewrite_html(html_file: Path, mapping: dict[str, str], errors: list[str]) -> set[str]:
    text = html_file.read_text(encoding="utf-8")
    referenced: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        old_url = match.group("url")
        suffix = match.group("suffix")
        if suffix[:-1]:
            errors.append(
                f"{html_file.as_posix()}: JavaScript reference must not use query or fragment: {old_url}{suffix[:-1]}"
            )
        new_url = mapping.get(old_url)
        if not new_url:
            errors.append(f"{html_file.as_posix()}: JavaScript reference has no public source: {old_url}")
            return match.group(0)
        referenced.add(old_url)
        quote = suffix[-1]
        return f"{match.group('prefix')}{new_url}{quote}"

    rewritten = SCRIPT_SRC_RE.sub(replace, text)
    if rewritten != text:
        html_file.write_text(rewritten, encoding="utf-8")
    return referenced


def validate_public_javascript(destination: Path, errors: list[str]) -> None:
    js_dir = destination / "js"
    if not js_dir.is_dir():
        errors.append("Public JavaScript directory is missing")
        return

    hashed_files = sorted(js_dir.rglob("*.js"))
    if not hashed_files:
        errors.append("Public JavaScript directory contains no scripts")
        return

    for path in hashed_files:
        finding = validate_hashed_file(path)
        if finding:
            errors.append(finding)

    for html_file in sorted(destination.rglob("*.html")):
        text = html_file.read_text(encoding="utf-8")
        for match in SCRIPT_SRC_RE.finditer(text):
            url = match.group("url")
            target = destination / url.lstrip("/")
            if not HASHED_NAME_RE.fullmatch(target.name):
                errors.append(
                    f"{html_file.relative_to(destination).as_posix()}: unversioned JavaScript remains: {url}"
                )
            elif not target.is_file():
                errors.append(
                    f"{html_file.relative_to(destination).as_posix()}: fingerprinted JavaScript is missing: {url}"
                )


def prepare_js_assets(destination: Path, errors: list[str]) -> dict[str, str]:
    """Fingerprint every public JS file and update built HTML script references."""
    js_dir = destination / "js"
    if not js_dir.is_dir():
        errors.append("Public JavaScript directory is missing")
        return {}

    mapping = build_mapping(js_dir, errors)
    if errors:
        return mapping

    referenced: set[str] = set()
    for html_file in sorted(destination.rglob("*.html")):
        referenced.update(rewrite_html(html_file, mapping, errors))

    if errors:
        return mapping

    for old_url, new_url in mapping.items():
        source = destination / old_url.lstrip("/")
        target = destination / new_url.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)

    validate_public_javascript(destination, errors)
    if not errors:
        print(f"Fingerprinting prepared {len(mapping)} JavaScript files; {len(referenced)} are referenced by HTML")
    return mapping


def self_test() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="parket36-js-assets-") as temp:
        root = Path(temp)
        destination = root / "_site"
        js_dir = destination / "js"
        nested_dir = js_dir / "forms"
        nested_dir.mkdir(parents=True)
        (js_dir / "main.js").write_text("console.log('main');\n", encoding="utf-8")
        (nested_dir / "callback.js").write_text("console.log('callback');\n", encoding="utf-8")
        html = destination / "index.html"
        html.write_text(
            "\n".join(
                [
                    '<script src="/js/main.js" defer></script>',
                    "<script defer src='/js/forms/callback.js'></script>",
                ]
            ),
            encoding="utf-8",
        )

        errors: list[str] = []
        mapping = prepare_js_assets(destination, errors)
        if errors:
            failures.extend(errors)
        if set(mapping) != {"/js/main.js", "/js/forms/callback.js"}:
            failures.append(f"unexpected mapping keys: {sorted(mapping)}")
        rewritten = html.read_text(encoding="utf-8")
        if "/js/main.js" in rewritten or "/js/forms/callback.js" in rewritten:
            failures.append("unversioned JavaScript URL remained in HTML")
        if rewritten.find("main.") > rewritten.find("callback."):
            failures.append("script order changed during fingerprinting")
        if (js_dir / "main.js").exists() or (nested_dir / "callback.js").exists():
            failures.append("original JavaScript file remained after fingerprinting")
        for url in mapping.values():
            target = destination / url.lstrip("/")
            if not target.is_file():
                failures.append(f"fingerprinted file is missing: {url}")
            else:
                finding = validate_hashed_file(target)
                if finding:
                    failures.append(finding)

        first_main_url = mapping.get("/js/main.js", "")
        second_destination = root / "_site-second"
        shutil.copytree(destination, second_destination)
        second_js = second_destination / first_main_url.lstrip("/")
        if second_js.exists():
            second_js.write_text("console.log('changed');\n", encoding="utf-8")
            if validate_hashed_file(second_js) is None:
                failures.append("content change did not invalidate JavaScript fingerprint")

    with tempfile.TemporaryDirectory(prefix="parket36-js-assets-missing-") as temp:
        destination = Path(temp) / "_site"
        (destination / "js").mkdir(parents=True)
        (destination / "js" / "main.js").write_text("console.log('main');\n", encoding="utf-8")
        (destination / "index.html").write_text(
            '<script src="/js/missing.js" defer></script>',
            encoding="utf-8",
        )
        errors = []
        prepare_js_assets(destination, errors)
        if not any("has no public source" in error for error in errors):
            failures.append("missing JavaScript reference was not rejected")

    if failures:
        print("JavaScript asset fingerprinting self-test failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("JavaScript asset fingerprinting self-test passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    parser.error("Use --self-test; build integration calls prepare_js_assets() directly")
    return 2


if __name__ == "__main__":
    sys.exit(main())
