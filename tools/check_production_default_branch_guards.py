#!/usr/bin/env python3
"""Validate fail-closed default-branch guards for production workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
GUARD = "if: github.ref_name == github.event.repository.default_branch"
EXACT_GUARD_LINE = f"    {GUARD}"
DOC = ROOT / "docs" / "production-default-branch-guards.md"


@dataclass(frozen=True)
class WorkflowSpec:
    path: Path
    protected_job: str
    next_job: str | None = None
    dependent_job: str | None = None


WORKFLOWS = (
    WorkflowSpec(
        ROOT / ".github" / "workflows" / "production-lead-launch-readiness.yml",
        "readiness",
    ),
    WorkflowSpec(
        ROOT / ".github" / "workflows" / "deploy-lead-function.yml",
        "validate",
        next_job="deploy",
        dependent_job="deploy",
    ),
    WorkflowSpec(
        ROOT / ".github" / "workflows" / "controlled-lead-smoke.yml",
        "validate",
        next_job="smoke",
        dependent_job="smoke",
    ),
    WorkflowSpec(
        ROOT / ".github" / "workflows" / "lead-endpoint-health.yml",
        "health",
    ),
)

DOC_MARKERS = (
    "# Защита production workflow основной веткой",
    "github.ref_name == github.event.repository.default_branch",
    "production-lead-launch-readiness.yml",
    "deploy-lead-function.yml",
    "controlled-lead-smoke.yml",
    "lead-endpoint-health.yml",
    "skipped",
    "needs: validate",
    "checkout",
    "production secrets",
)


def job_marker(name: str) -> str:
    return f"\n  {name}:\n"


def extract_job(text: str, name: str, next_name: str | None = None) -> str:
    start_marker = job_marker(name)
    start = text.find(start_marker)
    if start < 0:
        return ""
    start += len(start_marker)

    if next_name is None:
        return text[start:]

    end = text.find(job_marker(next_name), start)
    if end < 0:
        return ""
    return text[start:end]


def validate_workflow_text(text: str, spec: WorkflowSpec, label: str) -> list[str]:
    findings: list[str] = []

    if "workflow_dispatch:" not in text:
        findings.append(f"{label}: workflow_dispatch trigger is missing")

    guard_count = text.count(EXACT_GUARD_LINE)
    if guard_count != 1:
        findings.append(
            f"{label}: expected exactly one job-level default-branch guard, found {guard_count}"
        )

    protected = extract_job(text, spec.protected_job, spec.next_job)
    if not protected:
        findings.append(f"{label}: protected job `{spec.protected_job}` is missing or malformed")
        return findings

    guard_position = protected.find(EXACT_GUARD_LINE.strip())
    runs_on_position = protected.find("runs-on:")
    first_execution_position = min(
        position
        for position in (protected.find("env:"), protected.find("steps:"))
        if position >= 0
    ) if ("env:" in protected or "steps:" in protected) else -1

    if guard_position < 0:
        findings.append(
            f"{label}: job `{spec.protected_job}` is missing the default-branch guard"
        )
    if runs_on_position < 0:
        findings.append(f"{label}: job `{spec.protected_job}` is missing runs-on")
    elif guard_position >= 0 and guard_position > runs_on_position:
        findings.append(
            f"{label}: default-branch guard must appear before runs-on in `{spec.protected_job}`"
        )
    if first_execution_position < 0:
        findings.append(f"{label}: job `{spec.protected_job}` has no env or steps block")
    elif guard_position >= 0 and guard_position > first_execution_position:
        findings.append(
            f"{label}: default-branch guard must appear before env/steps in `{spec.protected_job}`"
        )

    if spec.dependent_job:
        dependent = extract_job(text, spec.dependent_job)
        if not dependent:
            findings.append(f"{label}: dependent job `{spec.dependent_job}` is missing")
        elif "needs: validate" not in dependent:
            findings.append(
                f"{label}: dependent job `{spec.dependent_job}` must require `needs: validate`"
            )

    return findings


def run_self_test() -> int:
    spec = WorkflowSpec(Path("sample.yml"), "validate", "deploy", "deploy")
    valid = f"""
name: sample
on:
  workflow_dispatch:
jobs:
  validate:
    name: validate
    {GUARD}
    runs-on: ubuntu-latest
    env:
      MODE: test
    steps:
      - run: echo ok
  deploy:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - run: echo deploy
"""
    if validate_workflow_text(valid, spec, "valid"):
        print("valid fixture was rejected")
        return 1

    without_guard = valid.replace(f"    {GUARD}\n", "")
    if not validate_workflow_text(without_guard, spec, "without guard"):
        print("missing guard fixture was accepted")
        return 1

    late_guard = valid.replace(
        f"    {GUARD}\n    runs-on: ubuntu-latest",
        f"    runs-on: ubuntu-latest\n    {GUARD}",
    )
    if not validate_workflow_text(late_guard, spec, "late guard"):
        print("late guard fixture was accepted")
        return 1

    without_dependency = valid.replace("    needs: validate\n", "")
    if not validate_workflow_text(without_dependency, spec, "without dependency"):
        print("missing dependency fixture was accepted")
        return 1

    print("Production default-branch guard self-test passed")
    return 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return run_self_test()

    findings: list[str] = []

    for spec in WORKFLOWS:
        label = str(spec.path.relative_to(ROOT))
        if not spec.path.is_file():
            findings.append(f"missing workflow: {label}")
            continue
        text = spec.path.read_text(encoding="utf-8", errors="ignore")
        findings.extend(validate_workflow_text(text, spec, label))

    if not DOC.is_file():
        findings.append(f"missing documentation: {DOC.relative_to(ROOT)}")
    else:
        doc_text = DOC.read_text(encoding="utf-8", errors="ignore")
        for marker in DOC_MARKERS:
            if marker not in doc_text:
                findings.append(
                    f"{DOC.relative_to(ROOT)}: missing documentation marker: {marker}"
                )

    if findings:
        print("Production default-branch guard findings:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Production default-branch guards passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
