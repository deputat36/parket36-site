#!/usr/bin/env python3
"""Self-test the deterministic raster OG card generator."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import sys

from og_cards import apply_og_cards, validate_og_cards

DOMAIN = "https://parket36.ru"
FIXTURE = """<!doctype html>
<html lang="ru">
<head>
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://parket36.ru/test-og/">
  <meta property="og:title" content="Как проверить старый паркет перед работами">
  <meta property="og:description" content="Практический чек-лист для осмотра паркета, щелей, скрипа и старого покрытия.">
  <meta property="og:image" content="https://parket36.ru/img/og-master36.svg">
  <script type="application/ld+json">{"@context":"https://schema.org","@graph":[{"@type":"Article","headline":"Тестовая страница","author":{"@type":"Person","name":"Иван"},"publisher":{"@type":"Organization","name":"Паркет36"},"datePublished":"2026-07-01","dateModified":"2026-07-01","mainEntityOfPage":"https://parket36.ru/test-og/"},{"@type":"ProfessionalService","name":"Паркет36 — мастер Иван","url":"https://parket36.ru/","telephone":"+79009267929"}]}</script>
</head>
<body><main><h1>Тестовая страница</h1></main></body>
</html>
"""


def main() -> int:
    findings: list[str] = []
    with TemporaryDirectory(prefix="parket-og-card-") as temporary:
        destination = Path(temporary)
        page = destination / "test-og" / "index.html"
        page.parent.mkdir(parents=True)
        page.write_text(FIXTURE, encoding="utf-8")

        generated = apply_og_cards(destination, DOMAIN, findings)
        checked = validate_og_cards(destination, DOMAIN, findings)
        cards = sorted((destination / "img" / "og").glob("*.png"))
        if generated != 1 or checked != 1 or len(cards) != 1:
            findings.append(
                f"Expected one generated and validated card; got generated={generated}, "
                f"checked={checked}, files={len(cards)}"
            )
        first_digest = sha256(cards[0].read_bytes()).hexdigest() if cards else ""
        first_name = cards[0].name if cards else ""

        generated_again = apply_og_cards(destination, DOMAIN, findings)
        cards_again = sorted((destination / "img" / "og").glob("*.png"))
        second_digest = sha256(cards_again[0].read_bytes()).hexdigest() if cards_again else ""
        second_name = cards_again[0].name if cards_again else ""
        if generated_again != 1 or first_name != second_name or first_digest != second_digest:
            findings.append("OG card generation must be deterministic")

        built_html = page.read_text(encoding="utf-8")
        required_markers = (
            "/img/og/og-",
            'property="og:image:type" content="image/png"',
            'property="og:image:width" content="1200"',
            'property="og:image:height" content="630"',
            'name="twitter:card" content="summary_large_image"',
            'name="twitter:image" content="https://parket36.ru/img/og/',
            '"@type":"Article"',
            '"@type":"ProfessionalService"',
            '"image":"https://parket36.ru/img/og/',
        )
        for marker in required_markers:
            if marker not in built_html:
                findings.append(f"Generated HTML is missing marker: {marker}")
        if built_html.count('"image":"https://parket36.ru/img/og/') != 2:
            findings.append("Article and ProfessionalService must share the generated PNG")

    if findings:
        print("OG card findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print("OG card generator check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
