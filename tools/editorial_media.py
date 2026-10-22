"""Render source-backed, explicitly illustrative media into public page templates."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
import re

SUBHERO = re.compile(r'(<section\b[^>]*class="subhero"[^>]*>)(.*?)(</section>)', re.S)


def figure(asset: dict, *, hero: bool = False, classes: str = "", card: bool = False) -> str:
    """Use intrinsic dimensions and responsive sources without inventing photo provenance."""
    src = escape(asset["src"], quote=True)
    alt = escape(asset["alt"], quote=True)
    caption = escape(asset["caption"])
    sizes = "(max-width: 640px) calc(100vw - 32px), (max-width: 1000px) 90vw, 560px"
    if card:
        sizes = "(max-width: 640px) calc(100vw - 32px), (max-width: 1000px) 44vw, 360px"
    responsive = ""
    if asset.get("srcset"):
        responsive = f' srcset="{escape(asset["srcset"], quote=True)}" sizes="{sizes}"'
    priority = ' fetchpriority="high"' if hero else ' loading="lazy"'
    return (
        f'<figure class="editorial-figure {classes}" data-editorial-media>'
        f'<img src="{src}" alt="{alt}" width="{asset["width"]}" '
        f'height="{asset["height"]}" decoding="async"{responsive}{priority}>'
        f'<figcaption>{caption}</figcaption></figure>'
    )


def render_explainer(entry: dict, assets: dict) -> str:
    """Keep explanatory text in HTML so it remains readable at mobile sizes."""
    cards = []
    for item in entry["cards"]:
        media = figure(assets[item["asset"]], classes="visual-explainer__figure", card=True)
        cards.append(
            '<article class="visual-explainer__card">' + media
            + '<div class="visual-explainer__copy"><h3>' + escape(item["title"])
            + '</h3><p>' + escape(item["text"]) + '</p></div></article>'
        )
    note = '<p class="visual-explainer__note">' + escape(entry["note"]) + '</p>' if entry.get("note") else ""
    return (
        '<section class="section visual-explainer" data-visual-explainer>'
        '<div class="container"><div class="section__head"><h2>'
        + escape(entry["title"]) + '</h2><p>' + escape(entry["intro"])
        + '</p></div><div class="visual-explainer__grid">' + ''.join(cards)
        + '</div>' + note + '</div></section>'
    )


def apply_editorial_media(root: Path, destination: Path, errors: list[str]) -> None:
    manifest = json.loads((root / "data" / "editorial-media.json").read_text(encoding="utf-8"))
    assets = manifest["assets"]
    explainers = manifest.get("explainers", {})
    for key, entry in explainers.items():
        for item in entry["cards"]:
            if item["asset"] not in assets:
                errors.append(f"Visual explainer {key}: unknown asset {item['asset']}")
    if errors:
        return
    for key, asset in assets.items():
        if not asset.get("provenance") or not asset.get("caption"):
            errors.append(f"Editorial asset {key}: provenance/caption is missing")
        for url in [asset["src"], *[v.strip().split()[0] for v in asset.get("srcset", "").split(",") if v.strip()]]:
            if not url.startswith("/img/") or ".." in url or not (destination / url.lstrip("/")).is_file():
                errors.append(f"Editorial asset {key}: unavailable local image {url}")

    count = 0
    for relative, entry in manifest["pages"].items():
        target = destination / relative
        if not target.is_file():
            errors.append(f"Editorial media references a non-public page: {relative}")
            continue
        text = target.read_text(encoding="utf-8")
        if relative != "index.html":
            media = figure(assets[entry["hero"]], hero=True, classes="editorial-figure--hero")
            match = SUBHERO.search(text)
            if not match:
                errors.append(f"Editorial media: no subhero on {relative}")
                continue
            inner = match[2]
            summary = ""
            if "subhero__grid" in inner:
                # Preserve useful copy and actions while freeing the second column for media.
                original_aside = re.search(r'<aside\b[^>]*>.*?</aside>', inner, re.S)
                if original_aside:
                    aside = original_aside[0].replace("person-card--photo-plan", "editorial-summary")
                    aside = aside.replace("<h3>", "<h2>").replace("</h3>", "</h2>")
                    summary = '<section class="section section--summary"><div class="container">' + aside + '</div></section>'
                inner, replaced = re.subn(r'<aside\b[^>]*>.*?</aside>', lambda _: media, inner, count=1, flags=re.S)
                if not replaced:
                    errors.append(f"Editorial media: unsupported grid on {relative}")
                    continue
            else:
                opening = re.match(r'\s*<div class="container">', inner)
                closing = inner.rfind("</div>")
                if not opening or closing < opening.end():
                    errors.append(f"Editorial media: unsupported subhero on {relative}")
                    continue
                copy = inner[opening.end():closing]
                inner = f'<div class="container subhero__grid"><div class="subhero__copy">{copy}</div>{media}</div>'
            text = text[:match.start()] + match[1] + inner + match[3] + summary + text[match.end():]

        # Supplement a commercial page or article with a topic-specific explanatory diagram.
        if entry.get("explainer"):
            key = entry["explainer"]
            if key not in explainers:
                errors.append(f"Visual explainer is missing: {key} on {relative}")
                continue
            block = render_explainer(explainers[key], assets)
            hero = SUBHERO.search(text)
            if not hero:
                errors.append(f"Visual explainer: no subhero on {relative}")
                continue
            # A page's useful original summary stays ahead of the visual explanation.
            summary = re.match(r'<section class="section section--summary">.*?</section>', text[hero.end():], re.S)
            position = hero.end() + (summary.end() if summary else 0)
            text = text[:position] + block + text[position:]
        elif entry.get("diagram"):
            diagram = figure(assets[entry["diagram"]], classes="editorial-figure--diagram")
            block = '<section class="section section--visual"><div class="container">' + diagram + '</div></section>'
            cta = text.find('<section class="final-cta"')
            if cta == -1:
                cta = text.find("</main>")
            if cta == -1:
                errors.append(f"Editorial media: no main landmark on {relative}")
                continue
            text = text[:cta] + block + text[cta:]
        target.write_text(text, encoding="utf-8")
        count += 1
    print(f"Editorial media prepared {count} pages from the provenance manifest")
