#!/usr/bin/env python3
"""Regression: rerunning quality after browser tests must not audit trace HTML."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import build_content_inventory
import build_pages
import check_breadcrumbs_token_migration
import check_empty_link_attributes
import check_guardrails
import check_process_step_token_migration
import check_site
import check_structured_data
import site_settings
from source_tree import QA_OUTPUT_DIRS


def main():
    readers = [
        (build_content_inventory, "iter_public_html"),
        (build_pages, "iter_source_html"),
        (check_breadcrumbs_token_migration, "public_html_files"),
        (check_empty_link_attributes, "html_files"),
        (check_guardrails, "html_files"),
        (check_process_step_token_migration, "public_html_files"),
        (check_site, "iter_html_files"),
        (check_structured_data, "iter_public_html"),
    ]
    with TemporaryDirectory(prefix="parket-source-tree-") as directory:
        root = Path(directory)
        expected = {root / "index.html", root / "uslugi" / "index.html"}
        for file in expected:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("<h1>Public source</h1>")
        for name in QA_OUTPUT_DIRS:
            for relative in [Path(name) / "index.html", Path(name) / "traces/resources/copy.html"]:
                file = root / relative
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('<h1>Duplicate saved browser HTML</h1><a href="">Trace only</a>')
        for module, method in readers:
            with patch.object(module, "ROOT", root):
                found = set(getattr(module, method)())
            if found != expected:
                raise AssertionError(f"{module.__name__}.{method}: QA output leaked into sources: {found ^ expected}")
        if set(site_settings.iter_markup_files(root)) != expected:
            raise AssertionError("site_settings must not read or rewrite generated QA HTML")
    print("Source tree regression passed: QA reports excluded by nine source readers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
