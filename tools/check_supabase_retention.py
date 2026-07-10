#!/usr/bin/env python3
"""Validate safe, explicit retention helpers for Parket36 lead data."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / "supabase" / "sql" / "parket_lead_retention.sql"

REQUIRED_MARKERS = {
    "create or replace function public.parket_retention_preview(": "read-only preview function",
    "create or replace function public.parket_apply_retention(": "explicit cleanup function",
    "retention cutoffs are required": "required cutoff validation",
    "retention cutoffs must be in the past": "past cutoff validation",
    "at least one completed lead status is required": "explicit status selection",
    "only done, spam and archived leads may be removed": "completed-status allowlist",
    "status = any(p_lead_statuses)": "status-scoped deletion",
    "delete from public.parket_public_lead_audit": "audit cleanup",
    "delete from public.parket_leads": "lead cleanup",
    "security definer": "controlled service execution",
    "set search_path = public, pg_temp": "fixed function search path",
    "revoke all on function public.parket_retention_preview": "preview public revoke",
    "revoke all on function public.parket_apply_retention": "cleanup public revoke",
    "grant execute on function public.parket_retention_preview": "preview service role grant",
    "grant execute on function public.parket_apply_retention": "cleanup service role grant",
    "not scheduled automatically": "no automatic destructive schedule statement",
}

FORBIDDEN_MARKERS = {
    "pg_cron": "automatic database schedule",
    "cron.schedule": "automatic retention schedule",
    "status in ('new'": "new lead deletion",
    "status in ('in_progress'": "in-progress lead deletion",
    "to anon": "anonymous function grant",
    "to authenticated": "authenticated function grant",
}


def main() -> int:
    if not SQL_PATH.exists():
        print(f"Retention SQL is missing: {SQL_PATH.relative_to(ROOT)}")
        return 1

    text = SQL_PATH.read_text(encoding="utf-8").lower()
    findings: list[str] = []

    for marker, label in REQUIRED_MARKERS.items():
        if marker.lower() not in text:
            findings.append(f"missing {label}: {marker}")

    for marker, label in FORBIDDEN_MARKERS.items():
        if marker.lower() in text:
            findings.append(f"forbidden {label}: {marker}")

    preview_position = text.find("create or replace function public.parket_retention_preview(")
    apply_position = text.find("create or replace function public.parket_apply_retention(")
    first_delete = text.find("delete from public.")
    if preview_position == -1 or apply_position == -1 or first_delete == -1:
        findings.append("cannot verify preview-before-delete order")
    elif not (preview_position < apply_position < first_delete):
        findings.append("preview function must appear before the destructive cleanup body")

    if findings:
        print("Supabase retention findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Supabase retention check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
