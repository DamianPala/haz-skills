"""Orphan file detection: find diff files not covered by YAML entries."""

from __future__ import annotations

import re
from pathlib import Path

import yaml


def find_orphan_files(workdir: Path) -> dict[int, list[str]]:
    """Find files in diff chunks not covered by any YAML entry.

    Returns dict mapping chunk number to list of orphan file paths.
    Only returns chunks that have orphans.
    """
    result: dict[int, list[str]] = {}

    for diff_path in sorted(workdir.glob("diff-*.txt")):
        m = re.search(r"diff-(\d+)\.txt", diff_path.name)
        if not m:
            continue
        chunk_num = int(m.group(1))
        yaml_path = workdir / f"changes-chunk-{chunk_num}.yaml"

        diff_files = _extract_diff_file_paths(diff_path)
        yaml_files = _extract_yaml_file_paths(yaml_path) if yaml_path.is_file() else set()

        orphans = sorted(diff_files - yaml_files)
        if orphans:
            result[chunk_num] = orphans

    return result


def build_orphan_diff(
    workdir: Path,
    chunk_num: int,
    orphan_paths: list[str],
) -> str:
    """Extract diff sections for orphan files from a chunk's diff file.

    Returns a text block with only the orphan file sections, ready for
    a targeted LLM interpretation pass.
    """
    diff_path = workdir / f"diff-{chunk_num}.txt"
    if not diff_path.is_file():
        return ""

    diff_text = diff_path.read_text(encoding="utf-8")
    orphan_set = set(orphan_paths)

    sections: list[str] = []
    current_section: list[str] = []
    current_path: str | None = None
    in_orphan = False

    for line in diff_text.splitlines():
        file_match = re.match(r"^## File: '([^']+)'", line)
        if file_match:
            # Save previous orphan section
            if in_orphan and current_section:
                sections.append("\n".join(current_section))

            current_path = file_match.group(1)
            in_orphan = current_path in orphan_set
            current_section = [line] if in_orphan else []
            continue

        if in_orphan:
            current_section.append(line)

    # Don't forget last section
    if in_orphan and current_section:
        sections.append("\n".join(current_section))

    return "\n\n---\n\n".join(sections)


def _extract_diff_file_paths(diff_path: Path) -> set[str]:
    """Extract file paths from ## File: headers in a diff chunk."""
    text = diff_path.read_text(encoding="utf-8")
    return set(re.findall(r"^## File: '([^']+)'", text, re.MULTILINE))


def merge_orphans_into_chunks(workdir: Path) -> int:
    """Merge orphan YAML entries back into their parent chunk YAML files.

    After orphan fill, this appends orphan entries to the main chunk YAML
    so that verify and merge see all items in one place.

    Returns number of orphan entries merged.
    """
    total = 0
    for orphan_path in sorted(workdir.glob("orphan-changes-chunk-*.yaml")):
        m = re.search(r"orphan-changes-chunk-(\d+)\.yaml", orphan_path.name)
        if not m:
            continue
        chunk_num = m.group(1)
        chunk_yaml_path = workdir / f"changes-chunk-{chunk_num}.yaml"

        if not chunk_yaml_path.is_file():
            continue

        # Parse orphan entries
        try:
            orphan_data = yaml.safe_load(orphan_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError):
            continue

        if not isinstance(orphan_data, dict):
            continue
        orphan_changes = orphan_data.get("changes", [])
        if not isinstance(orphan_changes, list) or not orphan_changes:
            continue

        # Parse chunk YAML
        chunk_text = chunk_yaml_path.read_text(encoding="utf-8")
        try:
            chunk_data = yaml.safe_load(chunk_text)
        except yaml.YAMLError:
            continue

        if not isinstance(chunk_data, dict):
            continue

        # Append orphan entries
        chunk_changes = chunk_data.get("changes", [])
        if not isinstance(chunk_changes, list):
            chunk_changes = []
        chunk_changes.extend(orphan_changes)
        chunk_data["changes"] = chunk_changes

        # Write back with preserved header comments
        header_lines = []
        for line in chunk_text.splitlines():
            if line.startswith("#"):
                header_lines.append(line)
            else:
                break

        yaml_body = yaml.dump(
            chunk_data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=100,
        )
        output = "\n".join(header_lines) + "\n\n" + yaml_body if header_lines else yaml_body
        chunk_yaml_path.write_text(output, encoding="utf-8")

        total += len(orphan_changes)
        orphan_path.unlink()  # Remove merged orphan file

    return total


def _extract_yaml_file_paths(yaml_path: Path) -> set[str]:
    """Extract all file paths from YAML entries' files lists."""
    try:
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return set()

    if not isinstance(data, dict):
        return set()

    paths: set[str] = set()
    for change in data.get("changes", []):
        if isinstance(change, dict):
            files = change.get("files", [])
            if isinstance(files, list):
                paths.update(str(f) for f in files)
    return paths
