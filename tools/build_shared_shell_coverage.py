#!/usr/bin/env python3
"""Build a deterministic governance report for public shared-shell coverage."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import asdict, dataclass
from io import StringIO
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from build_pages import PUBLIC_DIRS, PUBLIC_FILES, is_internal_working_path
from shared_shell import (
    DEFAULT_REQUEST_LABEL,
    FAMILY_PROFILES,
    PAGE_PROFILES,
    build_page_profiles,
    declared_family_pages,
)
from shared_shell_exclusions import (
    SHARED_SHELL_EXCLUSIONS,
    validate_exclusion_registry,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = "reports/shared-shell-coverage"


@dataclass(frozen=True)
class CoverageRecord:
    source_path: str
    url_path: str
    coverage: str
    profile_source: str
    exclusion_category: str
    exclusion_reason: str
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
    exclusions: dict[Path, dict[str, str]],
) -> list[CoverageRecord]:
    """Classify every public page as profiled, reviewed exclusion or unclassified."""
    records: list[CoverageRecord] = []
    for relative in sorted(public_pages):
        profile = profiles.get(relative)
        if profile is None:
            exclusion = exclusions.get(relative)
            if exclusion is None:
                coverage = "unclassified"
                exclusion_category = "—"
                exclusion_reason = "—"
            else:
                coverage = "excluded"
                exclusion_category = exclusion["category"]
                exclusion_reason = exclusion["reason"]
            records.append(
                CoverageRecord(
                    source_path=relative.as_posix(),
                    url_path=path_to_url(relative),
                    coverage=coverage,
                    profile_source="—",
                    exclusion_category=exclusion_category,
                    exclusion_reason=exclusion_reason,
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
                exclusion_category="—",
                exclusion_reason="—",
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
    """Collect shared-shell governance and fail on any unclassified public HTML."""
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

    exclusions, exclusion_findings = validate_exclusion_registry(
        root,
        public_paths,
        set(profiles),
        SHARED_SHELL_EXCLUSIONS,
    )
    findings.extend(exclusion_findings)

    records = classify_records(public_paths, profiles, family_by_path, exclusions)
    if not records:
        findings.append("No public HTML pages were collected for shared shell coverage")

    unknown_family = [record.source_path for record in records if record.profile_source == "family:unknown"]
    if unknown_family:
        findings.append(
            "Family-backed pages are missing a declarative family source: "
            + ", ".join(unknown_family)
        )

    unclassified = [record.source_path for record in records if record.coverage == "unclassified"]
    if unclassified:
        findings.append(
            "Unclassified public HTML pages must have a shared shell profile or reviewed exclusion: "
            + ", ".join(unclassified)
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


def markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def markdown_text(records: list[CoverageRecord]) -> str:
    profiled = [record for record in records if record.coverage == "profiled"]
    excluded = [record for record in records if record.coverage == "excluded"]
    unclassified = [record for record in records if record.coverage == "unclassified"]
    source_counts = Counter(record.profile_source for record in profiled)
    shell_percent = (len(profiled) / len(records) * 100) if records else 0.0
    governed_percent = ((len(profiled) + len(excluded)) / len(records) * 100) if records else 0.0

    lines = [
        "# Покрытие shared shell",
        "",
        "Файл генерируется командой `python tools/build_shared_shell_coverage.py --output-dir reports/shared-shell-coverage`.",
        "Отчёт разделяет публичные HTML-страницы на профилированные, проверенные исключения и непросмотренные страницы без контракта.",
        "",
        "## Сводка",
        "",
        f"- публичных HTML-страниц: {len(records)};",
        f"- страниц с профилем shared shell: {len(profiled)};",
        f"- проверенных исключений: {len(excluded)};",
        f"- непросмотренных страниц: {len(unclassified)};",
        f"- покрытие shared shell: {shell_percent:.1f}%;",
        f"- управляемое покрытие: {governed_percent:.1f}%.",
        "",
        "Проверенное исключение имеет точную категорию, причину и мета-контракт. Любая новая публичная HTML-страница без профиля или записи в реестре считается `unclassified` и блокирует quality gate.",
        "",
        "## Источники профилей",
        "",
        "| Источник | Страниц |",
        "|---|---:|",
    ]
    for source, count in sorted(source_counts.items()):
        lines.append(f"| `{source}` | {count} |")
    lines.append(f"| проверенные исключения | {len(excluded)} |")
    lines.append(f"| непросмотренные страницы | {len(unclassified)} |")

    lines.extend(["", "## Проверенные исключения", ""])
    if excluded:
        lines.extend(["| URL | Исходный файл | Категория | Причина |", "|---|---|---|---|"])
        for record in excluded:
            lines.append(
                f"| `{record.url_path}` | `{record.source_path}` | "
                f"`{record.exclusion_category}` | {markdown_cell(record.exclusion_reason)} |"
            )
    else:
        lines.append("Проверенных исключений нет.")

    lines.extend(["", "## Непросмотренные страницы", ""])
    if unclassified:
        lines.extend(["| URL | Исходный файл |", "|---|---|"])
        for record in unclassified:
            lines.append(f"| `{record.url_path}` | `{record.source_path}` |")
    else:
        lines.append("Непросмотренных публичных HTML-страниц нет.")

    lines.extend(
        [
            "",
            "## Полные данные",
            "",
            "Artifact `shared-shell-coverage` содержит:",
            "",
            "- `shared-shell-coverage.csv` — классификацию каждой публичной HTML-страницы, включая категорию и причину исключения;",
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


def sample_html(canonical: str, refresh: str | None = None, marker: str = "") -> str:
    refresh_meta = f'<meta http-equiv="refresh" content="4;url={refresh}">' if refresh else ""
    return (
        '<!doctype html><html><head><meta name="robots" content="noindex, follow">'
        f'<link rel="canonical" href="{canonical}">{refresh_meta}</head>'
        f'<body>{marker}</body></html>'
    )


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
        {
            Path("404.html"): {
                "category": "error",
                "reason": "Reviewed error document",
            }
        },
    )
    by_path = {record.source_path: record for record in records}
    if by_path["index.html"].profile_source != "explicit":
        findings.append("self-test: explicit profile classification failed")
    if by_path["sovety/example/index.html"].profile_source != "family:articles":
        findings.append("self-test: glob family profile classification failed")
    if by_path["uslugi/example/index.html"].profile_source != "family:adjacent-services":
        findings.append("self-test: allowlist family profile classification failed")
    if by_path["404.html"].coverage != "excluded":
        findings.append("self-test: reviewed-exclusion classification failed")
    if by_path["politika/index.html"].coverage != "unclassified":
        findings.append("self-test: unclassified-page classification failed")
    if by_path["404.html"].url_path != "/404.html":
        findings.append("self-test: file URL conversion failed")
    if by_path["sovety/example/index.html"].url_path != "/sovety/example/":
        findings.append("self-test: index URL conversion failed")

    with TemporaryDirectory(prefix="parket-shell-exclusion-test-") as temporary:
        root = Path(temporary)
        error_page = Path("404.html")
        redirect_page = Path("uslugi/legacy/index.html")
        (root / error_page).write_text(
            sample_html("https://parket36.ru/404.html"),
            encoding="utf-8",
        )
        (root / redirect_page).parent.mkdir(parents=True)
        (root / redirect_page).write_text(
            sample_html(
                "https://parket36.ru/uslugi/current/",
                refresh="/uslugi/current/",
            ),
            encoding="utf-8",
        )
        valid_entry = {
            "path": error_page,
            "category": "error",
            "reason": "Reviewed error document",
            "required_robots": "noindex, follow",
            "required_canonical": "https://parket36.ru/404.html",
        }
        redirect_entry = {
            "path": redirect_page,
            "category": "redirect",
            "reason": "Reviewed legacy redirect",
            "required_robots": "noindex, follow",
            "required_canonical": "https://parket36.ru/uslugi/current/",
            "required_refresh_target": "/uslugi/current/",
        }
        _, valid_findings = validate_exclusion_registry(
            root,
            [error_page, redirect_page],
            set(),
            (valid_entry, redirect_entry),
        )
        if valid_findings:
            findings.append("self-test: valid exclusion registry was rejected: " + "; ".join(valid_findings))

        _, duplicate_findings = validate_exclusion_registry(
            root,
            [error_page],
            set(),
            (valid_entry, valid_entry),
        )
        if not any("Duplicate shared shell exclusion path" in item for item in duplicate_findings):
            findings.append("self-test: duplicate exclusion path was not rejected")

        stale_entry = dict(valid_entry)
        stale_entry["path"] = Path("missing/index.html")
        _, stale_findings = validate_exclusion_registry(root, [error_page], set(), (stale_entry,))
        if not any("non-public or missing" in item for item in stale_findings):
            findings.append("self-test: stale exclusion was not rejected")

        _, overlap_findings = validate_exclusion_registry(
            root,
            [error_page],
            {error_page},
            (valid_entry,),
        )
        if not any("overlaps" in item for item in overlap_findings):
            findings.append("self-test: profile/exclusion overlap was not rejected")

        broken_redirect = dict(redirect_entry)
        broken_redirect["required_refresh_target"] = "/wrong/"
        _, redirect_findings = validate_exclusion_registry(
            root,
            [redirect_page],
            set(),
            (broken_redirect,),
        )
        if not any("meta refresh target" in item for item in redirect_findings):
            findings.append("self-test: redirect target drift was not rejected")

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
