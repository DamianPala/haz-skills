"""CLI entry point: argparse, main pipeline, and utility functions."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import NoReturn

from change_summary.chunk import chunk_by_file, sort_files_by_category, write_chunks
from change_summary.context import collect_project_context, parse_change_summary_config
from change_summary.filter import classify_skippable_by_path, is_binary_path
from change_summary.format import (
    format_commit_log_sidebar,
    format_net_file_section,
    format_net_header,
    format_skipped_section,
)
from change_summary.git_ops import (
    GitError,
    build_file_commits_map,
    collect_commit_log,
    collect_net_diff,
    collect_net_file_stats,
    patch_line_counts_from_diff,
    run_git,
)
from change_summary.models import FileChange, SkippedFile
from change_summary.prompts import write_prompts


def die(msg: str, code: int = 1) -> NoReturn:
    """Print error to stderr and exit."""
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def warn(msg: str) -> None:
    """Print warning to stderr."""
    print(f"warning: {msg}", file=sys.stderr)


def get_repo_root() -> Path:
    """Find the git repository root from the current directory."""
    try:
        root = run_git(["rev-parse", "--show-toplevel"]).strip()
    except GitError as exc:
        die(f"Not inside a git repository: {exc}")
    return Path(root)


def resolve_range(
    base: str | None,
    head: str | None,
    since: str | None,
    repo_root: Path,
) -> tuple[str | None, str, bool]:
    """Determine the commit range to analyze.

    Returns:
        (base_ref or None, head_ref, is_date_mode)
    """
    if since:
        return None, head or "HEAD", True

    head = head or "HEAD"

    if base:
        # Verify both refs exist
        _verify_ref(base, repo_root)
        _verify_ref(head, repo_root)
        return base, head, False

    # Auto-detect base from latest tag
    try:
        latest_tag = run_git(
            ["describe", "--tags", "--abbrev=0", head],
            cwd=repo_root,
        ).strip()
        return latest_tag, head, False
    except GitError:
        pass

    # No tags found at all
    warn(
        "No tags found in repository. Using entire history. Consider passing an explicit base ref."
    )
    return None, head, False


def _verify_ref(ref: str, repo_root: Path) -> None:
    """Verify that a git ref exists."""
    try:
        run_git(["rev-parse", "--verify", ref], cwd=repo_root)
    except GitError:
        die(f"Git ref not found: {ref}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Collect and pre-process git change data for LLM interpretation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # Collect subcommand
    collect_parser = subparsers.add_parser(
        "collect",
        help="Collect and chunk git changes for LLM interpretation.",
    )
    _add_collect_args(collect_parser)

    # Merge subcommand
    merge_parser = subparsers.add_parser(
        "merge",
        help="Merge per-chunk changes YAML files into a single changes.yaml.",
    )
    merge_parser.add_argument(
        "workdir",
        help="Directory containing changes-chunk-*.yaml files.",
    )

    # Validate subcommand
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate YAML files and cross-check against diffs. Accepts a file or workdir.",
    )
    validate_parser.add_argument(
        "path",
        help="Path to a changes YAML file or a workdir containing diff + YAML pairs.",
    )

    # Orphan subcommand
    orphan_parser = subparsers.add_parser(
        "orphan",
        help="Detect orphan files not covered by YAML entries and generate fill prompts.",
    )
    orphan_parser.add_argument(
        "workdir",
        help="Directory containing diff-*.txt and changes-chunk-*.yaml files.",
    )
    orphan_parser.add_argument(
        "--agent",
        default="claude",
        help="acpc agent name for orphan fill dispatch (default: claude).",
    )
    orphan_parser.add_argument(
        "--merge-back",
        action="store_true",
        help="Merge orphan YAML entries back into parent chunk YAMLs.",
    )

    # Backwards compatibility: if first arg is not a known subcommand, treat as collect
    known_commands = {"collect", "merge", "validate", "orphan"}
    if argv is None:
        import sys as _sys

        first_arg = _sys.argv[1] if len(_sys.argv) > 1 else None
    else:
        first_arg = argv[0] if argv else None

    if first_arg not in known_commands:
        # No subcommand given: parse as collect
        fallback = argparse.ArgumentParser(
            description="Collect and pre-process git change data for LLM interpretation.",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        _add_collect_args(fallback)
        args = fallback.parse_args(argv)
        args.command = "collect"
        return args

    return parser.parse_args(argv)


def _add_collect_args(parser: argparse.ArgumentParser) -> None:
    """Add arguments for the collect subcommand."""
    parser.add_argument(
        "base_ref",
        nargs="?",
        default=None,
        help="Base ref (tag, branch, commit). Auto-detected if omitted.",
    )
    parser.add_argument(
        "head_ref",
        nargs="?",
        default=None,
        help="Head ref. Defaults to HEAD.",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="Date range mode: analyze commits since this date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--author",
        default=None,
        help="Filter commits by author name or email.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output directory. Writes diff-1.txt (single chunk) or diff-N.txt (multi-chunk).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=100000,
        help="Max tokens per output chunk (default: 100000).",
    )
    parser.add_argument(
        "--agent",
        default="claude",
        help="acpc agent name for multi-chunk dispatch (default: claude).",
    )


def main(argv: list[str] | None = None) -> None:
    """Entry point: route to collect or merge subcommand."""
    args = parse_args(argv)

    if args.command == "merge":
        _run_merge(args)
        return

    if args.command == "validate":
        _run_validate(args)
        return

    if args.command == "orphan":
        _run_orphan(args)
        return

    _run_collect(args)


def _run_validate(args: argparse.Namespace) -> None:
    """Validate YAML files. If path is a directory, also cross-check against diffs."""
    from change_summary.validate import validate_file, validate_workdir

    target = Path(args.path)
    if target.is_dir():
        validate_workdir(target)
    else:
        validate_file(target)


def _run_orphan(args: argparse.Namespace) -> None:
    """Detect orphan files and generate fill prompts, or merge back."""
    from change_summary.orphan import (
        build_orphan_diff,
        find_orphan_files,
        merge_orphans_into_chunks,
    )
    from change_summary.prompts import write_orphan_prompts

    workdir = Path(args.workdir)
    if not workdir.is_dir():
        die(f"Workdir not found: {workdir}")

    # --merge-back mode: merge filled orphan YAML into chunk YAML
    if args.merge_back:
        merged = merge_orphans_into_chunks(workdir)
        if merged:
            print(f"Merged {merged} orphan entries back into chunk YAMLs.", file=sys.stderr)
        else:
            print("No orphan YAML files to merge.", file=sys.stderr)
        return

    # Detection mode
    orphans = find_orphan_files(workdir)
    if not orphans:
        print("No orphan files found. All diff files covered by YAML entries.", file=sys.stderr)
        return

    # Write orphan diff files and prompts
    for chunk_num, orphan_paths in orphans.items():
        orphan_diff = build_orphan_diff(workdir, chunk_num, orphan_paths)
        if not orphan_diff:
            continue
        orphan_diff_path = workdir / f"orphan-diff-{chunk_num}.txt"
        orphan_diff_path.write_text(orphan_diff, encoding="utf-8")
        print(
            f"Chunk {chunk_num}: {len(orphan_paths)} orphan file(s) → {orphan_diff_path.name}",
            file=sys.stderr,
        )

    write_orphan_prompts(workdir, orphans, agent=args.agent)

    total = sum(len(paths) for paths in orphans.values())
    print(
        f"Orphan detection: {total} file(s) in {len(orphans)} chunk(s). "
        f"Prompts written to {workdir}/orphan-fill-*.md",
        file=sys.stderr,
    )


def _run_merge(args: argparse.Namespace) -> None:
    """Merge per-chunk YAML files into a single changes.yaml."""
    from change_summary.merge import merge_chunks

    workdir = Path(args.workdir)
    if not workdir.is_dir():
        die(f"Workdir not found: {workdir}")

    try:
        out_path = merge_chunks(workdir)
    except FileNotFoundError as exc:
        die(str(exc))

    print(f"Merged to {out_path}", file=sys.stderr)


def _run_collect(args: argparse.Namespace) -> None:
    """Collect net diff, classify, format, chunk output."""
    repo_root = get_repo_root()

    # 1. Resolve range
    base, head, is_date_mode = resolve_range(
        args.base_ref,
        args.head_ref,
        args.since,
        repo_root,
    )

    if is_date_mode:
        range_str = f"--since={args.since}..{head}"
    elif base:
        range_str = f"{base}..{head}"
    else:
        range_str = head

    # 2. Collect project context and repo config
    project_ctx = collect_project_context(repo_root)
    config = parse_change_summary_config(repo_root)

    # 3. Collect net diff (split by file, submodules expanded)
    file_diffs, hunk_counts = collect_net_diff(base, head, repo_root, config)

    if not file_diffs:
        die(f"No changes found in range {range_str}", code=2)

    # 4. Collect per-file metadata (status, lines, category)
    file_stats = collect_net_file_stats(base, head, repo_root)

    # Fix +0/-0 line counts for submodule files
    patch_line_counts_from_diff(file_stats, file_diffs)

    stats_by_path = {fc.path: fc for fc in file_stats}

    # 5. Build file→commits map and commit log sidebar
    file_commits_map = build_file_commits_map(base, head, repo_root)
    commit_log = collect_commit_log(base, head, repo_root)

    # 6. Classify skippable files and detect binaries
    all_skipped: list[SkippedFile] = []
    binary_paths: set[str] = set()
    for path in list(file_diffs.keys()):
        fc = stats_by_path.get(path)
        if fc and classify_skippable_by_path(path):
            all_skipped.append(SkippedFile(path, fc.category, "lock/generated"))
            del file_diffs[path]
        elif is_binary_path(path, file_diffs):
            binary_paths.add(path)

    # 7. Add binary files that aren't in file_diffs (git shows them as
    #    "Binary files differ" which gets stripped, so they vanish from file_diffs)
    for fc in file_stats:
        if fc.path not in file_diffs and fc.path not in {s.path for s in all_skipped}:
            file_diffs[fc.path] = ""
            binary_paths.add(fc.path)

    # 8. Build file sections: (path, category, formatted_text)
    raw_sections: list[tuple[str, str, str]] = []
    for path, diff_text in file_diffs.items():
        fc = stats_by_path.get(path)
        if fc is None:
            # File from submodule expansion not in top-level stats
            fc = FileChange(path=path, status="modified", category="source")
        section = format_net_file_section(
            fc, diff_text, is_binary=(path in binary_paths), hunk_count=hunk_counts.get(path, 1)
        )
        raw_sections.append((path, fc.category, section))

    # 8. Sort by category then alphabetically
    sorted_sections = sort_files_by_category(raw_sections)
    file_section_texts = [s[2] for s in sorted_sections]

    # 9. Format header and sidebar
    header = format_net_header(project_ctx, range_str, file_stats)
    sidebar = format_commit_log_sidebar(commit_log)
    skipped_section = format_skipped_section(all_skipped)

    # 10. Chunk and write
    chunks = chunk_by_file(header, sidebar, file_section_texts, skipped_section, args.max_tokens)
    write_chunks(chunks, args.output)

    # Summary
    total_lines = sum(f.lines_added + f.lines_removed for f in file_stats)
    print(
        f"Collected: {len(chunks)} chunk(s), {len(file_diffs)} file(s), ~{total_lines} lines changed",
        file=sys.stderr,
    )

    # 11. Write file→commits map for post-processing
    if args.output:
        _write_file_commits_map(Path(args.output), file_commits_map)

    # 12. Generate agent prompts (when --output is set)
    if args.output:
        write_prompts(
            args.output,
            range_str,
            project_ctx.name,
            project_ctx.description,
            agent=args.agent,
        )


def _write_file_commits_map(out_dir: Path, file_commits_map: dict[str, list[str]]) -> None:
    """Write file→commits map as YAML for post-processing step."""
    import yaml

    out_path = out_dir / "file-commits-map.yaml"
    yaml_body = yaml.dump(
        file_commits_map,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=True,
    )
    out_path.write_text(yaml_body, encoding="utf-8")
