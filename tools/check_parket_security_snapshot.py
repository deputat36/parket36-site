#!/usr/bin/env python3
"""Validate that the reusable Parket36 production security snapshot stays read-only."""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / "supabase" / "verify-parket-security.sql"
DOC_PATH = ROOT / "docs" / "supabase-production-security-status-2026-08-03.md"
RUNNER_PATH = ROOT / "tools" / "run_quality_checks.py"
QUALITY_CHECKER_PATH = ROOT / "tools" / "check_quality_runner.py"
OPERATIONS_INDEX_PATH = ROOT / "docs" / "operations-index.md"

REQUIRED_SQL_MARKERS = (
    "parket_leads",
    "parket_public_lead_audit",
    "pg_policies",
    "information_schema.role_table_grants",
    "pg_stat_user_indexes",
    "parket_retention_preview",
    "parket_apply_retention",
    "'anon'",
    "'authenticated'",
    "'service_role'",
)

FORBIDDEN_STATEMENTS = (
    "insert",
    "update",
    "delete",
    "merge",
    "alter",
    "drop",
    "truncate",
    "create",
    "grant",
    "revoke",
    "call",
    "do",
    "copy",
    "vacuum",
    "analyze",
    "refresh",
    "reindex",
    "cluster",
    "listen",
    "notify",
    "unlisten",
)

FORBIDDEN_CAPABILITIES = (
    "functions/v1",
    "http_post",
    "http_get",
    "net.http",
    "pg_net",
    "dblink",
    "pg_sleep",
    "lo_import",
    "lo_export",
    "program",
)

REQUIRED_DOC_MARKERS = (
    "Проверка выполнялась только чтением",
    "включён RLS",
    "deny-all policy",
    "0 строк",
    "Edge Function `parket-public-lead`",
    "supabase/verify-parket-security.sql",
)


def strip_comments(sql: str) -> str:
    without_blocks = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return re.sub(r"--[^\n]*", " ", without_blocks)


def validate_sql_text(sql: str) -> list[str]:
    findings: list[str] = []
    executable = strip_comments(sql).strip()
    normalized = executable.lower()

    if not normalized.startswith(("with ", "select ")):
        findings.append("security snapshot must begin with WITH or SELECT")

    semicolons = executable.count(";")
    if semicolons != 1 or not executable.endswith(";"):
        findings.append("security snapshot must contain exactly one terminated SQL statement")

    for marker in REQUIRED_SQL_MARKERS:
        if marker not in sql:
            findings.append(f"security snapshot is missing required marker: {marker}")

    for statement in FORBIDDEN_STATEMENTS:
        if re.search(rf"\b{re.escape(statement)}\b", normalized):
            findings.append(f"security snapshot contains forbidden statement: {statement.upper()}")

    for capability in FORBIDDEN_CAPABILITIES:
        if capability in normalized:
            findings.append(f"security snapshot contains forbidden capability: {capability}")

    direct_data_patterns = (
        r"\bfrom\s+(?:public\.)?parket_leads\b",
        r"\bjoin\s+(?:public\.)?parket_leads\b",
        r"\bfrom\s+(?:public\.)?parket_public_lead_audit\b",
        r"\bjoin\s+(?:public\.)?parket_public_lead_audit\b",
    )
    for pattern in direct_data_patterns:
        if re.search(pattern, normalized):
            findings.append("security snapshot must inspect metadata, not read lead row contents")
            break

    return findings


def self_test() -> list[str]:
    failures: list[str] = []
    safe = """
    with snapshot as (
      select 'parket_leads' as table_name,
             'parket_public_lead_audit' as audit_name,
             'pg_policies' as policies,
             'information_schema.role_table_grants' as grants,
             'pg_stat_user_indexes' as indexes,
             'parket_retention_preview' as preview,
             'parket_apply_retention' as apply_name,
             'anon' as anon_role,
             'authenticated' as authenticated_role,
             'service_role' as service_role
    )
    select * from snapshot;
    """
    if validate_sql_text(safe):
        failures.append("safe SELECT-only fixture was rejected")

    unsafe_cases = {
        "insert": safe.replace("select * from snapshot;", "insert into example values (1);"),
        "delete": safe.replace("select * from snapshot;", "delete from example;"),
        "edge request": safe.replace("select * from snapshot;", "select 'functions/v1/parket-public-lead';"),
        "direct lead read": safe.replace("select * from snapshot;", "select * from public.parket_leads;"),
    }
    for label, candidate in unsafe_cases.items():
        if not validate_sql_text(candidate):
            failures.append(f"unsafe fixture was accepted: {label}")

    return failures


def main() -> int:
    findings = self_test()

    required_files = (
        SQL_PATH,
        DOC_PATH,
        RUNNER_PATH,
        QUALITY_CHECKER_PATH,
        OPERATIONS_INDEX_PATH,
    )
    for path in required_files:
        if not path.is_file():
            findings.append(f"missing required file: {path.relative_to(ROOT)}")

    if SQL_PATH.is_file():
        findings.extend(validate_sql_text(SQL_PATH.read_text(encoding="utf-8")))

    if DOC_PATH.is_file():
        doc = DOC_PATH.read_text(encoding="utf-8")
        for marker in REQUIRED_DOC_MARKERS:
            if marker not in doc:
                findings.append(f"production security document is missing marker: {marker}")

    runner_marker = '("Validate Parket production security snapshot", ["tools/check_parket_security_snapshot.py"])'
    if RUNNER_PATH.is_file() and runner_marker not in RUNNER_PATH.read_text(encoding="utf-8"):
        findings.append("production security snapshot check is missing from the quality runner")

    expected_marker = '["tools/check_parket_security_snapshot.py"]'
    if QUALITY_CHECKER_PATH.is_file() and expected_marker not in QUALITY_CHECKER_PATH.read_text(encoding="utf-8"):
        findings.append("production security snapshot check is missing from approved quality composition")

    if OPERATIONS_INDEX_PATH.is_file():
        operations = OPERATIONS_INDEX_PATH.read_text(encoding="utf-8")
        for marker in (
            "docs/supabase-production-security-status-2026-08-03.md",
            "supabase/verify-parket-security.sql",
        ):
            if marker not in operations:
                findings.append(f"operations index is missing security snapshot reference: {marker}")

    if findings:
        print("Parket production security snapshot findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Parket production security snapshot check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
