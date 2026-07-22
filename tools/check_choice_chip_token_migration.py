#!/usr/bin/env python3
"""Validate the tokenized Choice Chip contract, production CSS and request templates."""

from __future__ import annotations

import ast
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "design" / "components" / "parket36-components.json"
CSS = ROOT / "css" / "choice-chip-polish.css"
INDEX = ROOT / "index.html"
JS = ROOT / "js" / "main.js"
BUNDLE = ROOT / "tools" / "css_bundle.py"
DOC = ROOT / "docs" / "design" / "parket36-choice-chip-token-migration-v1.md"

EXPECTED_STATES = ["default", "hover", "focus", "pressed"]
EXPECTED_BUTTONS = [
    (
        "Скрипит пол",
        "Паркет или деревянный пол",
        "Скрипит или гуляет деревянный пол. Нужно понять, можно ли закрепить или отремонтировать без полной замены. Приложу общий вид и проблемные места.",
    ),
    (
        "Обновить паркет",
        "Циклёвка / шлифовка / покрытие",
        "Нужно обновить старый паркет: оценить состояние, возможность циклёвки, локального ремонта и покрытия лаком или маслом.",
    ),
    (
        "Щели и дефекты",
        "Реставрация / щели / скрип",
        "Есть щели, повреждённые планки или локальные дефекты паркета. Нужно понять, можно ли восстановить участок без полной замены пола.",
    ),
    (
        "После воды",
        "Пол после воды",
        "Была вода или протечка. Нужно понять, насколько пострадал паркет или деревянный пол и что можно делать до осмотра.",
    ),
    (
        "После арендаторов",
        "Пол после арендаторов",
        "Нужно привести пол в порядок после арендаторов: царапины, пятна, скрип или общее состояние перед новой сдачей.",
    ),
    (
        "Перед продажей",
        "Пол перед продажей или сдачей",
        "Нужно подготовить пол перед продажей или сдачей: привести паркет или деревянный пол в более аккуратный вид и понять срочный минимум.",
    ),
    (
        "Укладка",
        "Укладка паркета или доски",
        "Нужна укладка паркета или доски. Нужно оценить основание, площадь, материал, примыкания, пороги и сроки.",
    ),
    (
        "Плинтусы/пороги",
        "Плинтусы, пороги или примыкания",
        "Нужно оценить плинтусы, пороги или примыкания рядом с паркетом. Хочу понять, можно ли включить это в общую задачу по полу.",
    ),
]
REQUIRED_CSS_MARKERS = (
    "Design system v1: tokenized Choice Chip action buttons",
    ".request-form .pill-row .pill {",
    "min-height: 44px",
    "padding: 10px var(--p36-spacing-lg)",
    "border-radius: var(--p36-radius-full)",
    "var(--p36-color-semantic-surface-default)",
    "var(--p36-color-semantic-text-accent)",
    "var(--p36-shadow-card)",
    ".request-form .pill-row .pill:hover",
    "var(--p36-shadow-floating)",
    ".request-form .pill-row .pill:focus-visible",
    "outline: 3px solid var(--p36-color-primitive-brass-200)",
    ".request-form .pill-row .pill:active",
    "var(--p36-color-semantic-action-primary)",
    "var(--p36-color-semantic-text-inverse)",
    "@media (prefers-reduced-motion: reduce)",
)
FORBIDDEN_CSS_MARKERS = (
    "var(--wood",
    "var(--wood2",
    "var(--gold",
    "var(--line",
    "var(--shadow",
    "rgba(",
    "rgb(",
)
REQUIRED_JS_MARKERS = (
    "document.querySelectorAll('[data-request-template]').forEach(button => {",
    "button.dataset.requestTemplate",
    "button.dataset.requestService",
    "serviceField.value = option.value",
    "taskField.value = taskField.value.trim()",
    "taskField.focus()",
    "emitLead({ type: 'request-template'",
)


class ChoiceChipParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.div_stack: list[bool] = []
        self.in_pill_row = 0
        self.pill_row_count = 0
        self.pill_row_labels: list[str | None] = []
        self.current_button: dict[str, Any] | None = None
        self.buttons: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())

        if tag == "div":
            is_pill_row = "pill-row" in classes
            self.div_stack.append(is_pill_row)
            if is_pill_row:
                self.in_pill_row += 1
                self.pill_row_count += 1
                self.pill_row_labels.append(values.get("aria-label"))

        if tag == "button" and self.in_pill_row and "pill" in classes:
            self.current_button = {"attrs": values, "text": ""}

    def handle_data(self, data: str) -> None:
        if self.current_button is not None:
            self.current_button["text"] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "button" and self.current_button is not None:
            self.current_button["text"] = self.current_button["text"].strip()
            self.buttons.append(self.current_button)
            self.current_button = None

        if tag == "div" and self.div_stack:
            is_pill_row = self.div_stack.pop()
            if is_pill_row:
                self.in_pill_row -= 1


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_css_modules(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if "CSS_MODULES" in names:
            value = ast.literal_eval(node.value)
            if isinstance(value, tuple) and all(isinstance(item, str) for item in value):
                return value
    raise ValueError("CSS_MODULES tuple is missing")


def main() -> int:
    findings: list[str] = []
    for path in (CONTRACT, CSS, INDEX, JS, BUNDLE, DOC):
        if not path.is_file():
            findings.append(f"missing Choice Chip asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        contract = read_json(CONTRACT)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Choice Chip contract JSON is invalid: {exc}")
        return 1

    chip = contract.get("components", {}).get("choiceChip", {})
    if chip.get("figmaName") != "Choice Chip":
        findings.append("choiceChip.figmaName must be 'Choice Chip'")
    if chip.get("anatomy") != ["Container", "Label"]:
        findings.append("Choice Chip anatomy must remain Container + Label")
    properties = chip.get("properties", {})
    if properties.get("variant") != ["action"]:
        findings.append("Choice Chip variant must remain action")
    if properties.get("state") != EXPECTED_STATES:
        findings.append("Choice Chip states must remain default/hover/focus/pressed")
    dimensions = chip.get("dimensions", {})
    if dimensions.get("minimumHeight") != 44:
        findings.append("Choice Chip minimumHeight must remain 44")
    if dimensions.get("horizontalPadding") != 16:
        findings.append("Choice Chip horizontalPadding must remain 16")
    if dimensions.get("gap") != 8:
        findings.append("Choice Chip gap must remain 8")
    if dimensions.get("radiusToken") != "radius.full":
        findings.append("Choice Chip radiusToken must remain radius.full")
    accessibility = chip.get("accessibility", {})
    for key in ("nativeButtonRequired", "focusVisible", "persistentSelectedStateForbidden"):
        if accessibility.get(key) is not True:
            findings.append(f"Choice Chip accessibility flag must be true: {key}")
    if accessibility.get("minimumTouchTarget") != 44:
        findings.append("Choice Chip minimumTouchTarget must remain 44")

    css = CSS.read_text(encoding="utf-8")
    for marker in REQUIRED_CSS_MARKERS:
        if marker not in css:
            findings.append(f"Choice Chip CSS is missing marker: {marker}")
    for marker in FORBIDDEN_CSS_MARKERS:
        if marker in css:
            findings.append(f"Choice Chip CSS contains forbidden legacy/raw marker: {marker}")
    if re.search(r"#[0-9a-fA-F]{3,8}\b", css):
        findings.append("Choice Chip CSS must not contain raw hex colors")
    if "selected" in css.lower() or "aria-pressed" in css.lower():
        findings.append("Choice Chip CSS must not introduce a persistent selected state")

    html = INDEX.read_text(encoding="utf-8")
    if html.count('href="/css/choice-chip-polish.css"') != 1:
        findings.append("index.html must link choice-chip-polish.css exactly once")
    parser = ChoiceChipParser()
    parser.feed(html)
    if parser.pill_row_count != 1:
        findings.append(f"index.html must contain one pill-row, found {parser.pill_row_count}")
    if parser.pill_row_labels != ["Шаблоны ситуации"]:
        findings.append("pill-row must keep the accessible label 'Шаблоны ситуации'")
    if len(parser.buttons) != len(EXPECTED_BUTTONS):
        findings.append(
            f"Choice Chip count must remain {len(EXPECTED_BUTTONS)}, found {len(parser.buttons)}"
        )
    actual_buttons: list[tuple[str, str, str]] = []
    for index, button in enumerate(parser.buttons, start=1):
        attrs = button["attrs"]
        classes = set((attrs.get("class") or "").split())
        if classes != {"pill"}:
            findings.append(f"Choice Chip {index} must keep only the pill class")
        if attrs.get("type") != "button":
            findings.append(f"Choice Chip {index} must remain type=button")
        for forbidden in ("aria-pressed", "aria-selected", "data-selected"):
            if forbidden in attrs:
                findings.append(f"Choice Chip {index} must not use {forbidden}")
        template = attrs.get("data-request-template") or ""
        service = attrs.get("data-request-service") or ""
        actual_buttons.append((button["text"], service, template))
    if actual_buttons != EXPECTED_BUTTONS:
        findings.append("Choice Chip labels, services, templates or order changed")

    js = JS.read_text(encoding="utf-8")
    for marker in REQUIRED_JS_MARKERS:
        if marker not in js:
            findings.append(f"Choice Chip JS integration is missing marker: {marker}")
    start = js.find("document.querySelectorAll('[data-request-template]')")
    end = js.find("form.addEventListener('submit'", start)
    if start < 0 or end < 0:
        findings.append("Choice Chip JS handler block could not be isolated")
    else:
        handler = js[start:end].lower()
        for forbidden in ("aria-pressed", "aria-selected", "is-selected", "selectedchip"):
            if forbidden in handler:
                findings.append(f"Choice Chip JS must not persist selected state: {forbidden}")

    try:
        css_modules = load_css_modules(BUNDLE)
    except (SyntaxError, ValueError) as exc:
        findings.append(str(exc))
        css_modules = ()
    if css_modules.count("choice-chip-polish.css") != 1:
        findings.append("choice-chip-polish.css must appear exactly once in CSS_MODULES")
    elif "cta-polish.css" in css_modules and "logo-brand.css" in css_modules:
        chip_index = css_modules.index("choice-chip-polish.css")
        if not (
            css_modules.index("cta-polish.css") < chip_index < css_modules.index("logo-brand.css")
        ):
            findings.append("choice-chip-polish.css must load after cta-polish and before logo-brand")

    doc = DOC.read_text(encoding="utf-8")
    for marker in (
        "количество действий: 8",
        "постоянные `selected`, `aria-selected` и `aria-pressed` не добавляются",
        "минимальная высота — 44 px",
        "data-request-template",
        "data-request-service",
        "prefers-reduced-motion",
        "nodeId: null",
        "status: pending",
    ):
        if marker.lower() not in doc.lower():
            findings.append(f"Choice Chip documentation is missing marker: {marker}")

    if findings:
        print("Choice Chip token migration findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Choice Chip token migration passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
