#!/usr/bin/env python3
"""Validate the direct measured callback campaign link and browser coverage."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data" / "campaign-links.json"
GENERATOR = ROOT / "tools" / "build_campaign_links.py"
CAMPAIGN_DOC = ROOT / "docs" / "campaign-links.md"
PROFILE_GENERATOR = ROOT / "tools" / "build_local_profile_kit.py"
PROFILE_DOC = ROOT / "docs" / "local-profile-launch-kit.md"
CALLBACK_SCRIPT = ROOT / "js" / "callback-form.js"
E2E = ROOT / "tests" / "e2e" / "direct-callback-campaign.spec.mjs"

EXPECTED_NAME = "VK — обратный звонок"
EXPECTED_FRAGMENT = "callback"
EXPECTED_CONTENT = "callback_post"
EXPECTED_URL = (
    "https://parket36.ru/kontakty/?utm_source=vk&utm_medium=social&"
    "utm_campaign=voronezh_parquet_launch&utm_content=callback_post#callback"
)


def main() -> int:
    findings: list[str] = []

    try:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Direct callback campaign findings: cannot read config: {exc}")
        return 1

    links = payload.get("links") if isinstance(payload, dict) else None
    callback_links = [
        item for item in links or []
        if isinstance(item, dict) and item.get("name") == EXPECTED_NAME
    ]
    if len(callback_links) != 1:
        findings.append(f"campaign config must contain exactly one {EXPECTED_NAME!r} entry")
    else:
        item = callback_links[0]
        expected_fields = {
            "source": "vk",
            "medium": "social",
            "content": EXPECTED_CONTENT,
            "path": "/kontakty/",
            "fragment": EXPECTED_FRAGMENT,
        }
        for field, expected in expected_fields.items():
            if item.get(field) != expected:
                findings.append(f"campaign config {field} must equal {expected!r}")

    required_markers = {
        GENERATOR: {
            "def validate_fragment(": "fragment validator",
            "fragment target does not exist": "missing-anchor failure",
            'fragment = validate_fragment(path, item.get("fragment"), name)': "fragment validation call",
            "?utm_...#callback": "query-before-fragment guidance",
        },
        CAMPAIGN_DOC: {
            EXPECTED_URL: "generated callback URL",
            "`/kontakty/#callback`": "callback landing",
            "## Прямая ссылка на обратный звонок": "callback explanation",
        },
        PROFILE_GENERATOR: {
            '"vk_callback": "VK — обратный звонок"': "required callback link",
            "links['vk_callback']": "VK callback output",
            "Оставьте номер — Иван перезвонит": "clear VK action copy",
        },
        PROFILE_DOC: {
            EXPECTED_URL: "profile-kit callback URL",
            "Прямая callback-ссылка открывает короткую форму сразу": "usage explanation",
        },
        CALLBACK_SCRIPT: {
            "const UTM_KEYS = Object.freeze([": "allowed UTM key list",
            "const readCurrentUrlAttribution = () => {": "early URL attribution fallback",
            "if (!UTM_KEYS.some(key => params.has(key))) return null;": "UTM-only activation",
            "params.get('utm_source')": "UTM source read",
            "params.get('utm_medium')": "UTM medium read",
            "params.get('utm_campaign')": "UTM campaign read",
            "params.get('utm_content')": "UTM content read",
            "params.get('utm_term')": "UTM term read",
            "const currentUrlAttribution = readCurrentUrlAttribution();": "URL fallback usage",
            "if (currentUrlAttribution) return currentUrlAttribution;": "URL fallback priority",
        },
        E2E: {
            "прямая VK-ссылка открывает callback и сохраняет кампанию в заявке": "browser scenario",
            "utm_content=callback_post#callback": "query and fragment order",
            "landing: '/kontakty/'": "first-touch landing assertion",
            "trigger: 'hash-entry'": "automatic callback-open assertion",
            "utm_content: 'callback_post'": "payload attribution assertion",
        },
    }

    for path, markers in required_markers.items():
        if not path.is_file():
            findings.append(f"missing required file: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker, label in markers.items():
            if marker not in text:
                findings.append(f"{path.relative_to(ROOT)}: missing {label}: {marker}")

    if CALLBACK_SCRIPT.is_file():
        callback_text = CALLBACK_SCRIPT.read_text(encoding="utf-8", errors="ignore")
        if "params.get('topic')" in callback_text or 'params.get("topic")' in callback_text:
            findings.append("js/callback-form.js must not accept callback topic from URL parameters")

    if findings:
        print("Direct callback campaign findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Direct callback campaign passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
