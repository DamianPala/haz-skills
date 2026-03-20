"""Tests for v2 net-diff pipeline functions."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from change_summary.chunk import chunk_by_file, sort_files_by_category
from change_summary.format import (
    format_commit_log_sidebar,
    format_net_file_section,
    format_net_header,
)
from change_summary.git_ops import (
    _count_diff_hunks,
    build_file_commits_map,
    collect_commit_log,
    collect_net_diff,
    collect_net_file_stats,
    patch_line_counts_from_diff,
)
from change_summary.models import FileChange, ProjectContext


# --- Helpers ---

# Env that disables hooks (commitlint etc.) for test repos
_NO_HOOKS_ENV = {**os.environ, "HUSKY": "0"}


def _git(args: list[str], cwd: Path) -> None:
    env_args = [
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@test.com",
        "-c",
        "core.hooksPath=/dev/null",
    ]
    subprocess.run(
        ["git"] + env_args + args,
        cwd=cwd,
        capture_output=True,
        check=True,
        env=_NO_HOOKS_ENV,
    )


@pytest.fixture
def simple_repo(tmp_path: Path) -> Path:
    """Create a simple git repo with a few commits for testing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "-b", "main"], repo)

    # Initial commit
    (repo / "src").mkdir()
    (repo / "src" / "main.c").write_text("int main() { return 0; }\n")
    (repo / "README.md").write_text("# Project\n")
    _git(["add", "."], repo)
    _git(["commit", "-m", "feat: initial"], repo)
    _git(["tag", "v1.0.0"], repo)

    # Second commit: add feature
    (repo / "src" / "auth.c").write_text("void auth() {}\n")
    (repo / "src" / "auth.h").write_text("#pragma once\nvoid auth();\n")
    _git(["add", "."], repo)
    _git(["commit", "-m", "feat: add auth"], repo)

    # Third commit: fix + config change
    (repo / "src" / "main.c").write_text("int main() { auth(); return 0; }\n")
    (repo / "Makefile").write_text("all: main\n")
    _git(["add", "."], repo)
    _git(["commit", "-m", "fix: call auth on startup"], repo)
    _git(["tag", "v1.1.0"], repo)

    return repo


# --- _count_diff_hunks ---


class TestCountDiffHunks:
    def test_counts_hunks_per_file(self) -> None:
        raw = (
            "diff --git a/src/a.c b/src/a.c\n"
            "index abc..def 100644\n"
            "--- a/src/a.c\n"
            "+++ b/src/a.c\n"
            "@@ -1,3 +1,4 @@\n"
            " line1\n"
            "+added\n"
            "@@ -10,2 +11,3 @@\n"
            " line10\n"
            "+added2\n"
            "diff --git a/src/b.c b/src/b.c\n"
            "index ghi..jkl 100644\n"
            "@@ -1,1 +1,2 @@\n"
            "+only one hunk\n"
        )
        counts = _count_diff_hunks(raw)
        assert counts["src/a.c"] == 2
        assert counts["src/b.c"] == 1

    def test_empty_diff(self) -> None:
        assert _count_diff_hunks("") == {}


class TestPatchLineCountsFromDiff:
    def test_patches_zero_counts(self) -> None:
        stats = [FileChange("sub/file.c", "modified", "source", 0, 0)]
        diffs = {"sub/file.c": "+added line\n-removed line\n context\n+another add\n"}
        patch_line_counts_from_diff(stats, diffs)
        assert stats[0].lines_added == 2
        assert stats[0].lines_removed == 1

    def test_skips_nonzero_counts(self) -> None:
        stats = [FileChange("src/main.c", "modified", "source", 10, 5)]
        diffs = {"src/main.c": "+line\n-line\n"}
        patch_line_counts_from_diff(stats, diffs)
        assert stats[0].lines_added == 10  # unchanged
        assert stats[0].lines_removed == 5

    def test_skips_missing_diff(self) -> None:
        stats = [FileChange("missing.c", "modified", "source", 0, 0)]
        patch_line_counts_from_diff(stats, {})
        assert stats[0].lines_added == 0


class TestCollectNetDiffHunkCounts:
    def test_returns_hunk_counts(self, simple_repo: Path) -> None:
        _file_diffs, hunk_counts = collect_net_diff("v1.0.0", "v1.1.0", simple_repo)
        # src/main.c was modified (1 hunk), src/auth.c was added (1 hunk)
        assert "src/main.c" in hunk_counts
        assert hunk_counts["src/main.c"] >= 1


# --- collect_net_file_stats ---


class TestCollectNetFileStats:
    def test_returns_file_changes(self, simple_repo: Path) -> None:
        files = collect_net_file_stats("v1.0.0", "v1.1.0", simple_repo)
        assert len(files) >= 3
        paths = {f.path for f in files}
        assert "src/auth.c" in paths
        assert "src/auth.h" in paths
        assert "src/main.c" in paths

    def test_file_has_category(self, simple_repo: Path) -> None:
        files = collect_net_file_stats("v1.0.0", "v1.1.0", simple_repo)
        by_path = {f.path: f for f in files}
        assert by_path["src/auth.c"].category == "source"
        assert by_path["Makefile"].category == "ci"

    def test_file_has_status(self, simple_repo: Path) -> None:
        files = collect_net_file_stats("v1.0.0", "v1.1.0", simple_repo)
        by_path = {f.path: f for f in files}
        assert by_path["src/auth.c"].status == "added"
        assert by_path["src/main.c"].status == "modified"

    def test_file_has_line_counts(self, simple_repo: Path) -> None:
        files = collect_net_file_stats("v1.0.0", "v1.1.0", simple_repo)
        by_path = {f.path: f for f in files}
        assert by_path["src/auth.c"].lines_added > 0

    def test_no_likely_type(self, simple_repo: Path) -> None:
        """v2: LLM decides type, no heuristic hints."""
        files = collect_net_file_stats("v1.0.0", "v1.1.0", simple_repo)
        for f in files:
            assert f.likely_type == ""


