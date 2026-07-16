#!/usr/bin/env python3
"""Validate reviewed public pages that intentionally stay outside shared shell."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re

DOMAIN = "https://parket36.ru"
CATEGORY_RE = re.compile(r"^[a-z][a-z0-9-]*$")
REFRESH_TARGET_RE = re.compile(r"(?:^|;)\s*url\s*=\s*(.+?)\s*$", re.IGNORECASE)

SHARED_SHELL_EXCLUSIONS = (
    {
        "path": Path("404.html"),
        "category": "error",
        "reason": (
            "Специальный документ ошибки сохраняет компактный recovery-интерфейс "
            "и сокращённый footer вместо стандартной общей оболочки."
        ),
        "required_robots": "noindex, follow",
        "required_canonical": f"{DOMAIN}/404.html",
    },
    {
        "path": Path("politika/index.html"),
        "category": "legal",
        "reason": (
            "Юридическая страница использует сокращённую навигацию и минимальный footer, "
            "чтобы не смешивать политику обработки данных с коммерческим сценарием."
        ),
        "required_robots": "noindex, follow",
        "required_canonical": f"{DOMAIN}/politika/",
    },
    {
        "path": Path("pozvonit-ivanu/index.html"),
        "category": "campaign",
        "reason": (
            "Noindex-памятка звонка сохраняет отдельные call-first CTA и собственные "
            "data-call-source маркеры для атрибуции звонков."
        ),
        "required_robots": "noindex, follow",
        "required_canonical": f"{DOMAIN}/pozvonit-ivanu/",
        "required_markers": (
            'data-call-source="phone-helper-hero"',
            'data-call-source="phone-helper-final"',
        ),
    },
    {
        "path": Path("uslugi/master-na-chas/index.html"),
        "category": "redirect",
        "reason": (
            "Legacy noindex-переходник ведёт на канонический адрес /uslugi/muzh-na-chas/ "
            "и не должен выглядеть как самостоятельная услуга."
        ),
        "required_robots": "noindex, follow",
        "required_canonical": f"{DOMAIN}/uslugi/muzh-na-chas/",
        "required_refresh_target": "/uslugi/muzh-na-chas/",
    },
)


class MetadataParser(HTMLParser):
    """Collect only metadata required by reviewed-exclusion contracts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.robots: list[str] = []
        self.canonicals: list[str] = []
        self.refresh_targets: list[str] = []

    def handle_starttag(self, tag: str, attrs_list: list[tuple[str, str | None]]) -> None:
        attrs = {key.lower(): (value or "").strip() for key, value in attrs_list}
        lowered = tag.lower()
        if lowered == "meta" and attrs.get("name", "").lower() == "robots":
            self.robots.append(" ".join(attrs.get("content", "").split()))
            return
        if lowered == "link" and "canonical" in attrs.get("rel", "").lower().split():
            self.canonicals.append(attrs.get("href", ""))
            return
        if lowered == "meta" and attrs.get("http-equiv", "").lower() == "refresh":
            match = REFRESH_TARGET_RE.search(attrs.get("content", ""))
            self.refresh_targets.append(match.group(1).strip(" \"'") if match else "")


def _required_text(
    entry: dict[str, object],
    key: str,
    label: str,
    findings: list[str],
) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        findings.append(f"{label}: {key} must be a non-empty string")
        return ""
    return value.strip()


def validate_exclusion_registry(
    root: Path,
    public_pages: list[Path],
    profiled_pages: set[Path],
    registry: tuple[dict[str, object], ...] = SHARED_SHELL_EXCLUSIONS,
) -> tuple[dict[Path, dict[str, str]], list[str]]:
    """Return validated exclusions and fail-closed structural findings."""

    findings: list[str] = []
    exclusions: dict[Path, dict[str, str]] = {}
    public_set = set(public_pages)
    seen: set[Path] = set()

    if not isinstance(registry, tuple) or not registry:
        return {}, ["Shared shell exclusion registry must be a non-empty tuple"]

    for index, entry in enumerate(registry, start=1):
        label = f"shared shell exclusion #{index}"
        if not isinstance(entry, dict):
            findings.append(f"{label}: entry must be a mapping")
            continue

        relative = entry.get("path")
        if not isinstance(relative, Path) or not relative.parts:
            findings.append(f"{label}: path must be a non-empty relative Path")
            continue
        context = relative.as_posix()
        label = f"{context} exclusion"
        if relative.is_absolute() or ".." in relative.parts or relative.suffix != ".html":
            findings.append(f"{label}: path must be a safe public HTML path")
            continue
        if relative in seen:
            findings.append(f"Duplicate shared shell exclusion path: {context}")
            continue
        seen.add(relative)

        category = _required_text(entry, "category", label, findings)
        reason = _required_text(entry, "reason", label, findings)
        required_robots = _required_text(entry, "required_robots", label, findings)
        required_canonical = _required_text(entry, "required_canonical", label, findings)
        if category and not CATEGORY_RE.fullmatch(category):
            findings.append(f"{label}: category must use lowercase kebab-case")

        required_refresh = entry.get("required_refresh_target")
        if required_refresh is not None and (
            not isinstance(required_refresh, str) or not required_refresh.strip()
        ):
            findings.append(f"{label}: required_refresh_target must be non-empty when defined")
            required_refresh = ""
        if category == "redirect" and not isinstance(required_refresh, str):
            findings.append(f"{label}: redirect exclusions must define required_refresh_target")
        if category != "redirect" and required_refresh is not None:
            findings.append(f"{label}: only redirect exclusions may define required_refresh_target")

        required_markers = entry.get("required_markers", ())
        if not isinstance(required_markers, tuple) or not all(
            isinstance(marker, str) and marker.strip() for marker in required_markers
        ):
            findings.append(f"{label}: required_markers must be a tuple of non-empty strings")
            required_markers = ()
        elif len(set(required_markers)) != len(required_markers):
            findings.append(f"{label}: required_markers contain duplicates")

        if relative not in public_set:
            findings.append(f"{label}: references a non-public or missing HTML page")
        if relative in profiled_pages:
            findings.append(f"{label}: overlaps an explicit or family shared shell profile")

        source = root / relative
        if source.is_file():
            text = source.read_text(encoding="utf-8")
            parser = MetadataParser()
            parser.feed(text)
            if required_robots and parser.robots != [required_robots]:
                findings.append(
                    f"{label}: expected exactly one robots={required_robots}, found {parser.robots}"
                )
            if required_canonical and parser.canonicals != [required_canonical]:
                findings.append(
                    f"{label}: expected exactly one canonical={required_canonical}, "
                    f"found {parser.canonicals}"
                )
            if isinstance(required_refresh, str) and required_refresh.strip():
                target = required_refresh.strip()
                if parser.refresh_targets != [target]:
                    findings.append(
                        f"{label}: expected exactly one meta refresh target {target}, "
                        f"found {parser.refresh_targets}"
                    )
            elif parser.refresh_targets:
                findings.append(f"{label}: unexpected meta refresh target {parser.refresh_targets}")
            for marker in required_markers:
                if text.count(marker) != 1:
                    findings.append(f"{label}: expected exactly one required marker {marker}")

        exclusions[relative] = {
            "category": category or "invalid",
            "reason": reason or "invalid exclusion metadata",
        }

    return exclusions, findings
