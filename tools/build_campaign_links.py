#!/usr/bin/env python3
"""Build and validate deterministic campaign links for Parket36 launch channels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlencode, urlsplit

from site_settings import load_config

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "data" / "campaign-links.json"
OUTPUT_PATH = ROOT / "docs" / "campaign-links.md"
TOKEN_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def load_campaign_config() -> dict[str, object]:
    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"missing configuration: {CONFIG_PATH.relative_to(ROOT)}") from None
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {CONFIG_PATH.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("campaign configuration must be a JSON object")
    return payload


def landing_file(path: str) -> Path:
    relative = path.strip("/")
    return ROOT / relative / "index.html" if relative else ROOT / "index.html"


def validate_token(value: object, field: str, name: str) -> str:
    if not isinstance(value, str) or not TOKEN_PATTERN.fullmatch(value):
        raise ValueError(f"{name}: {field} must match {TOKEN_PATTERN.pattern}")
    return value


def validate_fragment(path: str, value: object, name: str) -> str:
    if value is None:
        return ""
    fragment = validate_token(value, "fragment", name)
    landing = landing_file(path)
    text = landing.read_text(encoding="utf-8", errors="ignore")
    if f'id="{fragment}"' not in text and f"id='{fragment}'" not in text:
        raise ValueError(f"{name}: fragment target does not exist on {path}: #{fragment}")
    return fragment


def build_rows() -> tuple[str, list[dict[str, str]]]:
    site = load_config()
    domain = str(site["domain"]).rstrip("/")
    if urlsplit(domain).scheme != "https":
        raise ValueError("site domain must use HTTPS")

    payload = load_campaign_config()
    campaign = validate_token(payload.get("campaign"), "campaign", "configuration")
    links = payload.get("links")
    if not isinstance(links, list) or not links:
        raise ValueError("campaign configuration must contain a non-empty links array")

    rows: list[dict[str, str]] = []
    names: set[str] = set()
    urls: set[str] = set()

    for index, item in enumerate(links, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"link #{index} must be an object")
        name = item.get("name")
        purpose = item.get("purpose")
        path = item.get("path")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"link #{index}: name is required")
        if not isinstance(purpose, str) or not purpose.strip():
            raise ValueError(f"{name}: purpose is required")
        if not isinstance(path, str) or not path.startswith("/"):
            raise ValueError(f"{name}: path must start with /")
        parsed_path = urlsplit(path)
        if parsed_path.scheme or parsed_path.netloc or parsed_path.query or parsed_path.fragment:
            raise ValueError(f"{name}: path must not contain a host, query or fragment")
        if not path.endswith("/"):
            raise ValueError(f"{name}: path must end with /")
        if not landing_file(path).is_file():
            raise ValueError(f"{name}: landing page does not exist: {path}")
        if name in names:
            raise ValueError(f"duplicate link name: {name}")
        names.add(name)

        source = validate_token(item.get("source"), "source", name)
        medium = validate_token(item.get("medium"), "medium", name)
        content = validate_token(item.get("content"), "content", name)
        fragment = validate_fragment(path, item.get("fragment"), name)
        params = {
            "utm_source": source,
            "utm_medium": medium,
            "utm_campaign": campaign,
            "utm_content": content,
        }
        term = item.get("term")
        if term is not None:
            params["utm_term"] = validate_token(term, "term", name)

        url = f"{domain}{path}?{urlencode(params)}"
        landing = path
        if fragment:
            url = f"{url}#{fragment}"
            landing = f"{path}#{fragment}"
        if url in urls:
            raise ValueError(f"duplicate generated URL: {url}")
        urls.add(url)
        rows.append(
            {
                "name": name.strip(),
                "purpose": purpose.strip(),
                "path": landing,
                "url": url,
                "content": content,
                "fragment": fragment,
            }
        )

    return campaign, rows


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render_markdown() -> str:
    campaign, rows = build_rows()
    lines = [
        "# Измеряемые ссылки запуска Паркет36",
        "",
        "Файл генерируется из `data/campaign-links.json` командой `python tools/build_campaign_links.py --write`.",
        "Проверка актуальности входит в общий quality gate: `python tools/build_campaign_links.py --check`.",
        "",
        f"Единая кампания: `{campaign}`.",
        "",
        "## Готовые ссылки",
        "",
        "| Размещение | Назначение | Посадочная | Измеряемая ссылка |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {name} | {purpose} | `{path}` | `{url}` |".format(
                name=markdown_escape(row["name"]),
                purpose=markdown_escape(row["purpose"]),
                path=row["path"],
                url=row["url"],
            )
        )

    lines.extend(
        [
            "",
            "## Как использовать",
            "",
            "- размещать готовую ссылку только в указанном канале, не заменяя её обычной ссылкой на домен;",
            "- для нового объявления или макета добавлять отдельный `content`, чтобы обращения не смешивались;",
            "- QR-код создавать именно из полной ссылки с UTM-параметрами;",
            "- для ссылки с якорем сохранять порядок `?utm_...#callback`: query перед fragment;",
            "- после восстановления домена сначала открыть каждую ссылку вручную и убедиться, что посадочная страница загружается по HTTPS;",
            "- не публиковать ссылки на ещё не созданные карточки: строки для Яндекс Бизнеса и 2ГИС подготовлены заранее, но используются только после подтверждения соответствующей карточки.",
            "",
            "## Прямая ссылка на обратный звонок",
            "",
            "Ссылка `VK — обратный звонок` открывает `/kontakty/#callback` сразу на короткой форме. Генератор проверяет, что целевая страница существует и содержит элемент `id=\"callback\"`. UTM остаются в query-параметрах до `#callback`, поэтому first-touch атрибуция сохраняется до отправки заявки.",
            "",
            "## Что уже измеряется",
            "",
            "Сайт сохраняет первую UTM-атрибуцию в пределах сессии и передаёт `utm_source`, `utm_medium`, `utm_campaign`, `utm_content` и `utm_term` вместе с заявкой. Поэтому источник заявки по форме можно определить даже до подключения Яндекс Метрики, если production Edge Function развёрнута и сохраняет актуальный payload.",
            "",
            "Клик по телефону отправляется как аналитическое событие только после подключения счётчика. До этого звонки нельзя надёжно связать с конкретной UTM-ссылкой средствами самого сайта.",
            "",
            "## Ограничения",
            "",
            "Готовые ссылки не создают рекламу, карточки или объявления автоматически. Они дают единый формат атрибуции для ручных размещений и не заменяют доступный домен, аналитику, подтверждённые фотографии и фактическую обработку обращений.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        expected = render_markdown()
    except ValueError as exc:
        print(f"Campaign link findings: {exc}")
        return 1

    if args.write:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(expected, encoding="utf-8")
        print(f"Wrote {OUTPUT_PATH.relative_to(ROOT)}")
        return 0

    if not OUTPUT_PATH.is_file():
        print(f"Campaign link findings: missing {OUTPUT_PATH.relative_to(ROOT)}")
        return 1
    actual = OUTPUT_PATH.read_text(encoding="utf-8")
    if actual != expected:
        print(f"Campaign link findings: {OUTPUT_PATH.relative_to(ROOT)} is stale")
        return 1

    print("Campaign links check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
