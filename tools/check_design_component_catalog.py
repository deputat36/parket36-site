#!/usr/bin/env python3
"""Validate the isolated Parket36 component contract and visual catalog."""

from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "design" / "components" / "parket36-components.json"
TOKENS = ROOT / "design" / "parket36-tokens.json"
CATALOG = ROOT / "design" / "prototypes" / "components-v1.htm"
CATALOG_CSS = ROOT / "design" / "prototypes" / "components-v1.css"
SERVICE_CARD_CSS = ROOT / "design" / "prototypes" / "components-v1-service-card.css"
FAQ_ITEM_CSS = ROOT / "design" / "prototypes" / "components-v1-faq-item.css"
GENERATED_CSS = ROOT / "design" / "generated" / "parket36-tokens.css"
DOC = ROOT / "docs" / "design" / "parket36-components-v1.md"
FIGMA_URL = "https://www.figma.com/design/2ovBluMs8xOKkkUIPevLaH"
TARGET_PAGE = "Foundations + Components — Дизайн-система"

EXPECTED_COMPONENTS = {
    "button": "Button",
    "badge": "Badge",
    "problemCard": "Problem Card",
    "serviceCard": "Service Card",
    "faqItem": "FAQ Item",
    "sectionHeader": "Section Header",
    "input": "Input",
}
EXPECTED_BUTTON_VARIANTS = ["primary", "secondary", "ghost"]
EXPECTED_BUTTON_STATES = ["default", "hover", "focus", "pressed", "disabled"]
EXPECTED_SERVICE_CARD_VARIANTS = ["compact", "media"]
EXPECTED_SERVICE_CARD_STATES = ["default", "hover", "focus"]
EXPECTED_FAQ_ITEM_STATES = ["closed", "open", "hover", "focus"]
EXPECTED_INPUT_STATES = ["default", "focus", "filled", "error", "disabled"]
REQUIRED_HTML = (
    'meta name="robots" content="noindex,nofollow"',
    "data-design-component-catalog",
    'href="../generated/parket36-tokens.css"',
    'href="./components-v1.css"',
    'href="./components-v1-service-card.css"',
    'href="./components-v1-faq-item.css"',
    'src="../logos/parket36-mark-a.svg"',
    "Базовые компоненты нового сайта",
    "Не является опубликованной страницей",
    "Service Card",
    'id="service-cards"',
    "FAQ Item",
    'id="faq-items"',
    '<details class="faq-item"',
    "<summary>",
)
REQUIRED_CSS = (
    "var(--p36-color-semantic-action-primary)",
    "var(--p36-color-semantic-action-secondary)",
    "var(--p36-size-touch-min)",
    ":focus-visible",
    "@media(max-width:520px)",
    "@media(prefers-reduced-motion:reduce)",
)
REQUIRED_SERVICE_CARD_CSS = (
    ".service-card-grid",
    ".service-card--compact",
    ".service-card--media",
    "min-height: 192px",
    "aspect-ratio: 1000 / 760",
    "var(--p36-radius-lg)",
    "var(--p36-shadow-floating)",
    ".service-card:focus-visible",
    "@media (prefers-reduced-motion: reduce)",
)
REQUIRED_FAQ_ITEM_CSS = (
    ".faq-item-grid",
    ".faq-item[open]",
    ".faq-item summary",
    ".faq-item summary::after",
    'content: "+"',
    'content: "−"',
    "min-height: 52px",
    "var(--p36-radius-lg)",
    "var(--p36-shadow-floating)",
    ".faq-item summary:focus-visible",
    "@media (prefers-reduced-motion: reduce)",
)
FORBIDDEN = (
    "<form",
    "<script",
    "supabase",
    "parket-public-lead",
    "request-form",
    "#6f4628",
    "#9b683d",
    "#d7a86e",
)


class CatalogParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h1_count = 0
        self.images_without_alt: list[str] = []
        self.local_assets: list[str] = []
        self.details_count = 0
        self.summary_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if tag == "details":
            self.details_count += 1
        if tag == "summary":
            self.summary_count += 1
        if tag == "img" and "alt" not in values:
            self.images_without_alt.append(values.get("src", "<unknown>") or "<unknown>")
        if tag in {"img", "link"}:
            path = values.get("src") or values.get("href")
            if path and not path.startswith(("http://", "https://", "#", "tel:")):
                self.local_assets.append(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def get_path(data: Any, dotted_path: str) -> Any:
    value = data
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(dotted_path)
        value = value[part]
    return value


def main() -> int:
    findings: list[str] = []
    required_files = (
        CONTRACT,
        TOKENS,
        CATALOG,
        CATALOG_CSS,
        SERVICE_CARD_CSS,
        FAQ_ITEM_CSS,
        GENERATED_CSS,
        DOC,
    )
    for path in required_files:
        if not path.is_file():
            findings.append(f"missing component catalog asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        contract = read_json(CONTRACT)
        tokens = read_json(TOKENS)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Component catalog JSON is invalid: {exc}")
        return 1

    meta = contract.get("meta", {})
    if meta.get("status") != "draft":
        findings.append("component contract must remain draft until Figma QA is complete")
    if meta.get("figmaFile") != FIGMA_URL:
        findings.append("component contract must point to the approved Figma file")
    if meta.get("figmaTargetPage") != TARGET_PAGE:
        findings.append("component contract must use the approved Figma target page")
    if meta.get("tokenSource") != "design/parket36-tokens.json":
        findings.append("component contract must use the approved token source")
    if meta.get("productionImpact") != "none":
        findings.append("component catalog must remain isolated from production")

    components = contract.get("components")
    if not isinstance(components, dict):
        findings.append("component contract must contain a components object")
        components = {}

    if set(components) != set(EXPECTED_COMPONENTS):
        findings.append(
            f"unexpected component set: {sorted(components)} != {sorted(EXPECTED_COMPONENTS)}"
        )

    figma_names: list[str] = []
    for key, expected_name in EXPECTED_COMPONENTS.items():
        component = components.get(key, {})
        if component.get("figmaName") != expected_name:
            findings.append(f"{key}.figmaName must be {expected_name!r}")
        else:
            figma_names.append(expected_name)
        if not component.get("anatomy"):
            findings.append(f"{key} must define anatomy")
        if not component.get("properties"):
            findings.append(f"{key} must define properties")
        radius_token = component.get("dimensions", {}).get("radiusToken")
        if radius_token:
            try:
                target = get_path(tokens, radius_token)
            except KeyError:
                findings.append(f"{key} has unresolved radius token: {radius_token}")
            else:
                if not isinstance(target, dict) or "$value" not in target:
                    findings.append(f"{key} radius token is not a design token: {radius_token}")

    if len(figma_names) != len(set(figma_names)):
        findings.append("Figma component names must be unique")

    button = components.get("button", {})
    if button.get("properties", {}).get("variant") != EXPECTED_BUTTON_VARIANTS:
        findings.append("button variants do not match the approved contract")
    if button.get("properties", {}).get("state") != EXPECTED_BUTTON_STATES:
        findings.append("button states do not match the approved contract")

    service_card = components.get("serviceCard", {})
    if service_card.get("properties", {}).get("variant") != EXPECTED_SERVICE_CARD_VARIANTS:
        findings.append("Service Card variants do not match the approved contract")
    if service_card.get("properties", {}).get("state") != EXPECTED_SERVICE_CARD_STATES:
        findings.append("Service Card states do not match the approved contract")
    if service_card.get("dimensions", {}).get("mediaAspectRatio") != "1000/760":
        findings.append("Service Card mediaAspectRatio must remain 1000/760")

    faq_item = components.get("faqItem", {})
    if faq_item.get("properties", {}).get("state") != EXPECTED_FAQ_ITEM_STATES:
        findings.append("FAQ Item states do not match the approved contract")
    if faq_item.get("dimensions", {}).get("minimumTriggerHeight") != 52:
        findings.append("FAQ Item minimumTriggerHeight must remain 52")
    if faq_item.get("accessibility", {}).get("nativeDetailsRequired") is not True:
        findings.append("FAQ Item must require native details/summary semantics")
    if faq_item.get("accessibility", {}).get("indicatorNotColorOnly") is not True:
        findings.append("FAQ Item indicator must not depend on color alone")

    input_component = components.get("input", {})
    if input_component.get("properties", {}).get("state") != EXPECTED_INPUT_STATES:
        findings.append("input states do not match the approved contract")

    token_touch_min = get_path(tokens, "size.touchMin.$value.value")
    for key in ("button", "faqItem", "input"):
        minimum = components.get(key, {}).get("accessibility", {}).get("minimumTouchTarget")
        if not isinstance(minimum, int) or minimum < token_touch_min:
            findings.append(f"{key} minimumTouchTarget must be at least {token_touch_min}")

    html = CATALOG.read_text(encoding="utf-8")
    css = CATALOG_CSS.read_text(encoding="utf-8")
    service_card_css = SERVICE_CARD_CSS.read_text(encoding="utf-8")
    faq_item_css = FAQ_ITEM_CSS.read_text(encoding="utf-8")
    combined = f"{html}\n{css}\n{service_card_css}\n{faq_item_css}".lower()

    for marker in REQUIRED_HTML:
        if marker not in html:
            findings.append(f"component catalog HTML is missing marker: {marker}")
    for marker in REQUIRED_CSS:
        if marker not in css:
            findings.append(f"component catalog CSS is missing marker: {marker}")
    for marker in REQUIRED_SERVICE_CARD_CSS:
        if marker not in service_card_css:
            findings.append(f"Service Card catalog CSS is missing marker: {marker}")
    for marker in REQUIRED_FAQ_ITEM_CSS:
        if marker not in faq_item_css:
            findings.append(f"FAQ Item catalog CSS is missing marker: {marker}")
    for marker in FORBIDDEN:
        if marker in combined:
            findings.append(f"isolated component catalog contains forbidden marker: {marker}")

    parser = CatalogParser()
    parser.feed(html)
    if parser.h1_count != 1:
        findings.append(f"component catalog must contain exactly one h1, found {parser.h1_count}")
    if parser.details_count != 4 or parser.summary_count != 4:
        findings.append(
            f"FAQ Item catalog must contain four details/summary pairs, found "
            f"{parser.details_count}/{parser.summary_count}"
        )
    for source in parser.images_without_alt:
        findings.append(f"component catalog image is missing alt: {source}")
    for raw_path in parser.local_assets:
        asset = (CATALOG.parent / raw_path).resolve()
        try:
            asset.relative_to(ROOT)
        except ValueError:
            findings.append(f"component catalog asset escapes repository: {raw_path}")
            continue
        if not asset.is_file():
            findings.append(f"component catalog references missing asset: {raw_path}")

    public_design_html = sorted((ROOT / "design" / "prototypes").glob("*.html"))
    if public_design_html:
        findings.append(
            "design prototypes must use .htm to stay out of public HTML scanners: "
            + ", ".join(path.name for path in public_design_html)
        )

    doc = DOC.read_text(encoding="utf-8")
    for marker in (
        FIGMA_URL,
        TARGET_PAGE,
        "Problem Card",
        "Service Card",
        "FAQ Item",
        "минимальная зона взаимодействия — 44 px",
    ):
        if marker not in doc:
            findings.append(f"component documentation is missing marker: {marker}")

    if findings:
        print("Design component catalog findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Design component catalog passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
