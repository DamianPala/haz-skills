"""Tests for change_summary.context: project context collection."""

from __future__ import annotations

from pathlib import Path

from change_summary.context import collect_project_context


class TestReadsReadmeExcerpt:
    def test_reads_readme(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text(
            "# My Project\n\nThis is a test project.\n\n## Features\n- Fast\n- Simple\n"
        )
        ctx = collect_project_context(tmp_path)
        assert ctx.readme_excerpt is not None
        assert "My Project" in ctx.readme_excerpt
        assert "Features" in ctx.readme_excerpt

    def test_missing_readme_returns_none(self, tmp_path: Path) -> None:
        ctx = collect_project_context(tmp_path)
        assert ctx.readme_excerpt is None


class TestReadsManifestPyproject:
    def test_reads_pyproject_name_and_description(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "my-tool"\ndescription = "A useful tool"\n'
        )
        ctx = collect_project_context(tmp_path)
        assert ctx.name == "my-tool"
        assert ctx.description == "A useful tool"

    def test_reads_package_json(self, tmp_path: Path) -> None:
        (tmp_path / "package.json").write_text('{"name": "my-app", "description": "A web app"}')
        ctx = collect_project_context(tmp_path)
        assert ctx.name == "my-app"
        assert ctx.description == "A web app"


class TestReadsChangelogEntries:
    def test_parses_changelog_entries(self, tmp_path: Path) -> None:
        (tmp_path / "CHANGELOG.md").write_text(
            "# Changelog\n\n"
            "## [2.0.0] - 2026-03-01\n\n### Changed\n- New API\n\n"
            "## [1.1.0] - 2026-02-01\n\n### Added\n- Feature X\n\n"
            "## [1.0.0] - 2026-01-01\n\n### Added\n- Initial release\n"
        )
        ctx = collect_project_context(tmp_path)
        assert ctx.previous_changelog_entry is not None
        assert "[2.0.0]" in ctx.previous_changelog_entry
        assert "[1.1.0]" in ctx.previous_changelog_entry
        assert "[1.0.0]" in ctx.previous_changelog_entry

    def test_no_changelog_returns_none(self, tmp_path: Path) -> None:
        ctx = collect_project_context(tmp_path)
        assert ctx.previous_changelog_entry is None


class TestMissingFilesReturnNone:
    def test_empty_dir_all_none(self, tmp_path: Path) -> None:
        ctx = collect_project_context(tmp_path)
        # Fallback: directory name when no manifest found
        assert ctx.name == tmp_path.resolve().name
        assert ctx.description is None
        assert ctx.readme_excerpt is None
        assert ctx.previous_changelog_entry is None
        assert ctx.agents_excerpt is None

    def test_top_dirs_still_listed(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        ctx = collect_project_context(tmp_path)
        assert "src/" in ctx.top_dirs
        assert "tests/" in ctx.top_dirs
