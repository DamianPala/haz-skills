"""Tests for orphan file detection."""

from __future__ import annotations

from pathlib import Path

import yaml

from change_summary.orphan import build_orphan_diff, find_orphan_files


def _write_diff(workdir: Path, chunk_num: int, file_sections: list[str]) -> None:
    """Write a fake diff file with ## File: headers."""
    content = "\n---\n\n".join(file_sections)
    (workdir / f"diff-{chunk_num}.txt").write_text(content, encoding="utf-8")


def _write_yaml(workdir: Path, chunk_num: int, files_per_change: list[list[str]]) -> None:
    """Write a fake changes YAML covering the given files."""
    changes = []
    for files in files_per_change:
        changes.append({"type": "feat", "description": "test", "files": files})
    yaml_text = yaml.dump({"changes": changes}, default_flow_style=False)
    (workdir / f"changes-chunk-{chunk_num}.yaml").write_text(yaml_text, encoding="utf-8")


class TestFindOrphanFiles:
    def test_no_orphans(self, tmp_path: Path) -> None:
        _write_diff(tmp_path, 1, ["## File: 'src/a.c' [source, modified, +5/-2]\n+code"])
        _write_yaml(tmp_path, 1, [["src/a.c"]])
        result = find_orphan_files(tmp_path)
        assert result == {}

    def test_finds_orphans(self, tmp_path: Path) -> None:
        _write_diff(
            tmp_path,
            1,
            [
                "## File: 'src/a.c' [source, modified, +5/-2]\n+code",
                "## File: 'src/b.c' [source, modified, +3/-1]\n+code",
                "## File: 'src/c.c' [source, added, +10/-0]\n+code",
            ],
        )
        _write_yaml(tmp_path, 1, [["src/a.c"]])
        result = find_orphan_files(tmp_path)
        assert 1 in result
        assert sorted(result[1]) == ["src/b.c", "src/c.c"]

    def test_multiple_chunks(self, tmp_path: Path) -> None:
        _write_diff(tmp_path, 1, ["## File: 'a.c' [source, modified, +1/-1]\n+x"])
        _write_yaml(tmp_path, 1, [["a.c"]])
        _write_diff(tmp_path, 2, ["## File: 'b.c' [source, added, +5/-0]\n+y"])
        _write_yaml(tmp_path, 2, [])  # empty YAML
        result = find_orphan_files(tmp_path)
        assert 1 not in result
        assert 2 in result
        assert result[2] == ["b.c"]

    def test_missing_yaml(self, tmp_path: Path) -> None:
        _write_diff(tmp_path, 1, ["## File: 'a.c' [source, modified, +1/-1]\n+x"])
        # No YAML file
        result = find_orphan_files(tmp_path)
        assert 1 in result
        assert result[1] == ["a.c"]


class TestBuildOrphanDiff:
    def test_extracts_orphan_sections(self, tmp_path: Path) -> None:
        diff_content = (
            "## File: 'src/a.c' [source, modified, +5/-2]\n"
            "+covered change\n"
            "\n---\n\n"
            "## File: 'src/b.c' [source, added, +10/-0]\n"
            "+orphan change\n"
            "+more orphan\n"
        )
        (tmp_path / "diff-1.txt").write_text(diff_content, encoding="utf-8")

        result = build_orphan_diff(tmp_path, 1, ["src/b.c"])
        assert "src/b.c" in result
        assert "+orphan change" in result
        assert "src/a.c" not in result

    def test_empty_when_no_match(self, tmp_path: Path) -> None:
        (tmp_path / "diff-1.txt").write_text(
            "## File: 'a.c' [source, modified, +1/-1]\n+x\n", encoding="utf-8"
        )
        result = build_orphan_diff(tmp_path, 1, ["nonexistent.c"])
        assert result == ""
