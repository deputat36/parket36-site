#!/usr/bin/env python3
"""Build a deterministic report of public HTML coverage by shared-shell profiles."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import asdict, dataclass
from io import StringIO
from pathlib import Path
import sys

from build_pages import PUBLIC_DIRS, PUBLIC_FILES, is_internal_working_path
from shared_shell import (
    DEFAULT_REQUEST_LABEL,
    FAMILY_PROFILES,
    PAGE_PROFILES,
    build_page_profiles,
    declared_family_pages,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = "reports/shared-shell-coverage"


@dataclass(frozen=True)
class CoverageRecord:
    source_path: str
    url_path: str
    coverage: str
    profile_source: str
    components: str
    active_nav: str
    request_href: str
    request_label: str


def path_to_url(relative: Path) -> str:
    """Convert a public HTML source path to its site-relative URL."""
    if relative == Path("index.html"):
        return "/"
    if relative.name == "index.html":
        return f"/{relative.parent.as_posix()}/"
    return f"/{relative.as_posix()}"


def iter_public_source_html(root: Path) -> list[Path]:
    """Return exactly the public source HTML files copied by build_pages.py."""
    result: set[Path] = set()
    for name in PUBLIC_DIRS:
        directory = root / name
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.html"):
            relative = path.relative_to(root)
            if not is_internal_working_path(relative):
                result.add(path)

    for name in PUBLIC_FILES:
        if not name.endswith(".html"):
            continue
        path = root / name
        if path.is_file():
            result.add(path)
    return sorted(result)


def family_sources(
    root: Path,
    profiles: dict[Path, dict[str, object]],
) -> tuple[dict[Path, str], list[str]]:
    """Map discovered family pages to their declarative family name."""
    findings: list[str] = []
    sources: dict[Path, str] = {}

    for family in FAMILY_PROFILES:
        name = family.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        family_findings: list[str] = []
        pages = declared_family_pages(root, family, family_findings)
        findings.extend(family_findings)
        for relative in pages:
            if relative not in profiles or relative in PAGE_PROFILES:
                continue
            previous = sources.get(relative)
            if previous is not None and previous != name.strip():
                findings.append(
                    f"{relative.as_posix()}: shared shell page belongs to multiple families: "
                    f"{previous}, {name.strip()}"
                )
                continue
            sources[relative] = name.strip()
    return sources, findings


def classify_records(
    public_pages: list[Path],
    profiles: dict[Path, dict[str, object]],
    family_by_path: dict[Path, str],
) -> list[CoverageRecord]:
    """Classify public pages as explicit, family-backed or outside shared shell."""
    records: list[CoverageRecord] = []
    for relative in sorted(public_pages):
        profile = profiles.get(relative)
        if profile is None:
            records.append(
                CoverageRecord(
                    source_path=relative.as_posix(),
                    url_path=path_to_url(relative),
                    coverage="outside",
                    profile_source="—",
                    components="—",
                    active_nav="—",
                    request_href="—",
                    request_label="—",
                )
            )
            continue

        if relative in PAGE_PROFILES:
            profile_source = "explicit"
        else:
            family_name = family_by_path.get(relative)
            profile_source = f"family:{family_name}" if family_name else "family:unknown"

        components = profile.get("components")
        active_nav = profile.get("active_nav")
        request_href = profile.get("request_href")
        request_label = profile.get("request_label", DEFAULT_REQUEST_LABEL)
        records.append(
            CoverageRecord(
                source_path=relative.as_posix(),
                url_path=path_to_url(relative),
                coverage="profiled",
                profile_source=profile_source,
                components=", ".join(components) if isinstance(components, tuple) else "—",
                active_nav=active_nav if isinstance(active_nav, str) else "none",
                request_href=request_href if isinstance(request_href, str) else "—",
                request_label=(
                    request_label.strip()
                    if isinstance(request_label, str) and request_label.strip()
                    else "—"
                ),
            )
        )
    return records


def collect_coverage(root: Path = ROOT) -> tuple[list[CoverageRecord], list[str]]:
    """Collect profile coverage and structural findings for the source tree."""
    findings: list[str] = []
    profiles = build_page_profiles(root, root, findings)
    family_by_path, family_findings = family_sources(root, profiles)
    findings.extend(family_findings)

    public_paths = [path.relative_to(root) for path in iter_public_source_html(root)]
    public_set = set(public_paths)
    orphan_profiles = sorted(set(profiles) - public_set)
    if orphan_profiles:
        findings.append(
            "Shared shell profiles reference non-public or missing HTML pages: "
            + ", ".join(path.as_posix() for path in orphan_profiles)
        )

    records = classify_records(public_paths, profiles, family_by_path)
    if not records:
        findings.append("No public HTML pages were collected for shared shell coverage")

    unknown_family = [record.source_path for record in records if record.profile_source == "family:unknown"]
    if unknown_family:
        findings.append(
            "Family-backed pages are missing a declarative family source: "
            + ", ".join(unknown_family)
        )
    return records, findings


def csv_text(records: list[CoverageRecord]) -> str:
    output = StringIO(newline="")
    fieldnames = list(asdict(records[0]).keys()) if records else []
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    if fieldnames:
        writer.writeheader()
        for record in records:
            writer.writerow(asdict(record))
    return output.getvalue()


def markdown_text(records: list[CoverageRecord]) -> str:
    profiled = [record for record in records if record.coverage == "profiled"]
    outside = [record for record in records if record.coverage == "outside"]
    source_counts = Counter(record.profile_source for record in profiled)
    coverage_percent = (len(profiled) / len(records) * 100) if records else 0.0

    lines = [
        "# Покрытие shared shell",
        "",
        "Файл генерируется командой `python tools/build_shared_shell_coverage.py --output-dir reports/shared-shell-coverage`.",
        "Отчёт показывает, какие публичные HTML-страницы используют явный или семейный профиль общей оболочки, а какие пока остаются вне shared shell.",
        "",
        "## Сводка",
        "",
        f"- публичных HTML-страниц: {len(records)};",
        f"- страниц с профилем shared shell: {len(profiled)};",
        f"- страниц вне shared shell: {len(outside)};",
        f"- покрытие: {coverage_percent:.1f}%.",
        "",
        "Страница вне shared shell не считается автоматической ошибкой: отчёт нужен для осознанного выбора следующего однородного семейства и для обнаружения новых непрофилированных страниц.",
        "",
        "## Источники профилей",
        "",
        "| Источник | Страниц |",
        "|---|---:|",
    ]
    for source, count in sorted(source_counts.items()):
        lines.append(f"| `{source}` | {count} |")
    lines.append(f"| вне shared shell | {len(outside)} |")

    lines.extend(["", "## Страницы вне shared shell", ""])
    if outside:
        lines.extend(["| URL | Исходный файл |", "|---|---|"])
        for record in outside:
            lines.append(f"| `{record.url_path}` | `{record.source_path}` |")
    else:
        lines.append("Все публичные HTML-страницы охвачены shared shell.")

    lines.extend(
        [
            "",
            "## Полные данные",
            "",
            "Artifact `shared-shell-coverage` содержит:",
            "",
            "- `shared-shell-coverage.csv` — классификацию каждой публичной HTML-страницы;",
            "- `shared-shell-coverage.md` — этот отчёт с актуальной сводкой.",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(output_dir: Path, root: Path = ROOT) -> tuple[Path, Path, list[str]]:
    records, findings = collect_coverage(root)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "shared-shell-coverage.csv"
    markdown_path = output_dir / "shared-shell-coverage.md"
    csv_path.write_text(csv_text(records), encoding="utf-8")
    markdown_path.write_text(markdown_text(records), encoding="utf-8")
    return csv_path, markdown_path, findings


def self_test() -> list[str]:
    findings: list[str] = []
    public_pages = [
        Path("404.html"),
        Path("index.html"),
        Path("politika/index.html"),
        Path("sovety/example/index.html"),
        Path("uslugi/example/index.html"),
    ]
    profiles = {
        Path("index.html"): {
            "components": ("header", "footer"),
            "active_nav": None,
            "request_href": "#request",
        },
        Path("sovety/example/index.html"): {
            "components": ("header", "mobile-cta"),
            "active_nav": "/sovety/",
            "request_href": "/zayavka/",
        },
        Path("uslugi/example/index.html"): {
            "components": ("header", "mobile-cta"),
            "active_nav": None,
            "request_href": "/zayavka/",
        },
    }
    records = classify_records(
        public_pages,
        profiles,
        {
            Path("sovety/example/index.html"): "articles",
            Path("uslugi/example/index.html"): "adjacent-services",
        },
    )
    by_path = {record.source_path: record for record in records}
    if by_path["index.html"].profile_source != "explicit":
        findings.append("self-test: explicit profile classification failed")
    if by_path["sovety/example/index.html"].profile_source != "family:articles":
        findings.append("self-test: glob family profile classification failed")
    if by_path["uslugi/example/index.html"].profile_source != "family:adjacent-services":
        findings.append("self-test: allowlist family profile classification failed")
    if by_path["politika/index.html"].coverage != "outside":
        findings.append("self-test: outside-page classification failed")
    if by_path["404.html"].url_path != "/404.html":
        findings.append("self-test: file URL conversion failed")
    if by_path["sovety/example/index.html"].url_path != "/sovety/example/":
        findings.append("self-test: index URL conversion failed")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        findings = self_test()
        if findings:
            print("Shared shell coverage self-test findings:")
            for finding in findings:
                print(f"  - {finding}")
            return 1
        print("Shared shell coverage self-test passed")
        return 0

    csv_path, markdown_path, findings = write_report(ROOT / args.output_dir)
    if findings:
        print("Shared shell coverage findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1
    print(f"Wrote {csv_path.relative_to(ROOT)}")
    print(f"Wrote {markdown_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
