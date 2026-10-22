"""Shared boundaries between website sources and generated QA output."""

QA_OUTPUT_DIRS = frozenset({
    "test-results", "playwright-report", "lighthouse-report", ".lighthouseci",
})
