"""Plain text output formatting for change analysis."""

from __future__ import annotations

from change_summary.models import FileChange, ProjectContext, SkippedFile


# ---------------------------------------------------------------------------
# Net-diff formatting (v2 pipeline)
# ---------------------------------------------------------------------------


def format_net_header(
    project_ctx: ProjectContext,
    range_str: str,
    files: list[FileChange],
) -> str:
    """Format header block for net-diff output."""
    parts: list[str] = []
    parts.append(f"# Change Analysis: {range_str}")
    parts.append("")

    if project_ctx.name:
        desc = f" -- {project_ctx.description}" if project_ctx.description else ""
        parts.append(f"Project: {project_ctx.name}{desc}")
    if project_ctx.top_dirs:
        parts.append(f"Dirs: {', '.join(project_ctx.top_dirs)}")
    if project_ctx.previous_changelog_entry:
        parts.append("Previous changelog:")
        for line in project_ctx.previous_changelog_entry.splitlines():
            parts.append(f"  {line}")
    parts.append("")

    # Stats from file list
    total_added = sum(f.lines_added for f in files)
    total_removed = sum(f.lines_removed for f in files)
    category_counts: dict[str, int] = {}
    for f in files:
        category_counts[f.category] = category_counts.get(f.category, 0) + 1

    parts.append(f"Files: {len(files)} changed")
    cat_parts = [f"{count} {cat}" for cat, count in sorted(category_counts.items())]
    if cat_parts:
        parts.append(f"  {', '.join(cat_parts)}")
    parts.append(f"Lines: +{total_added}/-{total_removed}")
    parts.append("")

    return "\n".join(parts)


def format_commit_log_sidebar(commit_log: str) -> str:
    """Format commit log as a hints sidebar section."""
    if not commit_log:
        return ""
    parts: list[str] = []
    parts.append("## Commit log (hints only, may be inaccurate)")
    parts.append(commit_log)
    parts.append("")
    return "\n".join(parts)


def format_net_file_section(
    fc: FileChange,
    diff_text: str,
    is_binary: bool = False,
    hunk_count: int = 1,
) -> str:
    """Format a single file's metadata header and diff for net-diff output.

    No likely_type in metadata (v2: LLM decides type from code).
    When hunk_count > 1, adds "N change regions" hint to help LLM
    notice all change regions, not just the largest.
    """
    if is_binary:
        meta = f"## File: '{fc.path}' [{fc.category}, {fc.status}, binary]"
        return f"{meta}\n[Binary file -- cannot show diff]\n"

    regions = f", {hunk_count} change regions" if hunk_count > 1 else ""
    meta = (
        f"## File: '{fc.path}' [{fc.category}, {fc.status},"
        f" +{fc.lines_added}/-{fc.lines_removed}{regions}]"
    )

    if diff_text:
        return f"{meta}\n\n{diff_text}\n"
    return f"{meta}\n"


def format_skipped_section(skipped: list[SkippedFile]) -> str:
    """Format the skipped files section at the end (deduplicated)."""
    if not skipped:
        return ""
    seen: set[str] = set()
    parts: list[str] = ["## Skipped files"]
    for sf in skipped:
        if sf.path in seen:
            continue
        seen.add(sf.path)
        parts.append(f"- {sf.path} [{sf.category}, {sf.reason}]")
    parts.append("")
    return "\n".join(parts)
