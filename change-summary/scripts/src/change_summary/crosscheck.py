"""Cross-check changes YAML entries against diff files by file coverage.

Deterministic verification: checks that YAML file lists match the actual
diff file headers without needing an LLM.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml


def crosscheck_file_coverage(workdir: Path) -> list[Path]:
    """Cross-check YAML entries against diff files using file coverage.

    For each diff-N.txt, extracts file paths from `## File:` headers.
    For each changes-chunk-N.yaml, extracts file paths from entries.
    Reports files in diff but not in any YAML entry (MISSING_FILE)
    and files in YAML but not in diff (EXTRA_FILE).

    Returns list of report file paths.
    """
    reports: list[Path] = []

    diff_files = sorted(workdir.glob("diff-*.txt"))
    for chunk_file in diff_files:
        n = re.search(r"diff-(\d+)\.txt", chunk_file.name)
        if not n:
            continue
        chunk_num = n.group(1)
        yaml_file = workdir / f"changes-chunk-{chunk_num}.yaml"
        report_file = workdir / f"cross-check-chunk-{chunk_num}.txt"

        if not yaml_file.is_file():
            report_file.write_text(f"MISSING_YAML: {yaml_file.name} not found\n", encoding="utf-8")
            reports.append(report_file)
            continue

        report = _crosscheck_file_pair(chunk_file, yaml_file, report_file)
        reports.append(report)

    return reports


def _crosscheck_file_pair(chunk_path: Path, yaml_path: Path, report_path: Path) -> Path:
    """Cross-check a single diff+yaml pair by file coverage."""
    chunk_text = chunk_path.read_text(encoding="utf-8")
    yaml_text = yaml_path.read_text(encoding="utf-8")

    # Extract file paths from diff
    diff_files = set(re.findall(r"^## File: '([^']+)'", chunk_text, re.MULTILINE))

    # Parse YAML
    data = _parse_yaml(yaml_text)
    changes = data.get("changes", [])
    if not isinstance(changes, list):
        report_path.write_text("YAML_ERROR: changes is not a list\n", encoding="utf-8")
        return report_path

    # Collect all files referenced in YAML entries
    yaml_files: set[str] = set()
    for change in changes:
        files = change.get("files", [])
        if isinstance(files, list):
            yaml_files.update(files)

    # Check coverage
    issues: list[str] = []

    missing = diff_files - yaml_files
    for f in sorted(missing):
        issues.append(f"MISSING_FILE: '{f}' is in diff but not covered by any YAML entry")

    extra = yaml_files - diff_files
    for f in sorted(extra):
        issues.append(f"EXTRA_FILE: '{f}' is in YAML but not in this chunk's diff")

    if issues:
        report_path.write_text("\n".join(issues) + "\n", encoding="utf-8")
    else:
        report_path.write_text("PASS\n", encoding="utf-8")

    return report_path


def _parse_yaml(text: str) -> dict:
    """Parse YAML with fallback for malformed skipped sections."""
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict):
            return data
    except yaml.YAMLError:
        pass

    # Fallback: changes only
    lines = text.splitlines(keepends=True)
    start = None
    end = len(lines)
    for i, line in enumerate(lines):
        if line.startswith("changes:"):
            start = i
        elif start is not None and line.startswith("skipped:"):
            end = i
            break
    if start is None:
        return {}
    try:
        data = yaml.safe_load("".join(lines[start:end]))
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}
