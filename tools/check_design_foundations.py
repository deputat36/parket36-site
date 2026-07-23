#!/usr/bin/env python3
"""Validate Parket36 foundations, visual catalog and Figma sync manifest."""

from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / "design" / "parket36-tokens.json"
FOUNDATIONS = ROOT / "design" / "foundations" / "parket36-foundations.json"
MANIFEST = ROOT / "design" / "figma" / "parket36-sync-manifest.json"
COMPONENTS = ROOT / "design" / "components" / "parket36-components.json"
CATALOG = ROOT / "design" / "prototypes" / "foundations-v1.htm"
CATALOG_CSS = ROOT / "design" / "prototypes" / "foundations-v1.css"
GENERATED_CSS = ROOT / "design" / "generated" / "parket36-tokens.css"
DOC = ROOT / "docs" / "design" / "parket36-foundations-v1.md"
GAP_DOC = ROOT / "docs" / "design" / "parket36-figma-gap-analysis-v1.md"

FIGMA_FILE_KEY = "2ovBluMs8xOKkkUIPevLaH"
FIGMA_URL = f"https://www.figma.com/design/{FIGMA_FILE_KEY}"
TARGET_PAGE = "Foundations + Components — Дизайн-система"
EXPECTED_PAGES = {
    "cover": ("Cover + Brand — Паркет36", "0:1"),
    "foundationsAndComponents": (TARGET_PAGE, "2:4"),
    "screens": ("Screens — Desktop и Mobile сайт", "2:5"),
}
EXPECTED_COLLECTIONS = {
    "primitives": ("P36 / Primitives", "5:2", 20),
    "semantic": ("P36 / Semantic", "5:23", 22),
    "dimensions": ("P36 / Dimensions", "5:46", 20),
}
EXPECTED_TEXT_STYLES = [
    "Type/Display",
    "Type/H1",
    "Type/H2",
    "Type/H3",
    "Type/Lead",
    "Type/Body",
    "Type/Body Strong",
    "Type/Small",
    "Type/Eyebrow",
]
EXPECTED_EFFECT_STYLES = ["Effect/Card", "Effect/Floating"]
EXPECTED_COMPONENTS = [
    "Button",
    "Badge",
    "Choice Chip",
    "Back to Top",
    "Breadcrumbs",
    "Proof Card",
    "Problem Card",
    "Service Card",
    "FAQ Item",
    "Section Header",
    "Input",
    "Mobile CTA",
]
REQUIRED_SECTIONS = ["colors", "typography", "spacing", "shape-and-depth", "layout"]
REQUIRED_CSS = [
    "var(--p36-color-semantic-action-primary)",
    "var(--p36-font-size-display)",
    "var(--p36-spacing-5xl)",
    "var(--p36-radius-full)",
    "var(--p36-shadow-floating)",
    "@media (max-width: 520px)",
    "@media (prefers-reduced-motion: reduce)",
]
FORBIDDEN = [
    "<form",
    "<script",
    "supabase",
    "parket-public-lead",
    "request-form",
    "#6f4628",
    "#9b683d",
    "#d7a86e",
]


class CatalogParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h1_count = 0
        self.section_ids: set[str] = set()
        self.images_without_alt: list[str] = []
        self.local_assets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if tag == "section" and values.get("id"):
            self.section_ids.add(values["id"] or "")
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


def validate_token_reference(
    findings: list[str], tokens: dict[str, Any], reference: str, context: str
) -> None:
    try:
        value = get_path(tokens, reference)
    except KeyError:
        findings.append(f"{context} has unresolved token reference: {reference}")
        return
    if not isinstance(value, dict):
        findings.append(f"{context} token reference is not an object: {reference}")


