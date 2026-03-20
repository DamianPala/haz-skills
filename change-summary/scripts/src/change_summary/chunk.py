"""Token estimation, chunking, and output writing."""

from __future__ import annotations

import sys
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 chars per token for code."""
    return len(text) // 4


# ---------------------------------------------------------------------------
# File-based chunking (v2 net-diff pipeline)
# ---------------------------------------------------------------------------

# Category sort order: source first (most important), then test, config, docs
_CATEGORY_ORDER = {
    "source": 0,
    "test": 1,
    "ci": 2,
    "config": 2,
    "deps": 3,
    "docs": 4,
    "assets": 5,
    "other": 6,
    "submodule": 7,
}


def sort_files_by_category(
    files: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """Sort (path, category, diff_text) tuples by category then alphabetically."""
    return sorted(files, key=lambda x: (_CATEGORY_ORDER.get(x[1], 99), x[0]))


def chunk_by_file(
    header: str,
    commit_log_sidebar: str,
    file_sections: list[str],
    skipped_section: str,
    max_tokens: int,
) -> list[str]:
    """Split file-based output into token-budget chunks.

    Each chunk gets header + commit log sidebar. File sections fill
    greedily until budget. Skipped section appended to the last chunk.
    """
    overhead = header + commit_log_sidebar + "---\n\n"
    overhead_tokens = estimate_tokens(overhead)
    budget = max_tokens - overhead_tokens - 100

    if budget <= 0:
        all_text = overhead
        for fs in file_sections:
            all_text += fs + "\n---\n\n"
        all_text += skipped_section
        return [all_text]

    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0

    for fs in file_sections:
        fs_tokens = estimate_tokens(fs)

        if current_parts and (current_tokens + fs_tokens) > budget:
            chunk_text = overhead + "\n---\n\n".join(current_parts) + "\n"
            chunks.append(chunk_text)
            current_parts = []
            current_tokens = 0

        current_parts.append(fs)
        current_tokens += fs_tokens

    if current_parts:
        chunk_text = overhead + "\n---\n\n".join(current_parts) + "\n"
        if skipped_section:
            chunk_text += "\n" + skipped_section
        chunks.append(chunk_text)
    elif skipped_section:
        chunks.append(overhead + skipped_section)

    if not chunks:
        chunks.append(overhead.rstrip())

    return chunks


def _clean_stale_outputs(out_dir: Path) -> None:
    """Remove stale output files from a previous run.

    Prevents single-chunk runs from seeing leftover chunk-*.txt and vice versa.
    Also cleans generated prompt files that depend on the output file list.
    """
    stale_patterns = [
        "script-output.txt",  # legacy name
        "diff-*.txt",
        "interpret-prompt.md",
        "interpret-chunk-*-prompt.md",
        "verify-prompt.md",
        "verify-chunk-*-prompt.md",
        "changes.yaml",
        "changes-chunk-*.yaml",
        "verify-result.txt",
        "verify-chunk-*-result.txt",
        "cross-check-result.txt",  # legacy name
        "cross-check-chunk-*.txt",
        "orphan-diff-*.txt",
        "orphan-changes-chunk-*.yaml",
        "orphan-fill-chunk-*-prompt.md",
        "orphan-fill-prompt.md",
        "dedup-prompt.md",
    ]
    for pattern in stale_patterns:
        for f in out_dir.glob(pattern):
            f.unlink()


def write_chunks(chunks: list[str], output_path: str | None) -> None:
    """Write output chunks to stdout or file(s).

    When output_path is given it is treated as a directory:
    - Single chunk  → <dir>/diff-1.txt
    - Multiple      → <dir>/diff-1.txt, diff-2.txt, ...
    When output_path is None, single chunk goes to stdout,
    multiple chunks go to ./diff-*.txt.
    """
    out_dir: Path | None = None
    if output_path:
        out_dir = Path(output_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        _clean_stale_outputs(out_dir)

    if len(chunks) <= 1:
        text = chunks[0] if chunks else ""
        if out_dir:
            out_file = out_dir / "diff-1.txt"
            try:
                out_file.write_text(text, encoding="utf-8")
            except OSError as exc:
                from change_summary.cli import die

                die(f"Failed to write output file '{out_file}': {exc}")
        else:
            print(text, end="")
    else:
        # Multiple chunks: write to numbered files
        if not out_dir:
            out_dir = Path(".")

        for i, chunk_text in enumerate(chunks, 1):
            chunk_path = out_dir / f"diff-{i}.txt"
            try:
                chunk_path.write_text(chunk_text, encoding="utf-8")
            except OSError as exc:
                from change_summary.cli import die

                die(f"Failed to write chunk file '{chunk_path}': {exc}")

        chunk_names = [f"diff-{i}.txt" for i in range(1, len(chunks) + 1)]
        print(
            f"Output split into {len(chunks)} chunks: {', '.join(chunk_names)}",
            file=sys.stderr,
        )
