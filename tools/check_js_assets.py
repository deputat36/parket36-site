#!/usr/bin/env python3
"""Validate JavaScript fingerprinting integration in the public build."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "tools" / "build_pages.py"
ASSETS = ROOT / "tools" / "js_assets.py"
DOC = ROOT / "docs" / "js-asset-fingerprinting.md"
RUNNER = ROOT / "tools" / "run_quality_checks.py"
QUALITY_CHECKER = ROOT / "tools" / "check_quality_runner.py"

REQUIRED_MARKERS = {
    BUILD: (
        "from js_assets import prepare_js_assets",
        "prepare_js_assets(DEST, errors)",
        "inject_lead_reliability(errors)",
        "validate_public_links(errors)",
    ),
    ASSETS: (
        "HASH_LENGTH = 12",
        "sha256",
        "prepare_js_assets",
        "validate_public_javascript",
        "Source public JavaScript is already fingerprinted",
        "JavaScript fingerprint mismatch",
        "JavaScript reference has no public source",
        "script order changed during fingerprinting",
        "content change did not invalidate JavaScript fingerprint",
        "--self-test",
    ),
    DOC: (
        "Fingerprinting JavaScript",
        "первые 12 символов SHA-256",
        "только внутри `_site`",
        "исходные HTML и JavaScript не изменяются",
        "порядок `defer`-скриптов",
        "tools/js_assets.py --self-test",
        "Browser smoke",
        "Lighthouse CI",
    ),
    RUNNER: (
        '"Validate JavaScript assets", ["tools/check_js_assets.py"]',
    ),
    QUALITY_CHECKER: (
        '["tools/check_js_assets.py"]',
    ),
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def main() -> int:
    findings: list[str] = []
    texts: dict[Path, str] = {}

    for path, markers in REQUIRED_MARKERS.items():
        if not path.is_file():
            findings.append(f"missing required file: {path.relative_to(ROOT)}")
            texts[path] = ""
            continue
        text = read(path)
        texts[path] = text
        for marker in markers:
            if marker not in text:
                findings.append(f"{path.relative_to(ROOT)}: missing marker: {marker}")

    build = texts.get(BUILD, "")
    inject_position = build.find("inject_lead_reliability(errors)")
    fingerprint_position = build.find("prepare_js_assets(DEST, errors)")
    links_position = build.find("validate_public_links(errors)")
    if min(inject_position, fingerprint_position, links_position) < 0 or not (
        inject_position < fingerprint_position < links_position
    ):
        findings.append(
            "JavaScript fingerprinting must run after lead script injection and before public link validation"
        )

    assets = texts.get(ASSETS, "")
    for forbidden in (
        "ROOT / \"js\"",
        "shutil.rmtree(js_dir)",
        "eval(",
        "exec(",
        "subprocess",
        "urllib",
        "requests",
    ):
        if forbidden in assets:
            findings.append(f"tools/js_assets.py contains forbidden implementation marker: {forbidden}")

    if ASSETS.is_file():
        completed = subprocess.run(
            [sys.executable, str(ASSETS), "--self-test"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stdout + completed.stderr).strip() or "unknown self-test error"
            findings.append(f"JavaScript fingerprinting self-test failed: {detail}")

    if findings:
        print("JavaScript asset fingerprinting findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("JavaScript asset fingerprinting guardrail passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
