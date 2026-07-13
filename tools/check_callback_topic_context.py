#!/usr/bin/env python3
"""Validate allowlisted callback topics derived from safe internal context."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CALLBACK_JS = ROOT / "js" / "callback-form.js"
E2E_TEST = ROOT / "tests" / "e2e" / "callback-topic-context.spec.mjs"
SERVICE_LINK_TEST = ROOT / "tests" / "e2e" / "service-callback-links.spec.mjs"

JS_MARKERS = {
    "const TOPICS_BY_PATH = Object.freeze({": "allowlisted topic map",
    "'/ceny/'": "price landing topic",
    "'/uslugi/'": "service selection hub topic",
    "'/uslugi/parket-i-poly/'": "floor diagnosis hub topic",
    "'/uslugi/ciklevka-parketa/'": "cycle sanding landing topic",
    "'/uslugi/restavraciya-parketa/'": "restoration landing topic",
    "'/sovety/parket-posle-vody/'": "water damage topic",
    "'/sovety/pochemu-skripit-parket/'": "squeak topic",
    "'/sovety/shcheli-v-parkete/'": "gap topic",
    "key: 'podbor-uslugi'": "service selection topic key",
    "key: 'diagnostika'": "diagnosis topic key",
    "key: 'posle-vody'": "water topic key",
    "key: 'skrip'": "squeak topic key",
    "key: 'shcheli'": "gap topic key",
    "sessionStorage.getItem(ATTRIBUTION_KEY)": "first-touch storage fallback",
    "const getEventAttribution = () => {": "early event attribution fallback",
    "source: 'direct'": "direct source fallback",
    "landing: location.pathname": "current-page landing fallback",
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
    "first-touch восстанавливает тему без внутреннего referrer": "first-touch fallback scenario",
    "переход со стоимости показывает тему бюджета": "price topic scenario",
    "переход с циклёвки отправляет конкретную задачу Ивану": "service submit scenario",
    "передаёт тему сервисного хаба": "service hub topic scenarios",
    "диагностика пола отправляет конкретную задачу в payload": "diagnosis submit scenario",
    "'/uslugi/'": "service selection hub scenario",
    "'/uslugi/parket-i-poly/'": "floor diagnosis hub scenario",
    "key: 'podbor-uslugi'": "service selection assertion",
    "key: 'diagnostika'": "diagnosis assertion",
    "'/sovety/parket-posle-vody/'": "water problem scenario",
    "'/sovety/pochemu-skripit-parket/'": "squeak problem scenario",
    "'/sovety/shcheli-v-parkete/'": "gap problem scenario",
    "key: 'posle-vody'": "water topic assertion",
    "key: 'skrip'": "squeak topic assertion",
    "key: 'shcheli'": "gap topic assertion",
    "attribution: { source: 'direct', landing: '/kontakty/' }": "direct attribution assertion",
    "topic: 'general'": "generic topic assertion",
    "topicSource: 'first-touch'": "first-touch source assertion",
    "topicSource: 'referrer'": "referrer source assertion",
    "callback_topic: 'stoimost'": "price analytics assertion",
    "callback_topic: 'cyclevka'": "service analytics assertion",
    "callback_topic_source: 'referrer'": "analytics source assertion",
    "landing: '/uslugi/ciklevka-parketa/'": "service first-touch assertion",
    "landing: '/uslugi/parket-i-poly/'": "diagnosis first-touch assertion",
}

SERVICE_TEST_MARKERS = {
    "'/uslugi/'": "service selection static callback page",
    "'/uslugi/parket-i-poly/'": "floor diagnosis static callback page",
    "'/sovety/parket-posle-vody/'": "water static callback page",
    "'/sovety/pochemu-skripit-parket/'": "squeak static callback page",
    "'/sovety/shcheli-v-parkete/'": "gap static callback page",
    "toHaveCount(2)": "two-link count assertion",
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

    if not SERVICE_LINK_TEST.is_file():
        findings.append("tests/e2e/service-callback-links.spec.mjs is missing")
        service_test_text = ""
    else:
        service_test_text = SERVICE_LINK_TEST.read_text(encoding="utf-8")

    for marker, label in JS_MARKERS.items():
        if marker not in js_text:
            findings.append(f"js/callback-form.js: missing {label}: {marker}")

    for marker, label in TEST_MARKERS.items():
        if marker not in test_text:
            findings.append(f"callback topic E2E: missing {label}: {marker}")

    for marker, label in SERVICE_TEST_MARKERS.items():
        if marker not in service_test_text:
            findings.append(f"service callback E2E: missing {label}: {marker}")

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
