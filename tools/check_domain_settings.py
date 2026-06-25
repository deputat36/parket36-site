#!/usr/bin/env python3
"""Validate domain-related shared settings."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit
import sys

from site_settings import load_config

ROOT = Path(__file__).resolve().parents[1]
CNAME_PATH = ROOT / "CNAME"
ROBOTS_PATH = ROOT / "robots.txt"


def main() -> int:
    findings: list[str] = []
    config = load_config()
    domain = str(config["domain"])
    expected_host = urlsplit(domain).netloc

    if not CNAME_PATH.exists():
        findings.append("CNAME file is missing")
    else:
        actual_host = CNAME_PATH.read_text(encoding="utf-8").strip()
        if actual_host != expected_host:
            findings.append(f"CNAME must be {expected_host}, found {actual_host or 'empty'}")

    if not ROBOTS_PATH.exists():
        findings.append("robots.txt is missing")
    else:
        robots_text = ROBOTS_PATH.read_text(encoding="utf-8")
        expected_sitemap = f"Sitemap: {domain}/sitemap.xml"
        if expected_sitemap not in robots_text:
            findings.append(f"robots.txt must contain {expected_sitemap}")

    if findings:
        print("Domain settings findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Domain settings passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
