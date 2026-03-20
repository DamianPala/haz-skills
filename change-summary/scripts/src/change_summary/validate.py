"""Validate and auto-fix LLM-generated changes YAML files.

Two stages:
1. Fix: repair common YAML issues, fill defaults
2. Validate: check required fields and constraints

Safety: entry count is compared before/after fix. If entries were lost,
the original is preserved and an error is reported.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

# Valid values for type and category fields
VALID_TYPES = {
    "feat",
    "fix",
    "refactor",
    "perf",
    "docs",
    "chore",
    "revert",
    "style",
    "test",
    "ci",
    "build",
}
TYPE_TO_CATEGORY = {
    "feat": "Added",
    "fix": "Fixed",
    "refactor": "Changed",
    "perf": "Changed",
    "revert": "Removed",
    "docs": "Changed",
    "chore": "Changed",
    "style": "Changed",
    "test": "Changed",
    "ci": "Changed",
    "build": "Changed",
}
VALID_CATEGORIES = {"Added", "Changed", "Fixed", "Removed", "Deprecated", "Security"}
REQUIRED_FIELDS = {"type", "description"}


def validate_and_fix(path: Path) -> list[str]:
    """Validate and auto-fix a changes YAML file in place.

    Returns list of issues (empty = all good).
    Writes fixed file back only if fixes were applied and entry count is preserved.
    """
    raw_text = path.read_text(encoding="utf-8")

    # Stage 1: Fix YAML syntax
    fixed_text = _fix_yaml_syntax(raw_text)

    # Parse (full first, fallback to changes-only if skipped section is malformed)
    data = _safe_parse(fixed_text)
    if data is None:
        data = _parse_changes_only(fixed_text)
        if data is None:
            return [f"YAML parse failed for {path.name}, even after syntax fix"]

    changes = data.get("changes", [])
    if not isinstance(changes, list):
        return [f"'changes' is not a list in {path.name}"]

    # Count entries before fixes
    count_before = len(changes)

    # Stage 1b: Fix field defaults
    for change in changes:
        _fix_defaults(change)

    # Safety check: did we lose entries?
    count_after = len(changes)
    if count_after < count_before:
        return [f"SAFETY: entry count dropped from {count_before} to {count_after}, not saving"]

    # Write fixed version back
    _write_back(path, raw_text, data)

    # Stage 2: Validate
    issues = _validate_entries(changes, path.name)
    return issues


def _fix_yaml_syntax(text: str) -> str:
    """Fix common YAML syntax issues from LLM output."""
    lines = text.splitlines(keepends=True)
    fixed: list[str] = []

    for line in lines:
        # Fix trailing whitespace
        line = line.rstrip() + "\n" if line.endswith("\n") else line.rstrip()
        fixed.append(line)

    return "".join(fixed)


def _fix_defaults(change: dict) -> None:
    """Fill missing optional fields with sensible defaults."""
    # Normalize commit → commits (backward compat: accept both, output list)
    if "commit" in change and "commits" not in change:
        raw = change.pop("commit")
        if isinstance(raw, list):
            change["commits"] = [str(h) for h in raw]
        else:
            change["commits"] = [str(raw)]
    elif "commits" in change:
        change.pop("commit", None)
        if not isinstance(change["commits"], list):
            change["commits"] = [str(change["commits"])]
        else:
            change["commits"] = [str(h) for h in change["commits"]]

    # Default confidence
    if "confidence" not in change:
        change["confidence"] = "medium"

    # Always set category from type (Python is authoritative, LLM may output wrong value)
    if "type" in change:
        change_type = change["type"]
        if change.get("breaking"):
            change["category"] = "Changed"
        else:
            change["category"] = TYPE_TO_CATEGORY.get(change_type, "Changed")

    # Ensure files is a list
    if "files" not in change:
        change["files"] = []
    elif isinstance(change["files"], str):
        change["files"] = [change["files"]]

    # Note required when confidence < high
    if change.get("confidence") in ("medium", "low") and "note" not in change:
        change["note"] = "confidence below high, no explanation provided by interpreter"


def _validate_entries(changes: list[dict], filename: str) -> list[str]:
    """Validate all entries against schema rules."""
    issues: list[str] = []

    for i, change in enumerate(changes):
        prefix = f"{filename} item {i + 1}"
        commits = change.get("commits", [])
        commit_label = commits[0] if commits else "???"

        # Required fields
        for field in REQUIRED_FIELDS:
            if field not in change or not change[field]:
                issues.append(f"{prefix} ({commit_label}): missing required field '{field}'")

        # Valid type
        if change.get("type") and change["type"] not in VALID_TYPES:
            issues.append(f"{prefix} ({commit_label}): invalid type '{change['type']}'")

        # Valid category
        if change.get("category") and change["category"] not in VALID_CATEGORIES:
            issues.append(f"{prefix} ({commit_label}): invalid category '{change['category']}'")

        # Breaking must have migration
        if change.get("breaking") and not change.get("migration"):
            issues.append(f"{prefix} ({commit_label}): breaking=true but no migration field")

        # Files should be a list
        if "files" in change and not isinstance(change["files"], list):
            issues.append(f"{prefix} ({commit_label}): files is not a list")

        # Commits should be a list of strings
        if "commits" in change and not isinstance(change["commits"], list):
            issues.append(f"{prefix} ({commit_label}): commits is not a list")

    return issues


def _parse_changes_only(text: str) -> dict | None:
    """Parse only the changes: block, ignoring malformed skipped section."""
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
        return None

    changes_text = "".join(lines[start:end])
    try:
        data = yaml.safe_load(changes_text)
        return data if isinstance(data, dict) else None
    except yaml.YAMLError:
        return None


def _safe_parse(text: str) -> dict | None:
    """Parse YAML, returning None on failure."""
    try:
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else None
    except yaml.YAMLError:
        return None


def _write_back(path: Path, original_text: str, data: dict) -> None:
    """Write fixed data back to file, preserving header comments."""
    # Extract header comments from original
    header_lines: list[str] = []
    for line in original_text.splitlines():
        if line.startswith("#"):
            header_lines.append(line)
        else:
            break

    yaml_body = yaml.dump(
        data,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=100,
    )

    output = "\n".join(header_lines) + "\n\n" + yaml_body if header_lines else yaml_body
    path.write_text(output, encoding="utf-8")


def validate_file(path: Path) -> None:
    """CLI entry point: validate and fix a single file, print results."""
    if not path.is_file():
        print(f"error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    issues = validate_and_fix(path)
    if issues:
        for issue in issues:
            print(f"  {issue}", file=sys.stderr)
        print(f"{len(issues)} issue(s) found in {path.name}", file=sys.stderr)
    else:
        print(f"{path.name}: OK", file=sys.stderr)


def validate_workdir(workdir: Path) -> None:
    """CLI entry point: validate all YAMLs in workdir + run cross-check.

    Finds changes.yaml or changes-chunk-N.yaml, validates each,
    then runs cross-check against diff files.
    """
    from change_summary.crosscheck import crosscheck_file_coverage

    # Find YAML files
    yamls = sorted(workdir.glob("changes-chunk-*.yaml"))
    if not yamls:
        single = workdir / "changes.yaml"
        if single.is_file():
            yamls = [single]

    if not yamls:
        print("error: no changes YAML files found in workdir", file=sys.stderr)
        sys.exit(1)

    # Validate each YAML
    total_issues = 0
    for yaml_path in yamls:
        issues = validate_and_fix(yaml_path)
        if issues:
            for issue in issues:
                print(f"  {issue}", file=sys.stderr)
            total_issues += len(issues)
        else:
            print(f"{yaml_path.name}: OK", file=sys.stderr)

    # Fill commits from file-commits map (if available)
    map_path = workdir / "file-commits-map.yaml"
    if map_path.is_file():
        file_commits_map = yaml.safe_load(map_path.read_text(encoding="utf-8")) or {}
        for yaml_path in yamls:
            fill_commits_from_map(yaml_path, file_commits_map)

    # Cross-check file coverage against diffs
    reports = crosscheck_file_coverage(workdir)
    for report in reports:
        content = report.read_text(encoding="utf-8").strip()
        if content == "PASS":
            print(f"{report.name}: PASS", file=sys.stderr)
        else:
            issue_count = len(content.splitlines())
            total_issues += issue_count
            print(f"{report.name}: {issue_count} issue(s)", file=sys.stderr)

    if total_issues == 0:
        print("All validations passed.", file=sys.stderr)
    else:
        print(f"{total_issues} total issue(s) found.", file=sys.stderr)


def fill_commits_from_map(yaml_path: Path, file_commits_map: dict[str, list[str]]) -> None:
    """Fill `commits` field in YAML entries from file→commits map.

    For each change entry, collect all commits that touched any of its files.
    Deduplicate and sort. Write back to the YAML file.
    """
    raw_text = yaml_path.read_text(encoding="utf-8")
    data = _safe_parse(raw_text)
    if data is None:
        return

    changes = data.get("changes", [])
    if not isinstance(changes, list):
        return

    for change in changes:
        files = change.get("files", [])
        if not isinstance(files, list):
            continue

        all_commits: list[str] = []
        seen: set[str] = set()
        for f in files:
            for commit_hash in file_commits_map.get(f, []):
                if commit_hash not in seen:
                    seen.add(commit_hash)
                    all_commits.append(commit_hash)

        change["commits"] = all_commits if all_commits else change.get("commits", [])

    _write_back(yaml_path, raw_text, data)
