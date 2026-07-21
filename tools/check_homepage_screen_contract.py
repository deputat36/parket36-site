#!/usr/bin/env python3
"""Validate the Parket36 homepage screen contract and prototype alignment."""

from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "design" / "screens" / "homepage-v1.json"
TOKENS = ROOT / "design" / "parket36-tokens.json"
FOUNDATIONS = ROOT / "design" / "foundations" / "parket36-foundations.json"
COMPONENTS = ROOT / "design" / "components" / "parket36-components.json"
MANIFEST = ROOT / "design" / "figma" / "parket36-sync-manifest.json"
PROTOTYPE = ROOT / "design" / "prototypes" / "homepage-v1.htm"
BASE_CSS = ROOT / "design" / "prototypes" / "homepage-v1-base.css"
CONTENT_CSS = ROOT / "design" / "prototypes" / "homepage-v1-content.css"
RESPONSIVE_CSS = ROOT / "design" / "prototypes" / "homepage-v1-responsive.css"
DOC = ROOT / "docs" / "design" / "parket36-homepage-screen-spec-v1.md"

FIGMA_URL = "https://www.figma.com/design/2ovBluMs8xOKkkUIPevLaH"
TARGET_PAGE = "Screens — Desktop и Mobile сайт"
EXPECTED_SECTIONS = ["header", "hero", "problems", "diagnostic", "assessment", "footer"]
EXPECTED_COMPONENTS = {"Button", "Badge", "Problem Card", "Section Header", "Input"}
EXPECTED_SCREEN_NAMES = ["Homepage/Desktop/1440", "Homepage/Mobile/390"]


class PrototypeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.h1_count = 0
        self.phone_links: list[str] = []
        self.local_assets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        node_id = values.get("id")
        if node_id:
            self.ids.add(node_id)
        if tag == "h1":
            self.h1_count += 1
        if tag == "a" and (values.get("href") or "").startswith("tel:"):
            self.phone_links.append(values.get("href") or "")
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


def token_dimension(tokens: dict[str, Any], dotted_path: str) -> int:
    value = get_path(tokens, f"{dotted_path}.$value.value")
    if not isinstance(value, int):
        raise ValueError(dotted_path)
    return value