# --- build_file_commits_map ---


class TestBuildFileCommitsMap:
    def test_returns_mapping(self, simple_repo: Path) -> None:
        mapping = build_file_commits_map("v1.0.0", "v1.1.0", simple_repo)
        assert "src/auth.c" in mapping
        assert "src/main.c" in mapping

    def test_file_touched_by_multiple_commits(self, simple_repo: Path) -> None:
        mapping = build_file_commits_map("v1.0.0", "v1.1.0", simple_repo)
        # main.c modified in the fix commit
        assert len(mapping["src/main.c"]) >= 1

    def test_values_are_short_hashes(self, simple_repo: Path) -> None:
        mapping = build_file_commits_map("v1.0.0", "v1.1.0", simple_repo)
        for commits in mapping.values():
            for h in commits:
                assert len(h) >= 7
                assert all(c in "0123456789abcdef" for c in h)


# --- collect_commit_log ---


class TestCollectCommitLog:
    def test_returns_oneline_log(self, simple_repo: Path) -> None:
        log = collect_commit_log("v1.0.0", "v1.1.0", simple_repo)
        assert "auth" in log.lower()
        lines = log.strip().splitlines()
        assert len(lines) == 2  # two commits between v1.0.0 and v1.1.0


# --- format functions ---


class TestFormatNetHeader:
    def test_includes_range(self) -> None:
        ctx = ProjectContext(name="test-project")
        files = [FileChange("a.c", "modified", "source", 10, 5)]
        header = format_net_header(ctx, "v1.0..v2.0", files)
        assert "v1.0..v2.0" in header

    def test_includes_file_count(self) -> None:
        ctx = ProjectContext(name="test")
        files = [
            FileChange("a.c", "modified", "source", 10, 5),
            FileChange("b.c", "added", "source", 20, 0),
        ]
        header = format_net_header(ctx, "v1..v2", files)
        assert "2 changed" in header

    def test_includes_line_counts(self) -> None:
        ctx = ProjectContext(name="test")
        files = [FileChange("a.c", "modified", "source", 10, 5)]
        header = format_net_header(ctx, "v1..v2", files)
        assert "+10/-5" in header


class TestFormatCommitLogSidebar:
    def test_empty_log(self) -> None:
        assert format_commit_log_sidebar("") == ""

    def test_includes_hint_warning(self) -> None:
        sidebar = format_commit_log_sidebar("abc1234 feat: something")
        assert "hints only" in sidebar.lower()
        assert "abc1234" in sidebar


class TestFormatNetFileSection:
    def test_includes_path_and_category(self) -> None:
        fc = FileChange("src/auth.c", "added", "source", 15, 0)
        section = format_net_file_section(fc, "+void auth() {}")
        assert "src/auth.c" in section
        assert "source" in section
        assert "added" in section

    def test_no_likely_type_in_header(self) -> None:
        fc = FileChange("src/auth.c", "added", "source", 15, 0)
        section = format_net_file_section(fc, "+void auth() {}")
        assert "likely_" not in section

    def test_binary_marker(self) -> None:
        fc = FileChange("fw.bin", "added", "other", 0, 0)
        section = format_net_file_section(fc, "", is_binary=True)
        assert "Binary file" in section

    def test_single_hunk_no_region_hint(self) -> None:
        fc = FileChange("src/auth.c", "added", "source", 15, 0)
        section = format_net_file_section(fc, "+code", hunk_count=1)
        assert "change regions" not in section

    def test_multiple_hunks_shows_region_count(self) -> None:
        fc = FileChange("src/main.c", "modified", "source", 32, 9)
        section = format_net_file_section(fc, "+code", hunk_count=4)
        assert "4 change regions" in section


# --- chunk functions ---


class TestSortFilesByCategory:
    def test_source_before_test(self) -> None:
        files = [
            ("tests/test.c", "test", "..."),
            ("src/main.c", "source", "..."),
        ]
        sorted_files = sort_files_by_category(files)
        assert sorted_files[0][0] == "src/main.c"
        assert sorted_files[1][0] == "tests/test.c"

    def test_alphabetical_within_category(self) -> None:
        files = [
            ("src/z.c", "source", "..."),
            ("src/a.c", "source", "..."),
        ]
        sorted_files = sort_files_by_category(files)
        assert sorted_files[0][0] == "src/a.c"
        assert sorted_files[1][0] == "src/z.c"


class TestChunkByFile:
    def test_single_chunk_fits(self) -> None:
        sections = ["## File: 'a.c'\n+code\n"]
        chunks = chunk_by_file("# Header\n", "## Log\n", sections, "", 100000)
        assert len(chunks) == 1
        assert "a.c" in chunks[0]

    def test_splits_when_over_budget(self) -> None:
        big = "x" * 40000  # ~10k tokens
        sections = [big, big, big]
        chunks = chunk_by_file("H\n", "L\n", sections, "", 12000)
        assert len(chunks) > 1

    def test_header_in_every_chunk(self) -> None:
        big = "x" * 40000
        sections = [big, big]
        chunks = chunk_by_file("# HEADER\n", "## LOG\n", sections, "", 12000)
        for chunk in chunks:
            assert "# HEADER" in chunk

    def test_skipped_in_last_chunk(self) -> None:
        sections = ["## File: 'a.c'\n"]
        chunks = chunk_by_file("H\n", "L\n", sections, "## Skipped\n- lock.json\n", 100000)
        assert "Skipped" in chunks[-1]
