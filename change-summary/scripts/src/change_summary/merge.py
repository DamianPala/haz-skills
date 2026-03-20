"""Merge per-chunk changes YAML files into a single changes.yaml."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


def merge_chunks(workdir: Path) -> Path:
    """Merge all changes-chunk-*.yaml files into changes.yaml.

    1. Parse each chunk YAML (full parse, fallback to changes-only if skipped is malformed)
    2. Concatenate changes and skipped lists
    3. Deduplicate, sort by date, compute bump
    4. Write merged changes.yaml

    Returns path to the merged file.
    """
    chunk_files = sorted(workdir.glob("changes-chunk-*.yaml"))
    orphan_files = sorted(workdir.glob("orphan-changes-chunk-*.yaml"))
    all_yaml_files = chunk_files + orphan_files
    if not chunk_files:
        raise FileNotFoundError(f"No changes-chunk-*.yaml files found in {workdir}")

    all_changes: list[dict] = []
    all_skipped: list[dict] = []
    headers: dict[str, str] = {}

    for chunk_file in all_yaml_files:
        raw_text = chunk_file.read_text(encoding="utf-8")
        data = _parse_chunk_yaml(raw_text)

        changes = data.get("changes", [])
        if isinstance(changes, list):
            all_changes.extend(changes)

        skipped = data.get("skipped", [])
        if isinstance(skipped, list):
            for item in skipped:
                if isinstance(item, dict) and item not in all_skipped:
                    all_skipped.append(item)

        if not headers:
            headers = _extract_headers(raw_text)

    all_changes = _deduplicate(all_changes)
    all_changes = _sort_by_significance(all_changes)
    bump = _compute_bump(all_changes)

    output = _build_output(all_changes, all_skipped, headers, bump)
    out_path = workdir / "changes.yaml"
    out_path.write_text(output, encoding="utf-8")
    return out_path


def _parse_chunk_yaml(raw_text: str) -> dict:
    """Parse a chunk YAML file, with fallback for malformed skipped sections.

    Tries full parse first. If that fails (usually due to free-form skipped text),
    parses only the changes: block and skips the skipped section.
    """
    try:
        data = yaml.safe_load(raw_text)
        if isinstance(data, dict):
            return data
    except yaml.YAMLError:
        pass

    # Fallback: parse only the changes: block
    lines = raw_text.splitlines(keepends=True)
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

    changes_text = "".join(lines[start:end])
    try:
        data = yaml.safe_load(changes_text)
        if isinstance(data, dict):
            print(
                "warning: skipped section malformed, parsed changes only",
                file=sys.stderr,
            )
            return data
    except yaml.YAMLError:
        pass

    return {}


def _extract_headers(raw_text: str) -> dict[str, str]:
    """Extract header comments from YAML text."""
    headers: dict[str, str] = {}
    for line in raw_text.splitlines():
        if not line.startswith("#"):
            break
        if ":" in line:
            key, _, value = line.lstrip("# ").partition(":")
            headers[key.strip().lower()] = value.strip()
    return headers


def _deduplicate(changes: list[dict]) -> list[dict]:
    """Remove duplicate entries: same commit hash + overlapping files."""
    seen: dict[str, dict] = {}
    result: list[dict] = []

    for change in changes:
        commits = change.get("commits", [])
        primary = commits[0] if commits else ""
        files = set(change.get("files", []))
        desc = change.get("description", "")

        if not primary:
            result.append(change)
            continue

        key = f"{primary}:{desc[:50]}"

        if key in seen:
            existing = seen[key]
            existing_files = set(existing.get("files", []))
            if files & existing_files or desc == existing.get("description", ""):
                if len(change.get("detail", "")) > len(existing.get("detail", "")):
                    seen[key] = change
                    result = [c for c in result if c is not existing]
                    result.append(change)
                continue

        seen[key] = change
        result.append(change)

    return result


_TYPE_SIGNIFICANCE = {
    "feat": 0,
    "fix": 1,
    "refactor": 2,
    "perf": 3,
    "test": 4,
    "ci": 5,
    "build": 6,
    "docs": 7,
    "chore": 8,
    "style": 9,
    "revert": 10,
}


def _sort_by_significance(changes: list[dict]) -> list[dict]:
    """Sort changes by type significance: features and fixes first, then test/ci/docs/chore."""

    def sort_key(change: dict) -> tuple[bool, int, str]:
        # Breaking changes first
        is_breaking = not change.get("breaking", False)
        type_order = _TYPE_SIGNIFICANCE.get(change.get("type", "chore"), 99)
        description = change.get("description", "")
        return (is_breaking, type_order, description)

    return sorted(changes, key=sort_key)


def _compute_bump(changes: list[dict]) -> str:
    """Compute suggested version bump from change types."""
    if any(c.get("breaking", False) for c in changes):
        return "major"
    if any(c.get("type") == "feat" for c in changes):
        return "minor"
    return "patch"


def _build_output(
    changes: list[dict],
    skipped: list[dict],
    headers: dict[str, str],
    bump: str,
) -> str:
    """Build the final YAML output string."""
    range_str = headers.get("change summary", "unknown")
    project = headers.get("project", "unknown")

    header_lines = [
        f"# Change Summary: {range_str}",
        f"# Project: {project}",
        f"# Suggested bump: {bump}",
        "",
    ]

    data: dict = {"changes": changes}
    if skipped:
        data["skipped"] = skipped

    yaml_body = yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=100,
    )

    return "\n".join(header_lines) + yaml_body