def main() -> int:
    findings: list[str] = []
    required_files = (
        SCREEN,
        TOKENS,
        FOUNDATIONS,
        COMPONENTS,
        MANIFEST,
        PROTOTYPE,
        BASE_CSS,
        CONTENT_CSS,
        RESPONSIVE_CSS,
        DOC,
    )
    for path in required_files:
        if not path.is_file():
            findings.append(f"missing homepage screen asset: {path.relative_to(ROOT)}")
    if findings:
        for finding in findings:
            print(f"  - {finding}")
        return 1

    try:
        screen = read_json(SCREEN)
        tokens = read_json(TOKENS)
        foundations = read_json(FOUNDATIONS)
        components = read_json(COMPONENTS)
        manifest = read_json(MANIFEST)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Homepage screen JSON is invalid: {exc}")
        return 1

    meta = screen.get("meta", {})
    expected_meta = {
        "status": "draft",
        "figmaFile": FIGMA_URL,
        "figmaTargetPage": TARGET_PAGE,
        "tokenSource": "design/parket36-tokens.json",
        "foundationSource": "design/foundations/parket36-foundations.json",
        "componentSource": "design/components/parket36-components.json",
        "prototype": "design/prototypes/homepage-v1.htm",
        "productionImpact": "none",
    }
    for key, expected in expected_meta.items():
        if meta.get(key) != expected:
            findings.append(f"homepage screen meta.{key} must be {expected!r}")

    desktop = screen.get("canvases", {}).get("desktop", {})
    mobile = screen.get("canvases", {}).get("mobile", {})
    foundation_layout = foundations.get("layout", {})
    expected_desktop = {
        "figmaName": "Homepage/Desktop/1440",
        "width": token_dimension(tokens, "size.desktopCanvas"),
        "contentWidth": token_dimension(tokens, "size.container"),
        "columns": foundation_layout.get("desktopColumns"),
        "gutter": foundation_layout.get("desktopGutter"),
        "margin": foundation_layout.get("desktopMargin"),
    }
    expected_mobile = {
        "figmaName": "Homepage/Mobile/390",
        "width": token_dimension(tokens, "size.mobileCanvas"),
        "columns": foundation_layout.get("mobileColumns"),
        "gutter": foundation_layout.get("mobileGutter"),
        "margin": foundation_layout.get("mobileMargin"),
    }
    if desktop != expected_desktop:
        findings.append(f"desktop canvas differs from foundations: {desktop} != {expected_desktop}")
    if mobile != expected_mobile:
        findings.append(f"mobile canvas differs from foundations: {mobile} != {expected_mobile}")

    breakpoints = screen.get("breakpoints", {})
    if breakpoints != {"tablet": 1000, "mobile": 640}:
        findings.append("homepage breakpoints must remain tablet=1000 and mobile=640")

    global_rules = screen.get("globalRules", {})
    if global_rules.get("primaryJourney") != ["problem", "diagnosis", "solution", "action"]:
        findings.append("homepage primary journey is incorrect")
    for flag in (
        "noPromiseBeforeDiagnosis",
        "prototypeNoteInternalOnly",
        "prototypeNoteExcludedFromFigmaScreen",
        "realProjectAssetsRequiredBeforeProduction",
        "temporaryWoodColorsAreNotBrandTokens",
    ):
        if global_rules.get(flag) is not True:
            findings.append(f"homepage global rule must remain true: {flag}")
    if global_rules.get("primaryAction") != "Оценить по фото":
        findings.append("homepage primary action must remain photo assessment")

    sections = screen.get("sections", [])
    section_ids = [section.get("id") for section in sections]
    if section_ids != EXPECTED_SECTIONS:
        findings.append(f"homepage section order is incorrect: {section_ids}")
    if len(section_ids) != len(set(section_ids)):
        findings.append("homepage section IDs must be unique")

    used_components: set[str] = set()
    for section in sections:
        for component in section.get("components", []):
            used_components.add(component)
            if component not in EXPECTED_COMPONENTS:
                findings.append(f"screen references unknown component: {component}")
    contract_components = {
        item.get("figmaName") for item in components.get("components", {}).values()
    }
    if not used_components.issubset(contract_components):
        findings.append("screen component usage is not covered by the component contract")
    if used_components != {"Button", "Badge", "Problem Card", "Section Header"}:
        findings.append(f"unexpected homepage component usage: {sorted(used_components)}")

    problem_section = next((item for item in sections if item.get("id") == "problems"), {})
    problem_items = problem_section.get("items", [])
    if len(problem_items) != 5:
        findings.append("homepage must contain exactly five problem choices")
    if [item.get("number") for item in problem_items] != ["01", "02", "03", "04", "05"]:
        findings.append("problem card numbering must remain 01–05")

    hero = next((item for item in sections if item.get("id") == "hero"), {})
    visual = hero.get("visual", {})
    if visual.get("type") != "before-after-placeholder":
        findings.append("hero visual must remain an explicit before-after placeholder")
    if [visual.get(key) for key in ("minimumDesktopHeight", "minimumTabletHeight", "minimumMobileHeight")] != [500, 430, 360]:
        findings.append("hero placeholder heights must remain 500/430/360")
    if "не являются UI- или brand-токенами" not in visual.get("policy", ""):
        findings.append("hero visual policy must exclude temporary wood colors from brand tokens")

    alignment = screen.get("componentAlignment", {})
    component_data = components.get("components", {})
    expected_alignment = {
        "Button": component_data.get("button", {}).get("dimensions", {}).get("mdHeight"),
        "Problem Card": component_data.get("problemCard", {}).get("dimensions", {}).get("minimumHeight"),
        "Section Header": component_data.get("sectionHeader", {}).get("dimensions", {}).get("maximumTextWidth"),
    }
    if alignment.get("Button", {}).get("minimumHeight") != expected_alignment["Button"]:
        findings.append("Button screen alignment differs from component contract")
    if alignment.get("Problem Card", {}).get("minimumHeight") != expected_alignment["Problem Card"]:
        findings.append("Problem Card screen alignment differs from component contract")
    if alignment.get("Section Header", {}).get("maximumTextWidth") != expected_alignment["Section Header"]:
        findings.append("Section Header screen alignment differs from component contract")
    if alignment.get("Problem Card", {}).get("titleSize") != 21:
        findings.append("Problem Card title size must remain 21 px")

    manifest_meta = manifest.get("meta", {})
    if manifest_meta.get("screenSource") != "design/screens/homepage-v1.json":
        findings.append("Figma manifest must reference the homepage screen contract")
    if manifest_meta.get("screenPrototype") != "design/prototypes/homepage-v1.htm":
        findings.append("Figma manifest must reference the homepage prototype")
    manifest_screens = manifest.get("screens", {})
    if list(manifest_screens) != EXPECTED_SCREEN_NAMES:
        findings.append("Figma manifest screen names differ from the screen contract")
    for name, expected_width in (("Homepage/Desktop/1440", 1440), ("Homepage/Mobile/390", 390)):
        entry = manifest_screens.get(name, {})
        if entry.get("nodeId") is not None or entry.get("status") != "pending":
            findings.append(f"Figma screen must remain pending until creation: {name}")
        if entry.get("width") != expected_width:
            findings.append(f"Figma screen width is incorrect: {name}")
        if entry.get("source") != "design/screens/homepage-v1.json":
            findings.append(f"Figma screen source is incorrect: {name}")

    html = PROTOTYPE.read_text(encoding="utf-8")
    base_css = BASE_CSS.read_text(encoding="utf-8")
    content_css = CONTENT_CSS.read_text(encoding="utf-8")
    responsive_css = RESPONSIVE_CSS.read_text(encoding="utf-8")
    required_html = [
        'meta name="robots" content="noindex,nofollow"',
        "data-design-prototype",
        'id="top"',
        'id="problems"',
        'id="diagnostic"',
        'id="assessment"',
        "Вернём деревянному полу характер",
        "Без обещаний до диагностики",
        "Начните с 2–4 фотографий",
    ]
    for marker in required_html:
        if marker not in html:
            findings.append(f"homepage prototype is missing marker: {marker}")

    parser = PrototypeParser()
    parser.feed(html)
    if parser.h1_count != 1:
        findings.append(f"homepage prototype must contain exactly one h1, found {parser.h1_count}")
    for required_id in ("top", "problems", "diagnostic", "assessment"):
        if required_id not in parser.ids:
            findings.append(f"homepage prototype is missing anchor: {required_id}")
    if not parser.phone_links or set(parser.phone_links) != {"tel:+79009267929"}:
        findings.append("homepage prototype phone links must use tel:+79009267929")
    for raw_path in parser.local_assets:
        asset = (PROTOTYPE.parent / raw_path).resolve()
        try:
            asset.relative_to(ROOT)
        except ValueError:
            findings.append(f"homepage prototype asset escapes repository: {raw_path}")
            continue
        if not asset.is_file():
            findings.append(f"homepage prototype references missing asset: {raw_path}")

    css_markers = {
        "homepage-v1-base.css": [
            "min-height:max(48px,var(--p36-size-touch-min))",
            ".header__phone",
            ".button:focus-visible",
        ],
        "homepage-v1-content.css": [
            ".choice{min-height:168px",
            ".choice strong{display:block",
            "font-size:21px",
            ".section-head{max-width:760px",
        ],
        "homepage-v1-responsive.css": [
            "@media (max-width:1000px)",
            "@media (max-width:640px)",
            "width:min(100% - 40px,var(--p36-size-container))",
            ".choice-grid,.service-grid{grid-template-columns:1fr;}",
            "@media (prefers-reduced-motion:reduce)",
        ],
    }
    css_contents = {
        "homepage-v1-base.css": base_css,
        "homepage-v1-content.css": content_css,
        "homepage-v1-responsive.css": responsive_css,
    }
    for filename, markers in css_markers.items():
        content = css_contents[filename]
        for marker in markers:
            if marker not in content:
                findings.append(f"{filename} is missing screen-contract marker: {marker}")

    combined = f"{html}\n{base_css}\n{content_css}\n{responsive_css}".lower()
    for forbidden in ("<form", "<script", "supabase", "parket-public-lead", "request-form"):
        if forbidden in combined:
            findings.append(f"isolated homepage prototype contains forbidden marker: {forbidden}")

    doc = DOC.read_text(encoding="utf-8")
    for marker in (
        FIGMA_URL,
        TARGET_PAGE,
        "Desktop / 1440",
        "Mobile / 390",
        "боковые поля: 20 px",
        "Button` — минимум 48 px",
        "Problem Card` — минимум 168 px",
        "не являются цветами интерфейса или бренд-токенами",
    ):
        if marker.lower() not in doc.lower():
            findings.append(f"homepage screen documentation is missing marker: {marker}")

    if findings:
        print("Homepage screen contract findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Homepage screen contract passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
