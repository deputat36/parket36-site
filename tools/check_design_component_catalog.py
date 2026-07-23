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
MOBILE_CTA_CSS = ROOT / "design" / "prototypes" / "components-v1-mobile-cta.css"
CHOICE_CHIP_CSS = ROOT / "design" / "prototypes" / "components-v1-choice-chip.css"
BACK_TO_TOP_CSS = ROOT / "design" / "prototypes" / "components-v1-back-to-top.css"
BREADCRUMBS_CSS = ROOT / "design" / "prototypes" / "components-v1-breadcrumbs.css"
PROOF_CARD_CSS = ROOT / "design" / "prototypes" / "components-v1-proof-card.css"
GENERATED_CSS = ROOT / "design" / "generated" / "parket36-tokens.css"
DOC = ROOT / "docs" / "design" / "parket36-components-v1.md"
FIGMA_URL = "https://www.figma.com/design/2ovBluMs8xOKkkUIPevLaH"
TARGET_PAGE = "Foundations + Components — Дизайн-система"

EXPECTED_COMPONENTS = {
    "button": "Button",
    "badge": "Badge",
    "choiceChip": "Choice Chip",
    "backToTop": "Back to Top",
    "breadcrumbs": "Breadcrumbs",
    "proofCard": "Proof Card",
    "problemCard": "Problem Card",
    "serviceCard": "Service Card",
    "faqItem": "FAQ Item",
    "sectionHeader": "Section Header",
    "input": "Input",
    "mobileCta": "Mobile CTA",
}
EXPECTED_STATES = {
    "button": ["default", "hover", "focus", "pressed", "disabled"],
    "choiceChip": ["default", "hover", "focus", "pressed"],
    "backToTop": ["hidden", "visible", "hover", "focus", "pressed"],
    "breadcrumbs": ["default", "hover", "focus"],
    "problemCard": ["default", "hover", "focus"],
    "serviceCard": ["default", "hover", "focus"],
    "faqItem": ["closed", "open", "hover", "focus"],
    "input": ["default", "focus", "filled", "error", "disabled"],
    "mobileCta": ["default", "hover", "focus", "pressed"],
}
EXPECTED_VARIANTS = {
    "button": ["primary", "secondary", "ghost"],
    "choiceChip": ["action"],
    "serviceCard": ["compact", "media"],
}

REQUIRED_HTML = (
    'meta name="robots" content="noindex,nofollow"',
    "data-design-component-catalog",
    'href="../generated/parket36-tokens.css"',
    'href="./components-v1.css"',
    'href="./components-v1-service-card.css"',
    'href="./components-v1-faq-item.css"',
    'href="./components-v1-mobile-cta.css"',
    'href="./components-v1-choice-chip.css"',
    'href="./components-v1-back-to-top.css"',
    'href="./components-v1-breadcrumbs.css"',
    'href="./components-v1-proof-card.css"',
    'src="../logos/parket36-mark-a.svg"',
    "Базовые компоненты нового сайта",
    "Не является опубликованной страницей",
    'id="choice-chips"',
    'id="back-to-top"',
    'id="breadcrumbs"',
    'id="proof-cards"',
    'id="problem-cards"',
    'id="service-cards"',
    'id="faq-items"',
    'id="section-header"',
    'id="inputs"',
    'id="mobile-cta"',
    "non-interactive · article",
    'aria-label="Вернуться к началу страницы"',
    "tel:+79009267929",
)
REQUIRED_BASE_CSS = (
    "var(--p36-color-semantic-action-primary)",
    "var(--p36-color-semantic-action-secondary)",
    "var(--p36-size-touch-min)",
    ":focus-visible",
    "@media(max-width:520px)",
    "@media(prefers-reduced-motion:reduce)",
)
REQUIRED_COMPONENT_CSS = {
    CHOICE_CHIP_CSS: (
        ".choice-chip-row", ".choice-chip {", "min-height: 44px",
        "var(--p36-radius-full)", "var(--p36-shadow-card)",
        ".choice-chip:hover", ".choice-chip:focus-visible", ".choice-chip:active",
        "@media (prefers-reduced-motion: reduce)",
    ),
    BACK_TO_TOP_CSS: (
        ".back-to-top-specimen-row", ".back-to-top-specimen {", "width: 48px",
        "height: 48px", "var(--p36-size-touch-min)", "var(--p36-radius-full)",
        "var(--p36-shadow-floating)", ".back-to-top-specimen.is-hidden",
        ".back-to-top-specimen.is-hover", ".back-to-top-specimen.is-focus",
        ".back-to-top-specimen.is-pressed", "@media (prefers-reduced-motion: reduce)",
    ),
    BREADCRUMBS_CSS: (
        ".breadcrumbs-specimen-row", ".breadcrumbs-specimen {", "flex-wrap: wrap",
        "min-height: 40px", "var(--p36-radius-full)", "var(--p36-radius-md)",
        "var(--p36-shadow-card)", ".breadcrumbs-specimen.is-hover",
        ".breadcrumbs-specimen.is-focus", ".breadcrumbs-specimen__separator",
        ".breadcrumbs-specimen__current", "@media (prefers-reduced-motion: reduce)",
    ),
    PROOF_CARD_CSS: (
        ".proof-card-specimen-grid", ".proof-card-specimen {", "min-height: 156px",
        "width: 48px", "height: 4px", "var(--p36-radius-lg)",
        "var(--p36-shadow-card)", "var(--p36-color-semantic-action-secondary)",
        ".proof-card-specimen--long", "@media (prefers-reduced-motion: reduce)",
    ),
    SERVICE_CARD_CSS: (
        ".service-card-grid", ".service-card--compact", ".service-card--media",
        "min-height: 192px", "aspect-ratio: 1000 / 760", "var(--p36-radius-lg)",
        "var(--p36-shadow-floating)", ".service-card:focus-visible",
        "@media (prefers-reduced-motion: reduce)",
    ),
    FAQ_ITEM_CSS: (
        ".faq-item-grid", ".faq-item[open]", ".faq-item summary",
        ".faq-item summary::after", 'content: "+"', 'content: "−"',
        "min-height: 52px", "var(--p36-radius-lg)", "var(--p36-shadow-floating)",
        ".faq-item summary:focus-visible", "@media (prefers-reduced-motion: reduce)",
    ),
    MOBILE_CTA_CSS: (
        ".mobile-cta-specimen", ".mobile-cta-specimen__action",
        ".mobile-cta-specimen__action--primary", ".mobile-cta-specimen__action--secondary",
        "min-height: 52px", "var(--p36-color-semantic-action-primary)",
        "var(--p36-color-semantic-action-secondary)", "var(--p36-radius-lg)",
        "var(--p36-shadow-floating)", "outline: 3px solid var(--p36-color-primitive-brass-200)",
        "@media (prefers-reduced-motion: reduce)",
    ),
}
FORBIDDEN = (
    "<form", "<script", "supabase", "parket-public-lead", "request-form",
    "data-request-template", "data-request-service", "#6f4628", "#9b683d", "#d7a86e",
)


class CatalogParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h1_count = 0
        self.images_without_alt: list[str] = []
        self.local_assets: list[str] = []
        self.details_count = 0
        self.summary_count = 0
        self.back_to_top_buttons = 0
        self.choice_chip_buttons = 0
        self.breadcrumbs_specimens = 0
        self.proof_card_articles = 0
        self.proof_card_interactive = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "h1":
            self.h1_count += 1
        if tag == "details":
            self.details_count += 1
        if tag == "summary":
            self.summary_count += 1
        if tag == "button" and "back-to-top-specimen" in classes:
            self.back_to_top_buttons += 1
        if tag == "button" and "choice-chip" in classes:
            self.choice_chip_buttons += 1
        if tag == "p" and "breadcrumbs-specimen" in classes:
            self.breadcrumbs_specimens += 1
        if tag == "article" and "proof-card-specimen" in classes:
            self.proof_card_articles += 1
        if tag in {"a", "button"} and "proof-card-specimen" in classes:
            self.proof_card_interactive += 1
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


def require_markers(findings: list[str], text: str, markers: tuple[str, ...], label: str) -> None:
    for marker in markers:
        if marker not in text:
            findings.append(f"{label} is missing marker: {marker}")


def main() -> int:
    findings: list[str] = []
    required_files = (
        CONTRACT, TOKENS, CATALOG, CATALOG_CSS, SERVICE_CARD_CSS, FAQ_ITEM_CSS,
        MOBILE_CTA_CSS, CHOICE_CHIP_CSS, BACK_TO_TOP_CSS, BREADCRUMBS_CSS,
        PROOF_CARD_CSS, GENERATED_CSS, DOC,
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
    if list(components) != list(EXPECTED_COMPONENTS):
        findings.append(f"unexpected ordered component set: {list(components)} != {list(EXPECTED_COMPONENTS)}")

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

    for key, states in EXPECTED_STATES.items():
        if components.get(key, {}).get("properties", {}).get("state") != states:
            findings.append(f"{EXPECTED_COMPONENTS[key]} states do not match the approved contract")
    for key, variants in EXPECTED_VARIANTS.items():
        if components.get(key, {}).get("properties", {}).get("variant") != variants:
            findings.append(f"{EXPECTED_COMPONENTS[key]} variants do not match the approved contract")

    choice_chip = components.get("choiceChip", {})
    if choice_chip.get("accessibility", {}).get("persistentSelectedStateForbidden") is not True:
        findings.append("Choice Chip must forbid persistent selected state")
    back_to_top = components.get("backToTop", {})
    if back_to_top.get("dimensions", {}).get("size") != 48 or back_to_top.get("dimensions", {}).get("visibilityThreshold") != 650:
        findings.append("Back to Top size and visibility threshold must remain 48/650")
    breadcrumbs = components.get("breadcrumbs", {})
    if breadcrumbs.get("dimensions", {}).get("minimumHeight") != 40 or breadcrumbs.get("dimensions", {}).get("mobileRadiusToken") != "radius.md":
        findings.append("Breadcrumbs dimensions differ from the approved contract")
    if breadcrumbs.get("accessibility", {}).get("currentItemNotLinked") is not True:
        findings.append("Breadcrumbs current item must remain non-linked")

    proof_card = components.get("proofCard", {})
    if proof_card.get("properties") != {"title": "text", "description": "text", "interactive": False}:
        findings.append("Proof Card properties must remain non-interactive")
    if proof_card.get("dimensions", {}).get("minimumHeight") != 156:
        findings.append("Proof Card minimumHeight must remain 156")
    proof_accessibility = proof_card.get("accessibility", {})
    for marker in ("nonInteractive", "linksForbidden", "buttonRoleForbidden", "tabindexForbidden", "hoverTransformForbidden"):
        if proof_accessibility.get(marker) is not True:
            findings.append(f"Proof Card must keep accessibility guardrail: {marker}")

    service_card = components.get("serviceCard", {})
    if service_card.get("dimensions", {}).get("mediaAspectRatio") != "1000/760":
        findings.append("Service Card mediaAspectRatio must remain 1000/760")
    faq_item = components.get("faqItem", {})
    if faq_item.get("dimensions", {}).get("minimumTriggerHeight") != 52:
        findings.append("FAQ Item minimumTriggerHeight must remain 52")
    mobile_cta = components.get("mobileCta", {})
    if mobile_cta.get("dimensions", {}).get("breakpoint") != 1000 or mobile_cta.get("dimensions", {}).get("actionHeight") != 52:
        findings.append("Mobile CTA breakpoint/actionHeight must remain 1000/52")

    token_touch_min = get_path(tokens, "size.touchMin.$value.value")
    for key in ("button", "choiceChip", "backToTop", "faqItem", "input", "mobileCta"):
        minimum = components.get(key, {}).get("accessibility", {}).get("minimumTouchTarget")
        if not isinstance(minimum, int) or minimum < token_touch_min:
            findings.append(f"{key} minimumTouchTarget must be at least {token_touch_min}")

    html = CATALOG.read_text(encoding="utf-8")
    css = CATALOG_CSS.read_text(encoding="utf-8")
    component_css = {path: path.read_text(encoding="utf-8") for path in REQUIRED_COMPONENT_CSS}
    combined = "\n".join([html, css, *component_css.values()]).lower()

    require_markers(findings, html, REQUIRED_HTML, "component catalog HTML")
    require_markers(findings, css, REQUIRED_BASE_CSS, "component catalog CSS")
    for path, markers in REQUIRED_COMPONENT_CSS.items():
        require_markers(findings, component_css[path], markers, f"{path.stem} catalog CSS")
    for marker in FORBIDDEN:
        if marker in combined:
            findings.append(f"isolated component catalog contains forbidden marker: {marker}")

    parser = CatalogParser()
    parser.feed(html)
    if parser.h1_count != 1:
        findings.append(f"component catalog must contain exactly one h1, found {parser.h1_count}")
    if parser.details_count != 4 or parser.summary_count != 4:
        findings.append(f"FAQ Item catalog must contain four details/summary pairs, found {parser.details_count}/{parser.summary_count}")
    if parser.choice_chip_buttons != 4:
        findings.append(f"Choice Chip catalog must contain four specimens, found {parser.choice_chip_buttons}")
    if parser.back_to_top_buttons != 5:
        findings.append(f"Back to Top catalog must contain five specimens, found {parser.back_to_top_buttons}")
    if parser.breadcrumbs_specimens != 3:
        findings.append(f"Breadcrumbs catalog must contain three specimens, found {parser.breadcrumbs_specimens}")
    if parser.proof_card_articles != 3:
        findings.append(f"Proof Card catalog must contain three article specimens, found {parser.proof_card_articles}")
    if parser.proof_card_interactive:
        findings.append("Proof Card catalog specimens must not be links or buttons")
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
        FIGMA_URL, TARGET_PAGE, "Choice Chip", "Back to Top", "Breadcrumbs", "Proof Card",
        "Problem Card", "Service Card", "FAQ Item", "Mobile CTA",
        "минимальная зона взаимодействия — 44 px", "650 px",
        "Вернуться к началу страницы", "текущий пункт без ссылки", "BreadcrumbList",
        "неинтерактивный", "hover-смещение",
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
