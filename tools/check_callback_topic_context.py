#!/usr/bin/env python3
"""Validate allowlisted callback topics derived from safe internal context."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CALLBACK_JS = ROOT / "js" / "callback-form.js"
E2E_TEST = ROOT / "tests" / "e2e" / "callback-topic-context.spec.mjs"

JS_MARKERS = {
    "const TOPICS_BY_PATH = Object.freeze({": "allowlisted topic map",
    "'/ceny/'": "price landing topic",
    "'/uslugi/ciklevka-parketa/'": "cycle sanding landing topic",
    "'/uslugi/restavraciya-parketa/'": "restoration landing topic",
    "sessionStorage.getItem(ATTRIBUTION_KEY)": "first-touch storage fallback",
    "referrer.origin === location.origin": "same-origin referrer restriction",
    "source: 'referrer'": "current commercial page priority",
    "source: 'first-touch'": "first-touch fallback",
    "form.dataset.callbackTopic = topic.key": "visible form topic state",
    "form.dataset.callbackTopicSource = topic.source": "visible topic source state",
    "context.id = 'callback-topic-context'": "visible topic explanation",
    "callback_topic: detail.topic": "dataLayer callback topic",
    "callback_topic_source: detail.topicSource": "dataLayer topic source",
    "topic: topic?.key || 'general'": "safe generic fallback",
}

TEST_MARKERS = {
    "прямой вход на контакты сохраняет общую тему": "generic direct-entry scenario",
    "переход со стоимости показывает тему бюджета": "price topic scenario",
    "переход с циклёвки отправляет конкретную задачу Ивану": "service submit scenario",
    "topic: 'general'": "generic topic assertion",
    "callback_topic: 'stoimost'": "price analytics assertion",
    "callback_topic: 'cyclevka'": "service analytics assertion",
    "landing: '/uslugi/ciklevka-parketa/'": "service first-touch assertion",
}


def main() -> int:
    findings: list[str] = []

    if not CALLBACK_JS.is_file():
        findings.append("js/callback-form.js is missing")
        js_text = ""
    else:
        js_text = CALLBACK_JS.read_text(encoding="utf-8")

    if not E2E_TEST.is_file():
        findings.append("tests/e2e/callback-topic-context.spec.mjs is missing")
        test_text = ""
    else:
        test_text = E2E_TEST.read_text(encoding="utf-8")

    for marker, label in JS_MARKERS.items():
        if marker not in js_text:
            findings.append(f"js/callback-form.js: missing {label}: {marker}")

    for marker, label in TEST_MARKERS.items():
        if marker not in test_text:
            findings.append(f"callback topic E2E: missing {label}: {marker}")

    if "params.get('topic')" in js_text or 'params.get("topic")' in js_text:
        findings.append("callback topic must not accept arbitrary URL topic values")

    if findings:
        print("Callback topic findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Callback topic context passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