def main() -> int:
    findings: list[str] = []
    required_files = (
        TOKENS,
        FOUNDATIONS,
        MANIFEST,
        COMPONENTS,
        CATALOG,
        CATALOG_CSS,
        GENERATED_CSS,
        DOC,
        GAP_DOC,
    )
    for path in required_files:
        if not path.is_file():
            findings.append(f"missing design foundations asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        tokens = read_json(TOKENS)
        foundations = read_json(FOUNDATIONS)
        manifest = read_json(MANIFEST)
        components = read_json(COMPONENTS)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Design foundations JSON is invalid: {exc}")
        return 1

    meta = foundations.get("meta", {})
    if meta.get("status") != "draft":
        findings.append("foundations contract must remain draft until Figma QA is complete")
    if meta.get("figmaFile") != FIGMA_URL:
        findings.append("foundations contract must point to the approved Figma file")
    if meta.get("figmaTargetPage") != TARGET_PAGE:
        findings.append("foundations contract must use the approved Figma target page")
    if meta.get("tokenSource") != "design/parket36-tokens.json":
        findings.append("foundations contract must use the approved token source")
    if meta.get("productionImpact") != "none":
        findings.append("foundations catalog must remain isolated from production")

    for group in foundations.get("colors", {}).get("primitiveGroups", []):
        validate_token_reference(findings, tokens, group, "primitive color group")
    for group in foundations.get("colors", {}).get("semanticGroups", []):
        validate_token_reference(findings, tokens, group, "semantic color group")

    text_styles = foundations.get("typography", {}).get("styles", [])
    style_names = [style.get("figmaName") for style in text_styles]
    if style_names != EXPECTED_TEXT_STYLES:
        findings.append("typography styles do not match the approved ordered style list")
    if len(style_names) != len(set(style_names)):
        findings.append("typography style names must be unique")
    for style in text_styles:
        name = style.get("figmaName", "<unnamed>")
        for key in ("familyToken", "weightToken", "sizeToken"):
            reference = style.get(key)
            if not isinstance(reference, str):
                findings.append(f"{name} is missing {key}")
            else:
                validate_token_reference(findings, tokens, reference, name)
        if not isinstance(style.get("lineHeight"), int) or style["lineHeight"] <= 0:
            findings.append(f"{name} must define a positive integer lineHeight")

    for section, token_refs in (
        ("spacing", foundations.get("spacing", {}).get("tokens", [])),
        ("radii", foundations.get("radii", {}).get("tokens", [])),
        ("layout", foundations.get("layout", {}).get("tokens", [])),
    ):
        for reference in token_refs:
            validate_token_reference(findings, tokens, reference, section)

    effect_styles = foundations.get("effects", {}).get("styles", [])
    effect_names = [style.get("figmaName") for style in effect_styles]
    if effect_names != EXPECTED_EFFECT_STYLES:
        findings.append("effect styles do not match the approved ordered style list")
    for style in effect_styles:
        reference = style.get("token")
        if isinstance(reference, str):
            validate_token_reference(findings, tokens, reference, style.get("figmaName", "effect"))
        else:
            findings.append("effect style is missing token reference")

    manifest_meta = manifest.get("meta", {})
    if manifest_meta.get("fileKey") != FIGMA_FILE_KEY:
        findings.append("Figma sync manifest has an unexpected file key")
    if manifest_meta.get("status") != "partial-unverified":
        findings.append("Figma sync manifest must remain partial-unverified while MCP is blocked")
    if manifest_meta.get("verificationBlocked") is not True:
        findings.append("Figma sync manifest must record the active verification blocker")
    if manifest_meta.get("productionImpact") != "none":
        findings.append("Figma sync manifest must not declare production impact")

    pages = manifest.get("pages", {})
    for key, (expected_name, expected_id) in EXPECTED_PAGES.items():
        page = pages.get(key, {})
        if page.get("name") != expected_name or page.get("nodeId") != expected_id:
            findings.append(f"Figma page mapping is incorrect: {key}")
        if page.get("status") != "known-from-prior-session":
            findings.append(f"Figma page must remain unverified until MCP audit: {key}")

    collections = manifest.get("variableCollections", {})
    known_total = 0
    for key, (expected_name, expected_id, expected_count) in EXPECTED_COLLECTIONS.items():
        collection = collections.get(key, {})
        if collection.get("name") != expected_name:
            findings.append(f"Figma collection name is incorrect: {key}")
        if collection.get("collectionId") != expected_id:
            findings.append(f"Figma collection ID is incorrect: {key}")
        if collection.get("knownVariableCount") != expected_count:
            findings.append(f"Figma collection count is incorrect: {key}")
        known_total += collection.get("knownVariableCount", 0)
    if known_total != 62:
        findings.append(f"known Figma variable count must be 62, found {known_total}")

    manifest_text = manifest.get("styles", {}).get("text", {})
    if manifest_text.get("expected") != EXPECTED_TEXT_STYLES:
        findings.append("manifest text style list differs from foundations contract")
    if manifest_text.get("status") != "pending" or manifest_text.get("nodeIds") != {}:
        findings.append("manifest text styles must remain pending with empty node IDs")
    manifest_effects = manifest.get("styles", {}).get("effects", {})
    if manifest_effects.get("expected") != EXPECTED_EFFECT_STYLES:
        findings.append("manifest effect style list differs from foundations contract")
    if manifest_effects.get("status") != "pending" or manifest_effects.get("nodeIds") != {}:
        findings.append("manifest effect styles must remain pending with empty node IDs")

    contract_names = [item.get("figmaName") for item in components.get("components", {}).values()]
    if contract_names != EXPECTED_COMPONENTS:
        findings.append("component contract names differ from approved v1 scope")
    manifest_components = manifest.get("components", {})
    if list(manifest_components) != EXPECTED_COMPONENTS:
        findings.append("manifest component names differ from component contract")
    for name, state in manifest_components.items():
        if state.get("nodeId") is not None or state.get("status") != "pending":
            findings.append(f"component must remain pending until Figma creation: {name}")

    html = CATALOG.read_text(encoding="utf-8")
    css = CATALOG_CSS.read_text(encoding="utf-8")
    combined = f"{html}\n{css}".lower()
    required_html = [
        'meta name="robots" content="noindex,nofollow"',
        "data-design-foundations-catalog",
        'href="../generated/parket36-tokens.css"',
        'href="./foundations-v1.css"',
        'src="../logos/parket36-mark-a.svg"',
        "Foundations нового сайта",
        "Не является опубликованной страницей сайта",
    ]
    for marker in required_html:
        if marker not in html:
            findings.append(f"foundations HTML is missing marker: {marker}")
    for marker in REQUIRED_CSS:
        if marker not in css:
            findings.append(f"foundations CSS is missing marker: {marker}")
    for marker in FORBIDDEN:
        if marker in combined:
            findings.append(f"isolated foundations catalog contains forbidden marker: {marker}")

    parser = CatalogParser()
    parser.feed(html)
    if parser.h1_count != 1:
        findings.append(f"foundations catalog must contain exactly one h1, found {parser.h1_count}")
    for section_id in REQUIRED_SECTIONS:
        if section_id not in parser.section_ids:
            findings.append(f"foundations catalog is missing section: {section_id}")
    for source in parser.images_without_alt:
        findings.append(f"foundations catalog image is missing alt: {source}")
    for raw_path in parser.local_assets:
        asset = (CATALOG.parent / raw_path).resolve()
        try:
            asset.relative_to(ROOT)
        except ValueError:
            findings.append(f"foundations catalog asset escapes repository: {raw_path}")
            continue
        if not asset.is_file():
            findings.append(f"foundations catalog references missing asset: {raw_path}")

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
        "Минимальная зона взаимодействия — 44 px",
        "не создавать новые страницы",
        "девять text styles",
    ):
        if marker.lower() not in doc.lower():
            findings.append(f"foundations documentation is missing marker: {marker}")

    gap_doc = GAP_DOC.read_text(encoding="utf-8")
    for marker in (
        "21 июля 2026 года",
        "known-from-prior-session",
        "62 переменных",
        "лимит вызовов Figma MCP",
        "не создавать новые страницы",
    ):
        if marker.lower() not in gap_doc.lower():
            findings.append(f"Figma gap analysis is missing marker: {marker}")

    if findings:
        print("Design foundations findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Design foundations and Figma sync manifest passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
