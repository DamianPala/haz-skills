"""Git operations for net-diff pipeline."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from change_summary.classify import categorize_file
from change_summary.models import ChangeSummaryConfig, FileChange


class GitError(Exception):
    pass


def run_git(args: list[str], *, cwd: Path | None = None, timeout: int = 30) -> str:
    """Run a git command and return stdout. Raise GitError on failure."""
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            cwd=cwd,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise GitError("git is not installed or not on PATH")
    except subprocess.TimeoutExpired:
        raise GitError(f"git command timed out: {' '.join(cmd)}")

    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(stderr)
    return result.stdout.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Net-diff collection (v2 pipeline)
# ---------------------------------------------------------------------------


def collect_net_diff(
    base: str | None,
    head: str,
    repo_root: Path,
    config: ChangeSummaryConfig | None = None,
) -> tuple[dict[str, str], dict[str, int]]:
    """Collect net diff between base and head, split by file.

    Returns (file_diffs, hunk_counts):
      - file_diffs: dict mapping file path to stripped diff content
      - hunk_counts: dict mapping file path to number of change regions (hunks)
    Handles submodules according to config (ignore/summarize/expand).
    """
    diff_args = ["diff", "--no-color"]
    if base:
        diff_args.append(f"{base}..{head}")
    else:
        diff_args.append(head)

    # Expand submodules inline (git diff --submodule=diff)
    diff_args.append("--submodule=diff")

    try:
        raw_diff = run_git(diff_args, cwd=repo_root, timeout=120)
    except GitError:
        return {}, {}

    hunk_counts = _count_diff_hunks(raw_diff)
    file_diffs = _split_diff_by_file(raw_diff)

    # Apply submodule config filters
    if config:
        file_diffs = _filter_submodule_diffs(file_diffs, config)
        hunk_counts = {p: c for p, c in hunk_counts.items() if p in file_diffs}

    return file_diffs, hunk_counts


def _count_diff_hunks(raw_diff: str) -> dict[str, int]:
    """Count @@ hunk markers per file in a raw unified diff."""
    current_file: str | None = None
    counts: dict[str, int] = {}
    for line in raw_diff.splitlines():
        m = re.match(r"^diff --git a/.+ b/(.+)$", line)
        if m:
            current_file = m.group(1)
            counts[current_file] = 0
        elif current_file is not None and line.startswith("@@"):
            counts[current_file] = counts.get(current_file, 0) + 1
    return counts


def patch_line_counts_from_diff(
    file_stats: list[FileChange],
    file_diffs: dict[str, str],
) -> None:
    """Fix +0/-0 line counts by counting +/- lines in diff text.

    Submodule files show +0/-0 from git numstat because --submodule=short
    doesn't expand submodules. This function patches those zero counts
    by counting actual added/removed lines from the diff content.
    """
    stats_by_path = {fc.path: fc for fc in file_stats}
    for path, diff_text in file_diffs.items():
        fc = stats_by_path.get(path)
        if fc is None or (fc.lines_added > 0 or fc.lines_removed > 0):
            continue
        added = 0
        removed = 0
        for line in diff_text.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                removed += 1
        fc.lines_added = added
        fc.lines_removed = removed


def _filter_submodule_diffs(
    file_diffs: dict[str, str], config: ChangeSummaryConfig
) -> dict[str, str]:
    """Remove diffs for ignored submodules, keep summarize/expand as-is."""
    if not config.ignore:
        return file_diffs
    return {
        path: diff
        for path, diff in file_diffs.items()
        if not any(path.startswith(f"{ign}/") or path == ign for ign in config.ignore)
    }


def collect_net_file_stats(
    base: str | None,
    head: str,
    repo_root: Path,
) -> list[FileChange]:
    """Collect per-file metadata from net diff (status, lines added/removed).

    Returns FileChange objects with path, status, category, lines.
    No likely_type (v2: LLM decides type from code, not heuristics).
    """
    range_spec = f"{base}..{head}" if base else head

    # name-status: A/M/D/R per file
    try:
        ns_raw = run_git(
            ["diff", "--name-status", "--submodule=short", range_spec],
            cwd=repo_root,
        )
    except GitError:
        ns_raw = ""

    # numstat: +lines/-lines per file
    try:
        num_raw = run_git(
            ["diff", "--numstat", "--submodule=short", range_spec],
            cwd=repo_root,
        )
    except GitError:
        num_raw = ""

    line_counts: dict[str, tuple[int, int]] = {}
    for line in num_raw.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            added_str, removed_str, path = parts[0], parts[1], parts[-1]
            added = int(added_str) if added_str != "-" else 0
            removed = int(removed_str) if removed_str != "-" else 0
            line_counts[path] = (added, removed)

    status_map = {"A": "added", "M": "modified", "D": "deleted"}
    files: list[FileChange] = []

    for line in ns_raw.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue

        raw_status = parts[0].strip()
        filepath = parts[-1].strip()

        if raw_status.startswith("R"):
            status = "renamed"
            filepath = parts[-1].strip()
        else:
            status = status_map.get(raw_status[0], "modified")

        added, removed = line_counts.get(filepath, (0, 0))
        category = categorize_file(filepath)

        files.append(
            FileChange(
                path=filepath,
                status=status,
                category=category,
                lines_added=added,
                lines_removed=removed,
            )
        )

    return files


def build_file_commits_map(
    base: str | None,
    head: str,
    repo_root: Path,
) -> dict[str, list[str]]:
    """Build mapping: file path → list of short commit hashes that touched it.

    Uses git log --name-only to get per-commit file lists, then inverts.
    """
    log_args = ["log", "--name-only", "--pretty=format:%h"]
    if base:
        log_args.append(f"{base}..{head}")
    else:
        log_args.append(head)

    try:
        raw = run_git(log_args, cwd=repo_root)
    except GitError:
        return {}

    file_to_commits: dict[str, list[str]] = {}
    current_hash = ""

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Short hash lines are 7-12 hex chars with no path separators
        if re.match(r"^[0-9a-f]{7,12}$", line):
            current_hash = line
        elif current_hash:
            file_to_commits.setdefault(line, []).append(current_hash)

    return file_to_commits


def collect_commit_log(
    base: str | None,
    head: str,
    repo_root: Path,
) -> str:
    """Collect git log --oneline for commit log sidebar (hints only)."""
    log_args = ["log", "--oneline"]
    if base:
        log_args.append(f"{base}..{head}")
    else:
        log_args.append(head)

    try:
        return run_git(log_args, cwd=repo_root).strip()
    except GitError:
        return ""


def _split_diff_by_file(raw_diff: str) -> dict[str, str]:
    """Split a unified diff into per-file sections with stripped headers.

    Returns a dict mapping file path to stripped diff content.
    """
    if not raw_diff.strip():
        return {}

    # Split on "diff --git a/... b/..." boundaries
    file_sections = re.split(r"^diff --git a/.+ b/.+\n", raw_diff, flags=re.MULTILINE)
    # Extract file paths from the "diff --git" lines
    file_paths = re.findall(r"^diff --git a/.+ b/(.+)$", raw_diff, flags=re.MULTILINE)

    result: dict[str, str] = {}
    for path, section in zip(file_paths, file_sections[1:]):
        stripped = _strip_diff_headers(section)
        if stripped:
            result[path] = stripped

    return result


def _strip_diff_headers(section: str) -> str:
    """Strip index, --- a/, +++ b/ lines and @@ line numbers from a diff section.

    Keeps the function/context name from @@ headers and all +/-/space lines.
    """
    lines = section.splitlines()
    result: list[str] = []

    for line in lines:
        # Skip "index abc..def 100644"
        if line.startswith("index "):
            continue
        # Skip "new file mode ...", "old mode ...", "new mode ...", "deleted file mode ..."
        if line.startswith(("new file mode", "old mode", "new mode", "deleted file mode")):
            continue
        # Skip "similarity index ...", "rename from ...", "rename to ..."
        if line.startswith(("similarity index", "rename from", "rename to")):
            continue
        # Skip "--- a/path" and "+++ b/path"
        if line.startswith("--- a/") or line.startswith("+++ b/"):
            continue
        # Skip "--- /dev/null" and "+++ /dev/null" (new/deleted files)
        if line.startswith("--- /dev/null") or line.startswith("+++ /dev/null"):
            continue
        # Strip @@ line numbers, keep context name
        if line.startswith("@@"):
            # Extract function/context name after the closing @@
            ctx_match = re.search(r"@@\s+(.+)$", line.split("@@", 2)[-1])
            if ctx_match:
                ctx_name = ctx_match.group(1).strip()
                if ctx_name:
                    result.append(f"  {ctx_name}")
            continue
        # Skip "Binary files ... differ"
        if line.startswith("Binary files "):
            continue
        # Keep +/-/space content lines
        result.append(line)

    return "\n".join(result)
